"""Non-destructive Neo4j sync of the QA-VALIDATED layer (Phase 6G campaign). Legacy graph untouched.

Safety design
  * Cold BACKUP before the first write: the project Neo4j must be stopped; `runtime/neo4j/data` is copied to `data/campaign/neo4j_backup/<stamp>/data` and verified
    file by file (size + sha256, re-hashed from the copy); the verified manifest also stores the LEGACY STATS (nodes/edges/evidence/candidates) read right after the
    backup. No verified backup => NO write (the campaign continues with SQLite/GraphML/CSV only and reports the blocker).
  * DRY RUN first: the plan (new vs already present nodes/edges/evidence) is computed read-only and saved; only then idempotent MERGE.
  * Separate namespace: labels VEntity/VPerson/VOrganization/... (never Entity/Person/Organization), VEvidence, VArticle; relationship types = predicate names but only
    between V-labelled nodes, with layer='QA_VALIDATED', official=false, gold=false. Legacy official edges, candidates and queries are unaffected; after every sync the legacy
    stats must equal the backup-time stats, otherwise the run is reported as a blocker.
  * Only tier QA_PASS goes in. QUARANTINE / REJECT / LEGACY_* are never written here (they stay in the SQLite/CSV exports, never promoted). Conflicting or historical
    rows are kept with their factual_status and the list of OTHER tiers holding the same (subject, predicate, object).
  python -m vckg.graph.neo4j_validated {backup|plan|sync|verify} [--agg data/aggregate/staging_graph.sqlite]"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from vckg.graph.neo4j_sync import LABELS, PREDICATES, connect

ROOT = Path(__file__).resolve().parents[3]
BACKUP_DIR = ROOT / "data/campaign/neo4j_backup"
NEO_DATA = ROOT / "runtime/neo4j/data"
AGG_DB = ROOT / "data/aggregate/staging_graph.sqlite"
LAYER = "QA_VALIDATED"
V_LABELS = {k: "V" + v.replace(":", ":V") for k, v in LABELS.items()}  # PERSON -> VPerson, BANK -> VOrganization:VBank
CONSTRAINTS = [
    "CREATE CONSTRAINT v_entity_id IF NOT EXISTS FOR (n:VEntity) REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT v_evidence_id IF NOT EXISTS FOR (e:VEvidence) REQUIRE e.evidence_id IS UNIQUE",
    "CREATE CONSTRAINT v_article_id IF NOT EXISTS FOR (a:VArticle) REQUIRE a.article_id IS UNIQUE",
]


class Blocked(RuntimeError):
    """A safety condition for Neo4j writes is not met. The caller records it and continues without Neo4j."""


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def neo4j_running() -> bool:
    out = subprocess.run(check=False, args=["powershell", "-NoProfile", "-Command", "if (Get-NetTCPConnection -State Listen -LocalPort 7687 -ErrorAction SilentlyContinue) {'UP'} else {'DOWN'}"],
                         capture_output=True, text=True, timeout=60).stdout
    return "UP" in out


def ps_script(name: str, timeout: int = 240) -> int:
    """Run a project PowerShell script with output sent to a LOG FILE, not a pipe: start-neo4j.ps1 leaves a long-lived JVM behind and a pipe held by that grandchild would
    block subprocess forever (observed)."""
    log = ROOT / "logs" / f"{Path(name).stem}.run.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as f:
        return subprocess.run(check=False, args=["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / name)], stdin=subprocess.DEVNULL, stdout=f,
                              stderr=subprocess.STDOUT, timeout=timeout).returncode


# ------------------------------------------------------------------------------------------------ backup
def legacy_stats(driver) -> dict:
    with driver.session() as s:
        one = lambda q: s.run(q).single()[0]
        return {"entity_nodes": one("MATCH (n:Entity) RETURN count(n)"), "official_edges": one("MATCH (:Entity)-[r]->(:Entity) WHERE r.edge_id IS NOT NULL RETURN count(r)"),
                "relation_types": one("MATCH (:Entity)-[r]->(:Entity) WHERE r.edge_id IS NOT NULL RETURN count(DISTINCT type(r))"), "evidence_nodes": one("MATCH (e:Evidence) RETURN count(e)"),
                "article_nodes": one("MATCH (a:Article) RETURN count(a)"), "cand_entities": one("MATCH (n:CandEntity) RETURN count(n)"),
                "candidate_edges": one("MATCH (:CandEntity)-[r:CANDIDATE]->(:CandEntity) RETURN count(r)")}


def make_backup(dest_root: Path = BACKUP_DIR, data_dir: Path = NEO_DATA, running=neo4j_running) -> Path:
    """Cold copy + verification. Requires Neo4j to be stopped. Returns the backup directory (with manifest.json, verified=true) or raises Blocked."""
    if running():
        raise Blocked("Neo4j is running: a consistent cold backup needs it stopped (stop it with scripts/stop-neo4j.ps1)")
    if not data_dir.exists():
        raise Blocked(f"Neo4j data dir not found: {data_dir}")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_root / stamp
    shutil.copytree(data_dir, dest / "data")
    files = []
    for p in sorted(data_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(data_dir)
            c = dest / "data" / rel
            if not c.exists():
                raise Blocked(f"backup missing file {rel}")
            a, b = sha256(p), sha256(c)
            if a != b or p.stat().st_size != c.stat().st_size:
                raise Blocked(f"backup verification failed for {rel}")
            files.append({"path": str(rel), "size": p.stat().st_size, "sha256": a})
    man = {"created_at": now(), "source": str(data_dir), "kind": "cold copy of the Neo4j data directory (database stopped)", "files": files, "total_bytes": sum(f["size"] for f in files),
           "verified": True, "legacy_stats": None, "restore": f"stop Neo4j, move runtime\\neo4j\\data aside, copy {dest}\\data to runtime\\neo4j\\data, start Neo4j"}
    (dest / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    return dest


def latest_verified_backup(dest_root: Path = BACKUP_DIR) -> tuple[Path, dict] | None:
    for d in sorted(dest_root.glob("*"), reverse=True) if dest_root.exists() else []:
        m = d / "manifest.json"
        if m.exists():
            man = json.loads(m.read_text(encoding="utf-8"))
            if man.get("verified"):
                return d, man
    return None


def reverify_backup(d: Path, man: dict) -> bool:
    return all((d / "data" / f["path"]).exists() and sha256(d / "data" / f["path"]) == f["sha256"] for f in man["files"])


# ------------------------------------------------------------------------------------------------ data selection (read-only from the aggregate)
def collect_validated(agg_db: Path) -> dict:
    db = sqlite3.connect(f"file:{Path(agg_db).as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        edges = [dict(r) for r in db.execute("SELECT * FROM edges WHERE tier='QA_PASS' ORDER BY edge_id")]
        if not edges:
            return {"edges": [], "entities": {}, "evidence": {}, "other_tiers": {}}
        ents = {r["entity_key"]: dict(r) for r in db.execute("SELECT * FROM entities")}
        keys = {k for e in edges for k in (e["subject_key"], e["object_key"])}
        evidence: dict[str, list[dict]] = {}
        for r in db.execute("SELECT * FROM evidence WHERE tier='QA_PASS' ORDER BY edge_id, article_id, evidence_start"):
            evidence.setdefault(r["edge_id"], []).append(dict(r))
        other: dict[tuple, set] = {}
        for r in db.execute("SELECT subject_key, predicate, object_key, tier FROM edges WHERE tier<>'QA_PASS'"):
            other.setdefault((r[0], r[1], r[2]), set()).add(r[3])
        return {"edges": edges, "entities": {k: ents[k] for k in keys}, "evidence": evidence, "other_tiers": other}
    finally:
        db.close()


def evidence_id(edge_id: str, r: dict) -> str:
    return hashlib.sha1(f"{edge_id}|{r['article_id']}|{r['evidence_start']}|{r['evidence_end']}".encode()).hexdigest()[:16]


def build_rows(data: dict) -> dict:
    nodes: dict[str, list[dict]] = {}
    for k, e in data["entities"].items():
        lab = V_LABELS.get(e["entity_type"] or "", "VOrganization")
        nodes.setdefault(lab, []).append({"entity_id": k, "registry_id": e["entity_id"], "name": e["name"] or k, "entity_type": e["entity_type"] or "", "identity_status": e["resolution_status"] or ""})
    edges: dict[str, list[dict]] = {}
    arts: dict[str, str] = {}
    evs = []
    for e in data["edges"]:
        if e["predicate"] not in PREDICATES:
            continue
        ev = data["evidence"].get(e["edge_id"], [])
        rows = [{"evidence_id": evidence_id(e["edge_id"], r), "edge_id": e["edge_id"], "article_id": r["article_id"], "text": r["evidence_text"], "start": r["evidence_start"], "end": r["evidence_end"],
                 "method": r["extraction_method"], "url": r["source_url"] or ""} for r in ev]
        for r in rows:
            arts[r["article_id"]] = r["url"]
        evs += rows
        edges.setdefault(e["predicate"], []).append({
            "s": e["subject_key"], "o": e["object_key"], "edge_id": e["edge_id"], "factual_status": e["factual_status"], "valid_from": e["valid_from"], "valid_to": e["valid_to"], "n_evidence": len(rows),
            "n_articles": e["n_articles"], "evidence_ids": [r["evidence_id"] for r in rows], "other_tiers": sorted(data["other_tiers"].get((e["subject_key"], e["predicate"], e["object_key"]), [])),
            "methods": json.loads(e["discovery_methods"] or "[]")})
    return {"nodes": nodes, "edges": edges, "articles": [{"article_id": a, "url": u} for a, u in sorted(arts.items())], "evidence": evs}


# ------------------------------------------------------------------------------------------------ plan (read-only) and apply (MERGE)
def plan(driver, rows: dict) -> dict:
    with driver.session() as s:
        have_nodes = {r[0] for r in s.run("MATCH (n:VEntity) RETURN n.entity_id")} if rows["nodes"] else set()
        have_edges = {r[0] for r in s.run("MATCH (:VEntity)-[r]->(:VEntity) WHERE r.layer = $l RETURN r.edge_id", l=LAYER)}
        have_ev = {r[0] for r in s.run("MATCH (e:VEvidence) RETURN e.evidence_id")}
        legacy_ids = {r[0] for r in s.run("MATCH (n:Entity) RETURN n.entity_id")}
    all_nodes = [n["entity_id"] for v in rows["nodes"].values() for n in v]
    all_edges = [e["edge_id"] for v in rows["edges"].values() for e in v]
    return {"nodes_total": len(all_nodes), "nodes_new": len([n for n in all_nodes if n not in have_nodes]), "edges_total": len(all_edges), "edges_new": len([e for e in all_edges if e not in have_edges]),
            "evidence_total": len(rows["evidence"]), "evidence_new": len([e for e in rows["evidence"] if e["evidence_id"] not in have_ev]),
            "nodes_with_legacy_registry_id": len([n for v in rows["nodes"].values() for n in v if n["registry_id"] in legacy_ids and n["entity_id"] == n["registry_id"]]),
            "edges_with_other_tiers": sum(1 for v in rows["edges"].values() for e in v if e["other_tiers"]), "at": now()}


def apply(driver, rows: dict, batch: int = 500) -> None:
    with driver.session() as s:
        for q in CONSTRAINTS:
            s.run(q)
        for lab, nodes in rows["nodes"].items():
            for i in range(0, len(nodes), batch):
                s.run(f"UNWIND $rows AS r MERGE (n:VEntity {{entity_id: r.entity_id}}) SET n:{lab}, n.registry_id=r.registry_id, n.name=r.name, n.entity_type=r.entity_type, "
                      f"n.identity_status=r.identity_status, n.layer='{LAYER}'", rows=nodes[i:i + batch])
        for i in range(0, len(rows["articles"]), batch):
            s.run("UNWIND $rows AS r MERGE (a:VArticle {article_id: r.article_id}) SET a.url = r.url", rows=rows["articles"][i:i + batch])
        for pred, edges in rows["edges"].items():
            for i in range(0, len(edges), batch):
                s.run(f"UNWIND $rows AS r MATCH (a:VEntity {{entity_id: r.s}}), (b:VEntity {{entity_id: r.o}}) MERGE (a)-[x:{pred} {{edge_id: r.edge_id}}]->(b) "
                      f"SET x.layer='{LAYER}', x.tier='QA_PASS', x.official=false, x.gold=false, x.derived=false, x.factual_status=r.factual_status, x.valid_from=r.valid_from, "
                      "x.valid_to=r.valid_to, x.evidence_count=r.n_evidence, x.article_count=r.n_articles, x.evidence_ids=r.evidence_ids, x.other_tiers=r.other_tiers, x.methods=r.methods",
                      rows=edges[i:i + batch])
        for i in range(0, len(rows["evidence"]), batch):
            s.run("UNWIND $rows AS r MERGE (v:VEvidence {evidence_id: r.evidence_id}) SET v.edge_id=r.edge_id, v.text=r.text, v.start=r.start, v.end=r.end, v.method=r.method "
                  "WITH v, r MATCH (a:VArticle {article_id: r.article_id}) MERGE (v)-[:FROM]->(a)", rows=rows["evidence"][i:i + batch])
        # read-only pointer from a validated node to the legacy node with the same registry id (new relationship only; no legacy property is written)
        s.run("MATCH (v:VEntity) WHERE v.entity_id = v.registry_id MATCH (e:Entity {entity_id: v.entity_id}) MERGE (v)-[x:SAME_REGISTRY_ID]->(e) SET x.derived=true")


def layer_stats(driver) -> dict:
    with driver.session() as s:
        one = lambda q: s.run(q).single()[0]
        return {"v_nodes": one("MATCH (n:VEntity) RETURN count(n)"), "v_edges": one("MATCH (:VEntity)-[r]->(:VEntity) WHERE r.layer='QA_VALIDATED' RETURN count(r)"),
                "v_relation_types": one("MATCH (:VEntity)-[r]->(:VEntity) WHERE r.layer='QA_VALIDATED' RETURN count(DISTINCT type(r))"), "v_evidence": one("MATCH (e:VEvidence) RETURN count(e)"),
                "v_articles": one("MATCH (a:VArticle) RETURN count(a)"), "same_registry_links": one("MATCH (:VEntity)-[x:SAME_REGISTRY_ID]->(:Entity) RETURN count(x)")}


# ------------------------------------------------------------------------------------------------ orchestration
def sync(agg_db: Path = AGG_DB, backup_dir: Path = BACKUP_DIR, out_dir: Path | None = None, *, running=neo4j_running, start=lambda: ps_script("start-neo4j.ps1"), stop=lambda: ps_script("stop-neo4j.ps1"),
         connect_fn=connect, data_dir: Path = NEO_DATA) -> dict:
    """Backup (if none verified) -> start Neo4j -> legacy check -> dry-run plan -> MERGE -> legacy check again -> second plan must show nothing new. Leaves Neo4j as it found it.
    Returns a result dict; raises Blocked when a safety condition fails (nothing is then written)."""
    result: dict = {"started_at": now()}
    was_running = running()
    bk = latest_verified_backup(backup_dir)
    if bk is None:
        if was_running and (stop() != 0 or running()):
            raise Blocked("cannot stop Neo4j to take the cold backup")
        d = make_backup(backup_dir, data_dir, running)
        bk = (d, json.loads((d / "manifest.json").read_text(encoding="utf-8")))
        result["backup_created"] = str(d)
    d, man = bk
    if not reverify_backup(d, man):
        raise Blocked(f"backup {d} no longer verifies (hash mismatch)")
    result["backup"] = str(d)
    if not running() and start() != 0:
        raise Blocked("could not start Neo4j")
    drv = connect_fn()
    try:
        drv.verify_connectivity()
        ls = legacy_stats(drv)
        if man.get("legacy_stats") is None:
            man["legacy_stats"] = ls  # first connection after the backup, before any write of ours
            (d / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
        if ls != man["legacy_stats"]:
            raise Blocked(f"legacy graph differs from the backup-time stats: {ls} != {man['legacy_stats']}")
        result["legacy_before"] = ls
        rows = build_rows(collect_validated(agg_db))
        p = plan(drv, rows)
        result["dry_run"] = p
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"neo4j_plan_{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(p, indent=1), encoding="utf-8")
        apply(drv, rows)
        after = legacy_stats(drv)
        if after != ls:
            raise Blocked(f"LEGACY GRAPH CHANGED after sync: {after} != {ls}")
        p2 = plan(drv, rows)
        result.update(legacy_after=after, layer=layer_stats(drv), second_plan=p2, idempotent=(p2["nodes_new"], p2["edges_new"], p2["evidence_new"]) == (0, 0, 0))
        return result
    finally:
        drv.close()
        if not was_running and running():
            stop()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="neo4j_validated")
    ap.add_argument("cmd", choices=["backup", "plan", "sync", "verify"])
    ap.add_argument("--agg", default=str(AGG_DB))
    a = ap.parse_args(argv)
    try:
        if a.cmd == "backup":
            print(make_backup())
        elif a.cmd == "verify":
            bk = latest_verified_backup()
            print(json.dumps({"backup": str(bk[0]) if bk else None, "verifies": bool(bk and reverify_backup(*bk))}))
        elif a.cmd == "plan":
            drv = connect()
            print(json.dumps(plan(drv, build_rows(collect_validated(Path(a.agg)))), indent=1))
        else:
            print(json.dumps(sync(Path(a.agg), out_dir=ROOT / "data/campaign/mass/neo4j"), indent=1, default=str))
    except Blocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 6
    return 0


if __name__ == "__main__":
    sys.exit(main())
