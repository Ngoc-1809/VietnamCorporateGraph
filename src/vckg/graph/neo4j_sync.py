"""Neo4j sync (Phase 5). Official graph = (:Entity) nodes + typed relationships; candidates live in a SEPARATE namespace.

 * (:Entity:Person|Organization[:Bank|:Regulator|:Authority]|BondIssue) only for entities in OFFICIAL edges
   (pipeline official + HUMAN_VERIFIED). Registry-only identities, articles and evidence are never counted as entities.
 * Relationship type = predicate; props: edge_id, factual_status, valid_from/to, evidence_count, review_state, derived=false.
 * (:Evidence {evidence_id, edge_id}) -[:FROM]-> (:Article); official relationship carries evidence_ids.
 * Candidates: (:CandEntity) -[:CANDIDATE {predicate, edge_id, official:false}]-> (:CandEntity). Never mixed with official.
 * Idempotent: MERGE on stable ids; a candidate promoted to official is removed from the candidate namespace.
Usage: python -m vckg.graph.neo4j_sync {ping|constraints|import|stats|queries|projections} ..."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from vckg.metrics import edge_event_key, unique_edges

ROOT = Path(__file__).resolve().parents[3]
PREDICATES = ["CHAIR_OF", "CEO_OF", "BOARD_MEMBER_OF", "FOUNDED", "OWNS_SHARES_IN", "SUBSIDIARY_OF", "ACQUIRED", "LENDS_TO", "ISSUED_BOND",
              "JOINT_VENTURE_WITH", "PARTNERS_WITH", "SANCTIONED_BY", "PROSECUTED_BY"]
LABELS = {"PERSON": "Person", "ORGANIZATION": "Organization", "BANK": "Organization:Bank", "REGULATOR": "Organization:Regulator",
          "GOVERNMENT_AGENCY": "Organization:Authority", "BOND_ISSUE": "BondIssue"}
CONSTRAINTS = [
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT cand_entity_id IF NOT EXISTS FOR (n:CandEntity) REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.article_id IS UNIQUE",
    "CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.evidence_id IS UNIQUE",
]
QUERIES = {
    "domain_entity_nodes": "MATCH (n:Entity) RETURN count(n) AS entities",
    "official_edges_total": "MATCH (:Entity)-[r]->(:Entity) WHERE r.edge_id IS NOT NULL RETURN count(r) AS official_edges",
    "relation_types": "MATCH (:Entity)-[r]->(:Entity) WHERE r.edge_id IS NOT NULL RETURN type(r) AS predicate, count(*) AS n ORDER BY n DESC",
    "evidence_lookup": "MATCH (s:Entity)-[r]->(o:Entity) WHERE r.edge_id IS NOT NULL WITH s,r,o LIMIT 5 "
                       "MATCH (e:Evidence {edge_id: r.edge_id})-[:FROM]->(a:Article) "
                       "RETURN s.name AS subject, type(r) AS predicate, o.name AS object, e.text AS evidence, a.url AS url LIMIT 10",
    "leaders_of_organization": "MATCH (p:Person)-[r:CHAIR_OF|CEO_OF|BOARD_MEMBER_OF]->(o:Organization) "
                               "RETURN o.name AS organization, collect(DISTINCT p.name + ' (' + type(r) + ')') AS leaders ORDER BY size(leaders) DESC LIMIT 10",
    "shared_leaders_person_person": "MATCH (a:Person)-[:CHAIR_OF|CEO_OF|BOARD_MEMBER_OF]->(o:Organization)<-[:CHAIR_OF|CEO_OF|BOARD_MEMBER_OF]-(b:Person) "
                                    "WHERE a.entity_id < b.entity_id RETURN a.name AS a, b.name AS b, collect(DISTINCT o.name) AS via, true AS derived",
    "shortest_path_between_entities": "MATCH (a:Entity), (b:Entity) WHERE a.entity_id < b.entity_id "
                                      "MATCH p = shortestPath((a)-[*..4]-(b)) WHERE all(x IN relationships(p) WHERE x.edge_id IS NOT NULL) "
                                      "RETURN a.name AS from, b.name AS to, length(p) AS hops ORDER BY hops LIMIT 10",
    "ownership_chain": "MATCH (h:Entity)-[r:OWNS_SHARES_IN|SUBSIDIARY_OF]->(c:Organization) RETURN h.name AS holder, type(r) AS rel, c.name AS company LIMIT 20",
    "enforcement_events": "MATCH (x:Entity)-[r:SANCTIONED_BY|PROSECUTED_BY]->(auth:Entity) RETURN x.name AS subject, type(r) AS rel, auth.name AS authority, r.factual_status AS status",
    "candidates_isolated_from_official": "MATCH (c:CandEntity)-[r:CANDIDATE]->(:CandEntity) RETURN count(r) AS candidate_edges, "
                                         "count{ (:CandEntity)-[:CHAIR_OF|CEO_OF|BOARD_MEMBER_OF|OWNS_SHARES_IN]->() } AS official_rels_on_candidate_nodes",
    "bond_issues": "MATCH (o:Organization)-[r:ISSUED_BOND]->(b:BondIssue) RETURN o.name AS issuer, b.name AS bond, r.factual_status AS status",
}


def password() -> str:
    return (ROOT / ".neo4j-auth").read_text().strip().split("/", 1)[1]


def connect(uri: str = "bolt://127.0.0.1:7687"):
    from neo4j import GraphDatabase
    return GraphDatabase.driver(uri, auth=("neo4j", password()), notifications_min_severity="OFF")


def edge_id(e: dict) -> str:
    return hashlib.sha1("|".join(map(str, edge_event_key(e))).encode()).hexdigest()[:16]


def evidence_id(eid: str, r: dict) -> str:
    return hashlib.sha1(f"{eid}|{r['article_id']}|{r['evidence_start']}|{r['evidence_end']}".encode()).hexdigest()[:16]


def _jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def registry_info(db: str | Path | None) -> dict[str, dict]:
    if not db or not Path(db).exists():
        return {}
    c = sqlite3.connect(str(db))
    out = {r[0]: {"name": r[1], "type": r[2], "status": r[3]} for r in c.execute(
        "SELECT entity_id, canonical_name, entity_type, resolution_status FROM entities")}
    c.close()
    return out


def collect(run_dirs: list[Path], registries: list[Path | None], human_jsonl: Path | None = None) -> tuple[list[dict], list[dict], dict, dict]:
    """Returns (official_edges, candidate_edges, entity_info, article_info). Candidates exclude anything already official."""
    info: dict[str, dict] = {}
    for reg in registries:
        info.update(registry_info(reg))
    official, cands = [], []
    for d in run_dirs:
        official += _jl(d / "relations_official.jsonl")
        cands += _jl(d / "relations_candidate.jsonl")
    if human_jsonl:
        official += _jl(human_jsonl)
    official, cands, merges = consolidate_persons_across_runs(official, cands, info)
    collect.last_merges = merges
    off = unique_edges(official)
    off_triples = {(k[0], k[1], k[2]) for k in off}
    cand = {k: v for k, v in unique_edges(cands).items() if (k[0], k[1], k[2]) not in off_triples}
    arts = {}
    for e in [*off.values(), *cand.values()]:
        for r in e["evidence"]:
            arts[r["article_id"]] = {"article_id": r["article_id"], "url": r["source_url"], "published_at": r.get("published_at") or ""}
    return list(off.values()), list(cand.values()), info, arts


def consolidate_persons_across_runs(official: list[dict], cands: list[dict], info: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Runs have separate article-scoped person clusters. Merge two person ids only if normalized names are equal AND they hold
    a role/ownership edge toward the SAME organization id (same rule as the registry's consolidate_persons). Logged, deterministic."""
    from vckg.entity_linking.normalize import normalize_name
    orgs_of: dict[str, set[str]] = {}
    for e in official + cands:
        for p, o in ((e["subject_id"], e["object_id"]),):
            if p.startswith("person:") or info.get(p, {}).get("type") == "PERSON":
                orgs_of.setdefault(p, set()).add(o)
    by_name: dict[str, list[str]] = {}
    for p in orgs_of:
        by_name.setdefault(normalize_name(info.get(p, {}).get("name", p), is_person=True), []).append(p)
    parent: dict[str, str] = {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x
    merges = []
    for key, ids in by_name.items():
        ids = sorted(ids)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                ra, rb = find(a), find(b)
                shared = orgs_of[a] & orgs_of[b]
                if ra != rb and shared:
                    parent[max(ra, rb)] = min(ra, rb)
                    merges.append({"keep": min(ra, rb), "drop": max(ra, rb), "name_key": key, "shared_orgs": sorted(shared)})
    if not merges:
        return official, cands, merges
    remap = lambda eid: find(eid)
    def apply(es):
        return [{**e, "subject_id": remap(e["subject_id"]), "object_id": remap(e["object_id"])} for e in es]
    return apply(official), apply(cands), merges


def _label(info: dict, eid: str) -> str:
    t = info.get(eid, {}).get("type", "ORGANIZATION")
    if eid.startswith("person:"):
        t = "PERSON"
    elif eid.startswith("bond:"):
        t = "BOND_ISSUE"
    return LABELS.get(t, "Organization")


def sync(driver, official: list[dict], cands: list[dict], info: dict, arts: dict, database: str = "neo4j") -> dict:
    with driver.session(database=database) as s:
        for q in CONSTRAINTS:
            s.run(q)
        # ---- articles
        s.run("UNWIND $rows AS r MERGE (a:Article {article_id: r.article_id}) SET a.url = r.url, a.published_at = r.published_at", rows=list(arts.values()))
        # ---- official entities, grouped by label combo (labels cannot be parameters)
        nodes: dict[str, list[dict]] = {}
        for e in official:
            for eid in (e["subject_id"], e["object_id"]):
                nodes.setdefault(_label(info, eid), {})[eid] = {"entity_id": eid, "name": info.get(eid, {}).get("name", eid),
                                                                "entity_type": info.get(eid, {}).get("type", ""), "identity_status": info.get(eid, {}).get("status", "")}
        for lab, rows in nodes.items():
            s.run(f"UNWIND $rows AS r MERGE (n:Entity {{entity_id: r.entity_id}}) SET n:{lab}, n.name = r.name, n.entity_type = r.entity_type, "
                  f"n.identity_status = r.identity_status", rows=list(rows.values()))
        # ---- official relationships + evidence
        for e in official:
            if e["predicate"] not in PREDICATES:
                continue
            eid_ = edge_id(e)
            ev = e["evidence"]
            evs = [{"evidence_id": evidence_id(eid_, r), "edge_id": eid_, "article_id": r["article_id"], "text": r["evidence_text"],
                    "start": r["evidence_start"], "end": r["evidence_end"], "method": r["extraction_method"], "model": r.get("model", ""),
                    "prompt_version": r.get("prompt_version", ""), "factual_status": r["factual_status"], "review_status": r["review_status"],
                    "valid_from": r.get("valid_from") or "", "valid_to": r.get("valid_to") or ""} for r in ev]
            review = "HUMAN_VERIFIED" if any(r["review_status"] == "HUMAN_VERIFIED" for r in ev) else "AUTO_ACCEPTED"
            statuses = sorted({r["factual_status"] for r in ev})
            s.run(f"MATCH (a:Entity {{entity_id:$s}}), (b:Entity {{entity_id:$o}}) MERGE (a)-[r:{e['predicate']} {{edge_id:$eid}}]->(b) "
                  "SET r.factual_status=$st, r.valid_from=$vf, r.valid_to=$vt, r.evidence_count=$n, r.evidence_ids=$ids, r.review_state=$rv, "
                  "r.derived=false, r.official=true, r.extraction_methods=$m",
                  s=e["subject_id"], o=e["object_id"], eid=eid_, st=statuses[0] if len(statuses) == 1 else "|".join(statuses),
                  vf=max((x["valid_from"] for x in evs), default=""), vt=max((x["valid_to"] for x in evs), default=""), n=len(evs),
                  ids=[x["evidence_id"] for x in evs], rv=review, m=sorted({x["method"] for x in evs}))
            s.run("UNWIND $rows AS r MERGE (v:Evidence {evidence_id: r.evidence_id}) SET v.edge_id=r.edge_id, v.text=r.text, v.start=r.start, v.end=r.end, "
                  "v.method=r.method, v.model=r.model, v.prompt_version=r.prompt_version, v.factual_status=r.factual_status, v.review_status=r.review_status, "
                  "v.valid_from=r.valid_from, v.valid_to=r.valid_to WITH v, r MATCH (a:Article {article_id:r.article_id}) MERGE (v)-[:FROM]->(a)", rows=evs)
            s.run("MATCH (:CandEntity {entity_id:$s})-[x:CANDIDATE {predicate:$p}]->(:CandEntity {entity_id:$o}) DELETE x",
                  s=e["subject_id"], p=e["predicate"], o=e["object_id"])  # promoted candidate leaves the candidate namespace
        # ---- candidates (separate namespace)
        for e in cands:
            ceid = hashlib.sha1("|".join(map(str, edge_event_key(e))).encode()).hexdigest()[:16]
            for eid in (e["subject_id"], e["object_id"]):
                s.run("MERGE (n:CandEntity {entity_id:$id}) SET n.name=$name, n.identity_status=$st", id=eid, name=info.get(eid, {}).get("name", eid),
                      st=info.get(eid, {}).get("status", ""))
            reasons = sorted({x for r in e["evidence"] for x in r.get("validation_status", "").replace("CANDIDATE:", "").split(";")[0].split(",") if x})
            s.run("MATCH (a:CandEntity {entity_id:$s}), (b:CandEntity {entity_id:$o}) MERGE (a)-[r:CANDIDATE {edge_id:$eid}]->(b) "
                  "SET r.predicate=$p, r.official=false, r.evidence_count=$n, r.reasons=$rs, r.factual_status=$st, r.source_urls=$u",
                  s=e["subject_id"], o=e["object_id"], eid=ceid, p=e["predicate"], n=len(e["evidence"]), rs=reasons,
                  st=e["evidence"][0]["factual_status"], u=sorted({r["source_url"] for r in e["evidence"]})[:5])
    with driver.session(database=database) as s:
        s.run("MATCH (n:CandEntity) WHERE NOT (n)--() DELETE n")
    return stats(driver, database)


def stats(driver, database: str = "neo4j") -> dict:
    with driver.session(database=database) as s:
        one = lambda q: s.run(q).single()[0]
        return {"domain_entity_nodes": one("MATCH (n:Entity) RETURN count(n)"),
                "official_edges": one("MATCH (:Entity)-[r]->(:Entity) WHERE r.edge_id IS NOT NULL RETURN count(r)"),
                "relation_types": one("MATCH (:Entity)-[r]->(:Entity) WHERE r.edge_id IS NOT NULL RETURN count(DISTINCT type(r))"),
                "evidence_nodes": one("MATCH (e:Evidence) RETURN count(e)"), "articles": one("MATCH (a:Article) RETURN count(a)"),
                "candidate_edges": one("MATCH ()-[r:CANDIDATE]->() RETURN count(r)"), "candidate_nodes": one("MATCH (n:CandEntity) RETURN count(n)")}


def run_queries(driver, names: list[str] | None = None) -> dict:
    out = {}
    with driver.session() as s:
        for k, q in QUERIES.items():
            if names and k not in names:
                continue
            out[k] = [dict(r) for r in s.run(q)]
    return out


def export_projections(official: list[dict], out_dir: Path, info: dict | None = None) -> dict:
    """Person-person and company-company projections (derived edges labelled), as GraphML + CSV. Uses official edges only."""
    import csv

    import networkx as nx

    from vckg.graph.projection import company_company_projection, person_person_projection, to_unweighted
    from vckg.models import Edge
    out_dir.mkdir(parents=True, exist_ok=True)
    edges = [Edge.model_validate(e) for e in official]
    res = {}
    for name, g in (("person_person", person_person_projection(edges)), ("company_company", company_company_projection(edges))):
        h = nx.Graph()
        for n in g.nodes:
            h.add_node(n, name=(info or {}).get(n, {}).get("name", n))
        for u, v, d in g.edges(data=True):
            h.add_edge(u, v, **{k: (";".join(sorted(x)) if isinstance(x, set) else x) for k, x in d.items()})
        nx.write_graphml(h, out_dir / f"{name}.graphml")
        nx.write_graphml(to_unweighted(h), out_dir / f"{name}_unweighted.graphml")
        with (out_dir / f"{name}_edges.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source", "target", "weight", "kind", "derived"])
            for u, v, d in h.edges(data=True):
                w.writerow([u, v, d.get("weight", 1), d.get("kind", ""), d.get("derived", False)])
        res[name] = {"nodes": h.number_of_nodes(), "edges": h.number_of_edges()}
    return res


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="neo4j_sync")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping")
    sub.add_parser("constraints")
    sub.add_parser("stats")
    q = sub.add_parser("queries")
    q.add_argument("--only", nargs="*")
    for name in ("import", "projections"):
        p = sub.add_parser(name)
        p.add_argument("--runs", nargs="+", required=True)
        p.add_argument("--registry", nargs="*", default=[])
        p.add_argument("--human", default=None)
        p.add_argument("--out", default=str(ROOT / "data/outputs/phase5/projections"))
    a = ap.parse_args(argv)
    try:
        drv = connect()
        drv.verify_connectivity()
    except Exception as e:  # noqa: BLE001
        print(f"[neo4j] UNAVAILABLE: {e}")
        return 1
    if a.cmd == "ping":
        with drv.session() as s:
            print("[neo4j] OK", s.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] AS v LIMIT 1").data()[0])
    elif a.cmd == "constraints":
        with drv.session() as s:
            [s.run(c) for c in CONSTRAINTS]
        print("constraints ensured")
    elif a.cmd == "stats":
        print(json.dumps(stats(drv), indent=2))
    elif a.cmd == "queries":
        print(json.dumps(run_queries(drv, a.only), ensure_ascii=False, indent=2, default=str))
    else:
        off, cand, info, arts = collect([Path(r) for r in a.runs], [Path(r) for r in a.registry], Path(a.human) if a.human else None)
        if a.cmd == "import":
            print(json.dumps({"input_official_unique": len(off), "input_candidate_unique": len(cand), "neo4j": sync(drv, off, cand, info, arts)}, indent=2))
        else:
            print(json.dumps(export_projections(off, Path(a.out), info), indent=2))
    drv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

