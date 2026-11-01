"""Phase 6E.1 - cross-batch staging graph aggregation (read-only over sources; no NLP, no crawl, no Neo4j, no registry writes).

Sources (registered in the aggregate DB; nothing is read twice, nothing is modified):
  baseline_legacy  Phase 5/6 export = `neo4j_sync.collect` over dev44 + holdout19 + new144 (the same 44 official / 31 candidate edges that were loaded into
                   Neo4j; person consolidation is the existing logged rule: same normalized name AND shared organisation)
  job:<job_id>     a COMPLETED Phase 6C/6D pipeline job: its `pipeline.sqlite` staging tables (QA decision per edge + all evidence)
Quality tiers are kept SEPARATE and never promoted into each other: LEGACY_OFFICIAL, LEGACY_CANDIDATE, QA_PASS, QUARANTINE, REJECT. None of them is gold.
An aggregated edge row is keyed by (edge_id, tier); edge_id = hash(canonical subject key, predicate, canonical object key, factual_status, valid_from, valid_to).
Entities are keyed by their registry ids (merges already recorded in a source's registry are honoured). NOTHING else is merged: no same-name persons, no
similar-name companies, no PROVISIONAL entities across articles. Such pairs are reported as unresolved collisions. The same id carrying a different type
or normalized name in two sources is an ID_CONFLICT and the two are kept apart (key = id@source).
Idempotent: a source is re-ingested only if its content fingerprint changed (rows of that source are REPLACED, never appended); the aggregate tables are
rebuilt deterministically from all enabled sources in one transaction.

  python -m vckg.graph.aggregate run [--out data/aggregate]        (register defaults if needed, ingest, aggregate, export, report)
  python -m vckg.graph.aggregate add-job --job-id J [--include-test-jobs]
  python -m vckg.graph.aggregate disable --source job:J            (keeps rows; excluded from the aggregate)
  python -m vckg.graph.aggregate list | verify"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import networkx as nx
from rapidfuzz import fuzz

from vckg.entity_linking.normalize import normalize_name
from vckg.graph.neo4j_sync import collect

ROOT = Path(__file__).resolve().parents[3]
PIPE = ROOT / "data/pipeline"
OUT = ROOT / "data/aggregate"
REPORT_DIR = ROOT / "reports/phase6e"
BASELINE_ID = "baseline_legacy"
BASELINE_RUNS = ["dev44", "holdout19", "new144"]
BASELINE_REGS = ["registry_p5_dev.sqlite", "registry_p5_holdout.sqlite", "registry_p5_new.sqlite"]
DEFAULT_JOBS = ["pilot6d"]
TIERS = ("LEGACY_OFFICIAL", "QA_PASS", "QUARANTINE", "REJECT", "LEGACY_CANDIDATE")
VALIDATED_TIERS = ("LEGACY_OFFICIAL", "QA_PASS")
STATUS_RANK = {"VERIFIED": 4, "EXTERNAL_VERIFIED": 4, "ARTICLE_GROUNDED": 3, "PROVISIONAL": 2, "AMBIGUOUS": 1}
TEST_JOB = re.compile(r"^(smoke|test|tmp)|(-|_)(rerun|err|trial)$", re.IGNORECASE)
NEAR_DUP_RATIO = 92  # token-sort ratio on normalized names; used ONLY to report candidates for human review

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(source_id TEXT PRIMARY KEY, kind TEXT NOT NULL, params TEXT, fingerprint TEXT, ingested_at TEXT, enabled INTEGER NOT NULL DEFAULT 1,
  n_edges INTEGER, n_evidence INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS src_edges(source_id TEXT NOT NULL, edge_id TEXT NOT NULL, tier TEXT NOT NULL, subject_id TEXT NOT NULL, subject_name TEXT, subject_type TEXT,
  subject_status TEXT, predicate TEXT NOT NULL, object_id TEXT NOT NULL, object_name TEXT, object_type TEXT, object_status TEXT, factual_status TEXT NOT NULL,
  valid_from TEXT NOT NULL DEFAULT '', valid_to TEXT NOT NULL DEFAULT '', decision TEXT, quarantine_class TEXT, discovery_method TEXT, derived INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(source_id, edge_id, tier));
CREATE TABLE IF NOT EXISTS src_evidence(source_id TEXT NOT NULL, edge_id TEXT NOT NULL, tier TEXT NOT NULL, article_id TEXT NOT NULL, evidence_start INTEGER NOT NULL,
  evidence_end INTEGER NOT NULL, evidence_text TEXT, source_url TEXT, extraction_method TEXT, published_at TEXT, review_status TEXT,
  PRIMARY KEY(source_id, edge_id, tier, article_id, evidence_start, evidence_end));
CREATE TABLE IF NOT EXISTS src_merges(source_id TEXT NOT NULL, kept TEXT, dropped TEXT, reason TEXT);
"""
AGG_TABLES = ("entities", "edges", "evidence", "collisions")
AGG_SCHEMA = """
DROP TABLE IF EXISTS entities; DROP TABLE IF EXISTS edges; DROP TABLE IF EXISTS evidence; DROP TABLE IF EXISTS collisions;
CREATE TABLE entities(entity_key TEXT PRIMARY KEY, entity_id TEXT NOT NULL, name TEXT, entity_type TEXT, name_key TEXT, resolution_status TEXT, statuses TEXT, sources TEXT, tiers TEXT, id_conflict INTEGER NOT NULL);
CREATE TABLE edges(edge_id TEXT NOT NULL, tier TEXT NOT NULL, subject_key TEXT NOT NULL, predicate TEXT NOT NULL, object_key TEXT NOT NULL, factual_status TEXT NOT NULL,
  valid_from TEXT NOT NULL, valid_to TEXT NOT NULL, quarantine_classes TEXT, discovery_methods TEXT, sources TEXT, n_evidence INTEGER, n_articles INTEGER, derived INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(edge_id, tier));
CREATE TABLE evidence(edge_id TEXT NOT NULL, tier TEXT NOT NULL, article_id TEXT NOT NULL, evidence_start INTEGER NOT NULL, evidence_end INTEGER NOT NULL, evidence_text TEXT, source_url TEXT,
  extraction_method TEXT, published_at TEXT, review_status TEXT, sources TEXT, PRIMARY KEY(edge_id, tier, article_id, evidence_start, evidence_end));
CREATE TABLE collisions(kind TEXT NOT NULL, key TEXT NOT NULL, detail TEXT, resolved INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(kind, key));
"""


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def j(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def src_edge_id(s: str, p: str, o: str, status: str, vf: str, vt: str) -> str:
    return sha(s, p, o, status, vf or "", vt or "")


class Agg:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(str(path), timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ------------------------------------------------------------------ source registry
    def register(self, source_id: str, kind: str, params: dict) -> bool:
        cur = self.db.execute("INSERT OR IGNORE INTO sources(source_id,kind,params) VALUES(?,?,?)", (source_id, kind, j(params)))
        self.db.commit()
        return bool(cur.rowcount)

    def sources(self, enabled_only: bool = False) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM sources" + (" WHERE enabled=1" if enabled_only else "") + " ORDER BY source_id"))

    def set_enabled(self, source_id: str, flag: bool) -> None:
        if not self.db.execute("UPDATE sources SET enabled=? WHERE source_id=?", (int(flag), source_id)).rowcount:
            raise SystemExit(f"unknown source {source_id}")
        self.db.commit()

    # ------------------------------------------------------------------ ingest (replace by source, only when content changed)
    def _replace(self, source_id: str, fingerprint: str, edges: list[tuple], evidence: list[tuple], merges: list[tuple], note: str = "") -> str:
        cur = self.db.execute("SELECT fingerprint FROM sources WHERE source_id=?", (source_id,)).fetchone()
        if cur and cur["fingerprint"] == fingerprint:
            return "UNCHANGED"
        with self.db:
            for t in ("src_edges", "src_evidence", "src_merges"):
                self.db.execute(f"DELETE FROM {t} WHERE source_id=?", (source_id,))
            self.db.executemany("INSERT OR IGNORE INTO src_edges VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", edges)
            self.db.executemany("INSERT OR IGNORE INTO src_evidence VALUES(?,?,?,?,?,?,?,?,?,?,?)", evidence)
            self.db.executemany("INSERT INTO src_merges VALUES(?,?,?,?)", merges)
            ne = self.db.execute("SELECT COUNT(*) FROM src_edges WHERE source_id=?", (source_id,)).fetchone()[0]
            nv = self.db.execute("SELECT COUNT(*) FROM src_evidence WHERE source_id=?", (source_id,)).fetchone()[0]
            self.db.execute("UPDATE sources SET fingerprint=?, ingested_at=?, n_edges=?, n_evidence=?, note=? WHERE source_id=?", (fingerprint, now(), ne, nv, note, source_id))
        return "REPLACED" if cur and cur["fingerprint"] else "INGESTED"

    def ingest_baseline(self, root: Path = ROOT) -> str:
        runs = [root / "data/outputs/phase5" / r for r in BASELINE_RUNS]
        regs = [root / "data/registry" / r for r in BASELINE_REGS]
        off, cand, info, _ = collect(runs, regs)
        merges = getattr(collect, "last_merges", [])
        edges, evid = [], []
        for tier, lst in (("LEGACY_OFFICIAL", off), ("LEGACY_CANDIDATE", cand)):
            groups: dict[tuple, list[dict]] = defaultdict(list)
            for e in lst:  # one aggregated row per (s,p,o,status,window); a legacy edge never mixes statuses in practice (checked), but split if it did
                for r in e["evidence"]:
                    groups[(e["subject_id"], e["predicate"], e["object_id"], r.get("factual_status") or "UNKNOWN", r.get("valid_from") or "", r.get("valid_to") or "")].append(r)
            for (s, p, o, st, vf, vt), rs in groups.items():
                eid = src_edge_id(s, p, o, st, vf, vt)
                si, oi = info.get(s, {}), info.get(o, {})
                edges.append((BASELINE_ID, eid, tier, s, si.get("name"), si.get("type"), si.get("status"), p, o, oi.get("name"), oi.get("type"), oi.get("status"), st, vf, vt,
                              tier, None, "RULE+QWEN_VERIFIER", 0))
                for r in rs:
                    evid.append((BASELINE_ID, eid, tier, r["article_id"], r["evidence_start"], r["evidence_end"], r.get("evidence_text"), r.get("source_url"),
                                 r.get("extraction_method"), r.get("published_at"), r.get("review_status")))
        mg = [(BASELINE_ID, m["keep"], m["drop"], f"same name_key '{m['name_key']}' + shared org {m['shared_orgs']}") for m in merges]
        fp = sha(j(sorted((e[1], e[2]) for e in edges)), j(sorted((v[1], v[3], v[4], v[5]) for v in evid)), j(sorted(m[1:3] for m in mg)))
        return self._replace(BASELINE_ID, fp, edges, evid, mg, "legacy official + legacy candidate, same data as the Neo4j baseline (74 nodes / 44 official)")

    def ingest_job(self, job_id: str, pipe: Path = PIPE, include_test: bool = False, allow_incomplete: bool = False) -> str:
        if TEST_JOB.search(job_id) and not include_test:
            raise SystemExit(f"job {job_id} looks like a smoke/test/rerun job: refused (use --include-test-jobs only deliberately)")
        d = pipe / job_id
        st = json.loads((d / "status.json").read_text(encoding="utf-8")) if (d / "status.json").exists() else {}
        if st.get("state") != "COMPLETED" and not allow_incomplete:
            raise SystemExit(f"job {job_id} state is {st.get('state')!r}, not COMPLETED (use --allow-incomplete to ingest finished articles only)")
        db = sqlite3.connect(f"file:{(d / 'pipeline.sqlite').as_posix()}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            ents = {r["entity_id"]: r for r in db.execute("SELECT * FROM staging_entities")}
            edges, evid = [], []
            for r in db.execute("SELECT * FROM staging_edges ORDER BY edge_key"):
                dec = r["decision"]
                tier = "QA_PASS" if dec in ("PASS", "AUTO_CORRECT") else dec if dec in ("QUARANTINE", "REJECT") else None
                if tier is None:
                    raise SystemExit(f"unknown QA decision {dec!r} in {job_id}")
                s, o = r["subject_id"], r["object_id"]
                eid = src_edge_id(s, r["predicate"], o, r["factual_status"], r["valid_from"], r["valid_to"])
                es, eo = ents.get(s), ents.get(o)
                edges.append((f"job:{job_id}", eid, tier, s, r["subject_name"], r["subject_type"], es["resolution_status"] if es else None, r["predicate"], o, r["object_name"],
                              r["object_type"], eo["resolution_status"] if eo else None, r["factual_status"], r["valid_from"] or "", r["valid_to"] or "", dec, r["quarantine_class"],
                              r["discovery_method"], int(dict(r).get("derived") or 0)))
                for ev in db.execute("SELECT * FROM staging_evidence WHERE edge_key=? ORDER BY article_id, evidence_start", (r["edge_key"],)):
                    evid.append((f"job:{job_id}", eid, tier, ev["article_id"], ev["evidence_start"], ev["evidence_end"], ev["evidence_text"], ev["source_url"], ev["extraction_method"], None, "NOT_REVIEWED"))
        finally:
            db.close()
        fp = sha(j(sorted((e[1], e[2], e[15], e[16]) for e in edges)), j(sorted((v[1], v[3], v[4], v[5]) for v in evid)))
        return self._replace(f"job:{job_id}", fp, edges, evid, [], f"pipeline job state={st.get('state')}")

    # ------------------------------------------------------------------ aggregate (deterministic rebuild from enabled sources)
    def aggregate(self) -> dict:
        en = [r["source_id"] for r in self.sources(True)]
        if not en:
            raise SystemExit("no enabled source")
        q = ",".join("?" * len(en))
        rows = [dict(r) for r in self.db.execute(f"SELECT * FROM src_edges WHERE source_id IN ({q}) ORDER BY source_id, tier, edge_id", en)]
        evs = [dict(r) for r in self.db.execute(f"SELECT * FROM src_evidence WHERE source_id IN ({q}) ORDER BY source_id, tier, edge_id, article_id, evidence_start", en)]
        # ---- entity observations per (id, source) and ID conflicts (same id, different type or normalized name)
        obs: dict[str, dict[str, dict]] = defaultdict(dict)
        for r in rows:
            for role in ("subject", "object"):
                eid = r[f"{role}_id"]
                t, nm = r[f"{role}_type"], r[f"{role}_name"] or eid
                o = obs[eid].setdefault(r["source_id"], {"type": t, "name": nm, "statuses": set(), "tiers": set()})
                o["statuses"].add(r[f"{role}_status"] or "UNKNOWN")
                o["tiers"].add(r["tier"])
        conflict_ids: set[str] = set()
        collisions: list[tuple] = []
        for eid, per in obs.items():
            sig = {(v["type"], normalize_name(v["name"], is_person=v["type"] == "PERSON")) for v in per.values()}
            if len(sig) > 1:
                conflict_ids.add(eid)
                collisions.append(("ID_CONFLICT", eid, j({"observations": {s: {"type": v["type"], "name": v["name"]} for s, v in per.items()},
                                                        "action": "kept apart as id@source; not merged"}), 0))

        def ekey(eid: str, source: str) -> str:
            return f"{eid}@{source}" if eid in conflict_ids else eid
        ent_rows: dict[str, dict] = {}
        for eid, per in obs.items():
            for source, v in per.items():
                k = ekey(eid, source)
                e = ent_rows.setdefault(k, {"entity_id": eid, "name": v["name"], "type": v["type"], "statuses": set(), "sources": set(), "tiers": set()})
                e["statuses"] |= v["statuses"]
                e["sources"].add(source)
                e["tiers"] |= v["tiers"]
        # ---- edges: unique (edge_id, tier); evidence deduped by (edge, tier, article, span)
        edges: dict[tuple, dict] = {}
        raw_edges = len(rows)
        for r in rows:
            sk, ok = ekey(r["subject_id"], r["source_id"]), ekey(r["object_id"], r["source_id"])
            eid = src_edge_id(sk, r["predicate"], ok, r["factual_status"], r["valid_from"], r["valid_to"])
            e = edges.setdefault((eid, r["tier"]), {"edge_id": eid, "tier": r["tier"], "subject_key": sk, "predicate": r["predicate"], "object_key": ok, "factual_status": r["factual_status"],
                                                    "valid_from": r["valid_from"], "valid_to": r["valid_to"], "qc": set(), "dm": set(), "sources": set(), "derived": r["derived"]})
            e["sources"].add(r["source_id"])
            if r["quarantine_class"]:
                e["qc"].add(r["quarantine_class"])
            if r["discovery_method"]:
                e["dm"].add(r["discovery_method"])
        local2agg = {(r["source_id"], r["edge_id"], r["tier"]): src_edge_id(ekey(r["subject_id"], r["source_id"]), r["predicate"], ekey(r["object_id"], r["source_id"]), r["factual_status"], r["valid_from"], r["valid_to"]) for r in rows}
        ev: dict[tuple, dict] = {}
        raw_ev = len(evs)
        for x in evs:
            eid = local2agg[(x["source_id"], x["edge_id"], x["tier"])]
            k = (eid, x["tier"], x["article_id"], x["evidence_start"], x["evidence_end"])
            e = ev.setdefault(k, {**{c: x[c] for c in ("evidence_text", "source_url", "extraction_method", "published_at", "review_status")}, "sources": set()})
            e["sources"].add(x["source_id"])
            if not e["source_url"] and x["source_url"]:
                e["source_url"] = x["source_url"]
        per_edge_ev: dict[tuple, set] = defaultdict(set)
        for (eid, tier, art, _s, _e) in ev:
            per_edge_ev[(eid, tier)].add(art)
        n_ev = Counter((k[0], k[1]) for k in ev)
        # ---- unresolved identity collisions (reported, NEVER merged)
        used = {e["subject_key"] for e in edges.values()} | {e["object_key"] for e in edges.values()}
        used_ents = {k: v for k, v in ent_rows.items() if k in used}
        names = {k: normalize_name(v["name"], is_person=v["type"] == "PERSON") for k, v in used_ents.items()}
        by_name: dict[tuple, list[str]] = defaultdict(list)
        for k, nm in names.items():
            by_name[(used_ents[k]["type"] == "PERSON", nm)].append(k)
        for (is_p, nm), ks in sorted(by_name.items(), key=lambda t: (t[0][0], t[0][1])):
            if len(ks) > 1 and nm:
                prov = [k for k in ks if "PROVISIONAL" in used_ents[k]["statuses"]]
                collisions.append(("SAME_NAME_PERSONS_UNMERGED" if is_p else "SAME_NAME_ORGS_DIFFERENT_ID", nm,
                                   j({"entity_keys": sorted(ks), "provisional_among": sorted(prov), "action": "not merged: needs evidence/human decision"}), 0))
        orgs = sorted(k for k, v in used_ents.items() if v["type"] != "PERSON" and names[k])
        seen_pairs: set[tuple] = set()
        for a, b in itertools.combinations(orgs, 2):
            if names[a] == names[b] or (a, b) in seen_pairs:
                continue
            if used_ents[a]["type"] == "BOND_ISSUE" or used_ents[b]["type"] == "BOND_ISSUE":
                continue
            if fuzz.token_sort_ratio(names[a], names[b]) >= NEAR_DUP_RATIO:
                seen_pairs.add((a, b))
                collisions.append(("SIMILAR_NAME_ORGS_UNMERGED", f"{a}||{b}", j({"names": [used_ents[a]["name"], used_ents[b]["name"]], "ratio": round(fuzz.token_sort_ratio(names[a], names[b]), 1),
                                                                                  "action": "not merged: fuzzy similarity is only a review hint"}), 0))
        # ---- write (single transaction)
        with self.db:
            self.db.executescript(AGG_SCHEMA)
            for k in sorted(ent_rows):
                v = ent_rows[k]
                worst = min(sorted(v["statuses"]), key=lambda s: STATUS_RANK.get(s, 0))  # most CONSERVATIVE status across sources (never upgraded by another source)
                self.db.execute("INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,?,?)", (k, v["entity_id"], v["name"], v["type"], names.get(k) or normalize_name(v["name"], is_person=v["type"] == "PERSON"),
                                                                                      worst, j(sorted(v["statuses"])), j(sorted(v["sources"])), j(sorted(v["tiers"])), int(v["entity_id"] in conflict_ids)))
            for (eid, tier), e in sorted(edges.items()):
                self.db.execute("INSERT INTO edges VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (eid, tier, e["subject_key"], e["predicate"], e["object_key"], e["factual_status"], e["valid_from"], e["valid_to"],
                                                                                          j(sorted(e["qc"])), j(sorted(e["dm"])), j(sorted(e["sources"])), n_ev[(eid, tier)], len(per_edge_ev[(eid, tier)]), e["derived"]))
            for k in sorted(ev):
                x = ev[k]
                self.db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?)", (*k, x["evidence_text"], x["source_url"], x["extraction_method"], x["published_at"], x["review_status"], j(sorted(x["sources"]))))
            for c in sorted(collisions):
                self.db.execute("INSERT OR REPLACE INTO collisions VALUES(?,?,?,?)", c)
        return {"raw_edge_rows": raw_edges, "raw_evidence_rows": raw_ev, "unique_edges": len(edges), "unique_evidence": len(ev), "sources": en}

    # ------------------------------------------------------------------ metrics / export
    def content_hash(self) -> str:
        h = hashlib.sha256()
        for t, order in (("entities", "entity_key"), ("edges", "edge_id,tier"), ("evidence", "edge_id,tier,article_id,evidence_start,evidence_end"), ("collisions", "kind,key")):
            for r in self.db.execute(f"SELECT * FROM {t} ORDER BY {order}"):
                h.update(json.dumps(list(r), ensure_ascii=False, default=str).encode())
        return h.hexdigest()[:16]

    def graph(self, tiers: tuple[str, ...]) -> nx.MultiDiGraph:
        g = nx.MultiDiGraph()
        q = ",".join("?" * len(tiers))
        for r in self.db.execute(f"SELECT * FROM edges WHERE tier IN ({q}) ORDER BY edge_id, tier", tiers):
            for k in (r["subject_key"], r["object_key"]):
                if k not in g:
                    e = self.db.execute("SELECT * FROM entities WHERE entity_key=?", (k,)).fetchone()
                    g.add_node(k, name=e["name"] or "", entity_type=e["entity_type"] or "", resolution_status=e["resolution_status"] or "", id_conflict=e["id_conflict"])
            g.add_edge(r["subject_key"], r["object_key"], key=f"{r['edge_id']}:{r['tier']}", edge_id=r["edge_id"], tier=r["tier"], predicate=r["predicate"], factual_status=r["factual_status"],
                       n_evidence=r["n_evidence"], n_articles=r["n_articles"], derived=bool(r["derived"]))
        return g

    def metrics(self) -> dict:
        q = lambda s, *a: self.db.execute(s, a).fetchall()
        per_tier = {}
        for t in TIERS:
            e = q("SELECT predicate, COUNT(*) n FROM edges WHERE tier=? GROUP BY predicate ORDER BY predicate", t)
            per_tier[t] = {"unique_edges": sum(r["n"] for r in e), "relation_types": len(e), "by_predicate": {r["predicate"]: r["n"] for r in e},
                           "unique_nodes": len({x for r in q("SELECT subject_key, object_key FROM edges WHERE tier=?", t) for x in (r[0], r[1])}),
                           "evidence": q("SELECT COUNT(*) FROM evidence WHERE tier=?", t)[0][0], "articles": q("SELECT COUNT(DISTINCT article_id) FROM evidence WHERE tier=?", t)[0][0],
                           "by_status": {r[0]: r[1] for r in q("SELECT factual_status, COUNT(*) FROM edges WHERE tier=? GROUP BY 1", t)}}
            if t == "QUARANTINE":
                per_tier[t]["by_class"] = dict(Counter(c for r in q("SELECT quarantine_classes FROM edges WHERE tier='QUARANTINE'") for c in (json.loads(r[0]) or ["(none)"])))
        union = ("LEGACY_OFFICIAL", "QA_PASS")
        nodes_v = {x for r in q("SELECT subject_key, object_key FROM edges WHERE tier IN (?,?)", *union) for x in (r[0], r[1])}
        nodes_all = {x for r in q("SELECT subject_key, object_key FROM edges") for x in (r[0], r[1])}
        pred_v = {r[0] for r in q("SELECT predicate FROM edges WHERE tier IN (?,?)", *union)}
        pred_all = {r[0] for r in q("SELECT predicate FROM edges")}
        comp = {}
        for name, tiers in (("legacy_official", ("LEGACY_OFFICIAL",)), ("qa_pass", ("QA_PASS",)), ("validated_union(legacy_official+qa_pass)", union), ("all_tiers", TIERS)):
            u = self.graph(tiers).to_undirected()
            cs = sorted((len(c) for c in nx.connected_components(u)), reverse=True)
            comp[name] = {"nodes": u.number_of_nodes(), "edges_multigraph": u.number_of_edges(), "components": len(cs), "largest": cs[0] if cs else 0, "sizes_top5": cs[:5],
                          "singleton_components": sum(1 for c in cs if c == 1)}
        overlap = {}
        trip = {t: {(r["subject_key"], r["predicate"], r["object_key"]) for r in q("SELECT * FROM edges WHERE tier=?", t)} for t in TIERS}
        for a, b in itertools.combinations(TIERS, 2):
            n = len(trip[a] & trip[b])
            if n:
                overlap[f"{a} & {b}"] = n
        coll = Counter(r["kind"] for r in q("SELECT kind FROM collisions"))
        by_src = {}
        for s in self.sources(True):
            by_src[s["source_id"]] = {"edge_rows": q("SELECT COUNT(*) FROM src_edges WHERE source_id=?", s["source_id"])[0][0], "by_tier": {r[0]: r[1] for r in q("SELECT tier, COUNT(*) FROM src_edges WHERE source_id=? GROUP BY 1", s["source_id"])},
                                      "evidence_rows": q("SELECT COUNT(*) FROM src_evidence WHERE source_id=?", s["source_id"])[0][0], "articles": q("SELECT COUNT(DISTINCT article_id) FROM src_evidence WHERE source_id=?", s["source_id"])[0][0],
                                      "ingested_at": s["ingested_at"], "fingerprint": s["fingerprint"]}
        raw_e = q("SELECT COUNT(*) FROM src_edges WHERE source_id IN (SELECT source_id FROM sources WHERE enabled=1)")[0][0]
        raw_v = q("SELECT COUNT(*) FROM src_evidence WHERE source_id IN (SELECT source_id FROM sources WHERE enabled=1)")[0][0]
        uq_e, uq_v = q("SELECT COUNT(*) FROM edges")[0][0], q("SELECT COUNT(*) FROM evidence")[0][0]
        return {
            "generated_at": now(), "content_hash": self.content_hash(), "sources": by_src, "disabled_sources": [s["source_id"] for s in self.sources() if not s["enabled"]],
            "per_tier": per_tier,
            "unique_domain_nodes": {"validated_union(legacy_official+qa_pass)": len(nodes_v), "all_tiers(incl. quarantine/reject/legacy_candidate)": len(nodes_all),
                                    "by_type_validated": dict(Counter(self.db.execute("SELECT entity_type FROM entities WHERE entity_key=?", (k,)).fetchone()[0] for k in nodes_v))},
            "unique_edges_total_rows(edge,tier)": uq_e, "relation_types": {"validated_union": len(pred_v), "all_tiers": len(pred_all), "validated_list": sorted(pred_v), "all_list": sorted(pred_all)},
            "evidence": {"unique_rows": uq_v, "articles_all_tiers": q("SELECT COUNT(DISTINCT article_id) FROM evidence")[0][0],
                         "articles_validated": q("SELECT COUNT(DISTINCT article_id) FROM evidence WHERE tier IN (?,?)", *union)[0][0],
                         "with_source_url": q("SELECT COUNT(*) FROM evidence WHERE source_url IS NOT NULL AND source_url<>''")[0][0]},
            "duplicates_removed": {"edge_rows_across_sources": raw_e - uq_e, "evidence_rows_across_sources": raw_v - uq_v, "raw_edge_rows": raw_e, "raw_evidence_rows": raw_v,
                                   "person_merges_applied_in_baseline(existing_logged_rule)": q("SELECT COUNT(*) FROM src_merges")[0][0]},
            "triples_present_in_several_tiers": overlap, "identity_collisions_unresolved": {"by_kind": dict(coll), "total": sum(coll.values())},
            "connected_components": comp,
            "notes": ["No gold: LEGACY_OFFICIAL (verifier-based, AUTO_ACCEPTED) and QA_PASS (rule outcome) are NOT ground truth.", "Tiers are never promoted; a triple in two tiers stays in both.",
                      "Collisions are review hints only; nothing was merged by name or fuzzy similarity."]}

    def export(self, out: Path, m: dict) -> dict:
        ex = out / "export"
        ex.mkdir(parents=True, exist_ok=True)
        for name, tiers in (("graph_validated", VALIDATED_TIERS), ("graph_all_tiers", TIERS)):
            nx.write_graphml(self.graph(tiers), ex / f"{name}.graphml")
        def dump(path: Path, sql: str) -> int:
            cur = self.db.execute(sql)
            cols = [d[0] for d in cur.description]
            n = 0
            with path.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(cols)
                for r in cur:
                    w.writerow(list(r))
                    n += 1
            return n
        n = {"nodes": dump(ex / "nodes.csv", "SELECT * FROM entities WHERE entity_key IN (SELECT subject_key FROM edges UNION SELECT object_key FROM edges) ORDER BY entity_key"),
             "edges": dump(ex / "edges.csv", "SELECT * FROM edges ORDER BY tier, edge_id"), "evidence": dump(ex / "evidence.csv", "SELECT * FROM evidence ORDER BY tier, edge_id, article_id, evidence_start"),
             "collisions": dump(ex / "collisions.csv", "SELECT * FROM collisions ORDER BY kind, key")}
        (out / "summary.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        return n


def run_all(out: Path = OUT, pipe: Path = PIPE, jobs: list[dict] | None = None, register_defaults: bool = True, root: Path = ROOT) -> dict:
    ag = Agg(out / "staging_graph.sqlite")
    try:
        if register_defaults and not ag.sources():  # first run only: legacy baseline + pilot6d (smoke/rerun jobs are NOT part of the cumulative data)
            ag.register(BASELINE_ID, "legacy_baseline", {"runs": BASELINE_RUNS, "registries": BASELINE_REGS})
            for jb in DEFAULT_JOBS:
                ag.register(f"job:{jb}", "pipeline_job", {"job_id": jb})
        for jb in jobs or []:
            ag.register(f"job:{jb['job_id']}", "pipeline_job", jb)
        results = {}
        for s in ag.sources(True):
            if s["kind"] == "legacy_baseline":
                results[s["source_id"]] = ag.ingest_baseline(root)
            else:
                p = json.loads(s["params"])
                results[s["source_id"]] = ag.ingest_job(p["job_id"], pipe, bool(p.get("include_test")), bool(p.get("allow_incomplete")))
        agg = ag.aggregate()
        m = ag.metrics()
        m["ingest"] = results
        m["aggregate_run"] = agg
        m["export_rows"] = ag.export(out, m)
        (out / "summary.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        return m
    finally:
        ag.db.close()


def _check_job(a) -> bool:
    if TEST_JOB.search(a.job_id) and not a.include_test_jobs:
        raise SystemExit(f"job {a.job_id} looks like a smoke/test/rerun job: refused (use --include-test-jobs only deliberately)")
    p = PIPE / a.job_id / "status.json"
    st = json.loads(p.read_text(encoding="utf-8")).get("state") if p.exists() else None
    if st != "COMPLETED" and not a.allow_incomplete:
        raise SystemExit(f"job {a.job_id} state is {st!r}, not COMPLETED (use --allow-incomplete to ingest finished articles only)")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aggregate")
    ap.add_argument("--out", default=str(OUT))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    a1 = sub.add_parser("add-job")
    a1.add_argument("--job-id", required=True)
    a1.add_argument("--include-test-jobs", action="store_true")
    a1.add_argument("--allow-incomplete", action="store_true")
    d = sub.add_parser("disable")
    d.add_argument("--source", required=True)
    sub.add_parser("list")
    sub.add_parser("verify")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.cmd == "run":
        m = run_all(out)
        print(json.dumps({k: m[k] for k in ("ingest", "content_hash", "unique_domain_nodes", "duplicates_removed", "identity_collisions_unresolved")}, ensure_ascii=False, indent=1))
    elif a.cmd == "add-job":
        # ingest_job validates (state COMPLETED, not a smoke/test/rerun job) and raises BEFORE anything is registered or written
        m = run_all(out, jobs=[{"job_id": a.job_id, "include_test": a.include_test_jobs, "allow_incomplete": a.allow_incomplete}]) if _check_job(a) else {}
        print(json.dumps({"ingest": m["ingest"], "content_hash": m["content_hash"]}, indent=1))
    elif a.cmd == "disable":
        ag = Agg(out / "staging_graph.sqlite")
        ag.set_enabled(a.source, False)
        ag.db.close()
        print(f"disabled {a.source}; run `run` to rebuild the aggregate without it")
    elif a.cmd == "list":
        ag = Agg(out / "staging_graph.sqlite")
        for s in ag.sources():
            print(f"{s['source_id']:24s} kind={s['kind']:16s} enabled={s['enabled']} edges={s['n_edges']} evidence={s['n_evidence']} ingested={s['ingested_at']}")
        ag.db.close()
    else:  # verify: idempotence (content hash identical after a second full run)
        h1 = run_all(out, register_defaults=False)["content_hash"]
        h2 = run_all(out, register_defaults=False)["content_hash"]
        print(json.dumps({"hash_run1": h1, "hash_run2": h2, "idempotent": h1 == h2}))
        return 0 if h1 == h2 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())


