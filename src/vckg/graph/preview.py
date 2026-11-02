"""Exploratory graph preview (read-only over a SNAPSHOT of the aggregate; no NLP, no models, no crawl, no Neo4j).

  python -m vckg.graph.preview build [--agg data/aggregate/staging_graph.sqlite] [--queue data/campaign/mass/queue.sqlite] [--out data/graph_preview]

1. Consistent snapshot (SQLite Backup API) of the aggregate DB and the campaign queue DB -> data/graph_preview/<snapshot_id>/snapshot/ (originals untouched).
2. Graph from the snapshot: tiers LEGACY_OFFICIAL + QA_PASS ("validated") and + QUARANTINE ("exploratory"). REJECT and LEGACY_CANDIDATE are excluded. Canonical entity keys,
   directions, tiers and provenance are kept; nothing is merged or promoted. Unresolved text endpoints stay as separate nodes of type UNRESOLVED_TEXT.
3. Exports: nodes.csv, edges.csv (one row per evidence), validated.graphml, exploratory.graphml, stats.json/.md, and an interactive local viewer (viewer.html + data/*.js,
   vis-network from data/graph_preview/lib) that renders only a bounded subgraph at a time.
The exploratory graph is NOT validated and there is no gold accuracy."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import networkx as nx

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/graph_preview"
AGG = ROOT / "data/aggregate/staging_graph.sqlite"
QUEUE = ROOT / "data/campaign/mass/queue.sqlite"
STAGING = ROOT / "data/staging/staging.sqlite"
TIERS = ("LEGACY_OFFICIAL", "QA_PASS", "QUARANTINE")
VALIDATED = ("LEGACY_OFFICIAL", "QA_PASS")
TYPES = ["PERSON", "ORGANIZATION", "BANK", "REGULATOR", "GOVERNMENT_AGENCY", "BOND_ISSUE", "UNRESOLVED_TEXT"]
EV_TEXT_MAX = 600
THRESH = {"nodes": 2000, "edges": 5000, "relation_types": 10}


def backup(src: Path, dst: Path) -> None:
    """Consistent copy while other connections may exist (SQLite online backup)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    s = sqlite3.connect(f"file:{Path(src).as_posix()}?mode=ro", uri=True, timeout=60)
    d = sqlite3.connect(str(dst))
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()


def publisher(url: str | None) -> str:
    h = urlsplit(url or "").netloc.lower()
    return h.removeprefix("www.")


def take_snapshot(out_root: Path, agg: Path, queue: Path, now: datetime | None = None) -> tuple[str, Path, dict]:
    now = now or datetime.now().astimezone()
    sid = now.strftime("%Y%m%d-%H%M%S")
    d = out_root / sid
    snap = d / "snapshot"
    backup(agg, snap / "staging_graph.sqlite")
    meta = {"snapshot_id": sid, "taken_at": now.isoformat(timespec="seconds"), "source_aggregate": str(agg), "source_queue": str(queue)}
    if Path(queue).exists():
        backup(queue, snap / "queue.sqlite")
        q = sqlite3.connect(snap / "queue.sqlite")
        meta["nlp"] = {str(r[0]): r[1] for r in q.execute("SELECT nlp_status, COUNT(*) FROM urls WHERE parse_status='ok' GROUP BY 1")}
        meta["articles_downloaded"] = q.execute("SELECT COUNT(*) FROM urls WHERE crawl_status='fetched'").fetchone()[0]
        meta["articles_parsed"] = q.execute("SELECT COUNT(*) FROM urls WHERE parse_status='ok'").fetchone()[0]
        meta["chunks_finished"] = q.execute("SELECT COUNT(*) FROM chunks WHERE status='finished'").fetchone()[0]
        meta["qwen_live_calls"] = int(q.execute("SELECT value FROM meta WHERE key='qwen_live_done'").fetchone()[0])
        q.close()
        meta["articles_nlp_processed"] = meta["nlp"].get("done", 0)
    a = sqlite3.connect(snap / "staging_graph.sqlite")
    meta["aggregate_rows"] = {t: a.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("entities", "edges", "evidence", "person_merges", "collisions")}
    meta["aggregate_last_ingest"] = a.execute("SELECT MAX(ingested_at) FROM sources").fetchone()[0]
    a.close()
    (d / "snapshot.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return sid, d, meta


def load(snap_db: Path, staging: Path | None):
    db = sqlite3.connect(f"file:{Path(snap_db).as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    q = ",".join("?" * len(TIERS))
    ents = {r["entity_key"]: dict(r) for r in db.execute("SELECT * FROM entities")}
    edges = [dict(r) for r in db.execute(f"SELECT * FROM edges WHERE tier IN ({q}) ORDER BY tier, edge_id", TIERS)]
    ev: dict[tuple, list[dict]] = defaultdict(list)
    for r in db.execute(f"SELECT * FROM evidence WHERE tier IN ({q}) ORDER BY edge_id, article_id, evidence_start", TIERS):
        ev[(r["edge_id"], r["tier"])].append(dict(r))
    db.close()
    pub: dict[str, str | None] = {}
    if staging and Path(staging).exists():
        s = sqlite3.connect(f"file:{Path(staging).as_posix()}?mode=ro", uri=True, timeout=60)
        ids = sorted({r["article_id"] for v in ev.values() for r in v})
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            for aid, p in s.execute(f"SELECT article_id, published_at FROM articles WHERE article_id IN ({','.join('?' * len(part))})", part):
                pub[aid] = p
        s.close()
    return ents, edges, ev, pub


def ntype(e: dict) -> str:
    return e.get("entity_type") or "UNRESOLVED_TEXT"


def build_graph(ents: dict, edges: list[dict], tiers: tuple[str, ...]) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for e in edges:
        if e["tier"] not in tiers:
            continue
        for k in (e["subject_key"], e["object_key"]):
            if k not in g:
                n = ents[k]
                g.add_node(k, name=n["name"] or k, entity_type=ntype(n), identity_status=n["resolution_status"] or "", registry_id=n["entity_id"])
        g.add_edge(e["subject_key"], e["object_key"], key=f"{e['edge_id']}:{e['tier']}", edge_id=e["edge_id"], relation_type=e["predicate"], qa_tier=e["tier"],
                   factual_status=e["factual_status"], valid_from=e["valid_from"], valid_to=e["valid_to"], n_evidence=int(e["n_evidence"] or 0), n_articles=int(e["n_articles"] or 0))
    return g


def components(g: nx.MultiDiGraph) -> list[list[str]]:
    return sorted((sorted(c) for c in nx.connected_components(g.to_undirected())), key=lambda c: (-len(c), c[0]))


def communities(g: nx.MultiDiGraph) -> list[list[str]]:
    if g.number_of_nodes() == 0:
        return []
    u = nx.Graph(g.to_undirected())
    cs = nx.community.louvain_communities(u, seed=7)
    return sorted((sorted(c) for c in cs), key=lambda c: (-len(c), c[0]))


def stats_of(g: nx.MultiDiGraph, comps: list[list[str]], ents: dict) -> dict:
    triples = {(u, d["relation_type"], v) for u, v, d in g.edges(data=True)}
    by_tier_rel: dict[str, Counter] = defaultdict(Counter)
    for _u, _v, d in g.edges(data=True):
        by_tier_rel[d["qa_tier"]][d["relation_type"]] += 1
    rels = Counter(d["relation_type"] for _u, _v, d in g.edges(data=True))
    deg = sorted(((g.degree(n), n) for n in g.nodes), key=lambda t: (-t[0], t[1]))[:20]
    return {"nodes": g.number_of_nodes(), "nodes_by_type": dict(Counter(a["entity_type"] for _n, a in g.nodes(data=True))),
            "nodes_by_identity_status": dict(Counter(a["identity_status"] or "(none)" for _n, a in g.nodes(data=True))),
            "edge_rows": g.number_of_edges(), "unique_triples_ignoring_status_and_tier": len(triples), "edges_by_tier": dict(Counter(d["qa_tier"] for _u, _v, d in g.edges(data=True))),
            "edges_by_tier_and_relation": {t: dict(c) for t, c in by_tier_rel.items()}, "edges_by_relation": dict(rels), "relation_types": len(rels),
            "connected_components": len(comps), "largest_component": len(comps[0]) if comps else 0, "component_sizes_top10": [len(c) for c in comps[:10]],
            "singleton_components": sum(1 for c in comps if len(c) == 1),
            "top20_degree": [{"id": n, "name": g.nodes[n]["name"], "type": g.nodes[n]["entity_type"], "degree": d, "in": g.in_degree(n), "out": g.out_degree(n)} for d, n in deg],
            "thresholds": {"nodes>=2000": g.number_of_nodes() >= THRESH["nodes"], "edge_rows>=5000": g.number_of_edges() >= THRESH["edges"],
                           "unique_triples>=5000": len(triples) >= THRESH["edges"], "relation_types>=10": len(rels) >= THRESH["relation_types"]}}


def write_graphml(g: nx.MultiDiGraph, path: Path) -> None:
    h = nx.MultiDiGraph()
    for n, a in g.nodes(data=True):
        h.add_node(n, **{k: ("" if v is None else v) for k, v in a.items()})
    for u, v, k, d in g.edges(keys=True, data=True):
        h.add_edge(u, v, key=k, **{x: ("" if y is None else y) for x, y in d.items()})
    nx.write_graphml(h, path)


def export_csv(out: Path, ents, edges, ev, pub, gv, ge, comp_v, comp_e, com_v, com_e) -> tuple[int, int]:
    idx = lambda groups: {n: i for i, c in enumerate(groups) for n in c}
    cv, ce, mv, me = idx(comp_v), idx(comp_e), idx(com_v), idx(com_e)
    with (out / "nodes.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "name", "entity_type", "identity_status", "registry_id", "in_validated_graph", "degree_validated", "degree_exploratory", "component_validated",
                    "component_exploratory", "community_validated", "community_exploratory", "tiers_present"])
        tiers_of: dict[str, set] = defaultdict(set)
        for e in edges:
            tiers_of[e["subject_key"]].add(e["tier"])
            tiers_of[e["object_key"]].add(e["tier"])
        for n, a in sorted(ge.nodes(data=True)):
            w.writerow([n, a["name"], a["entity_type"], a["identity_status"], a["registry_id"], int(n in gv), gv.degree(n) if n in gv else 0, ge.degree(n), cv.get(n, ""), ce.get(n, ""),
                        mv.get(n, ""), me.get(n, ""), "|".join(sorted(tiers_of[n]))])
    n_rows = 0
    with (out / "edges.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["edge_id", "qa_tier", "in_validated_graph", "subject_id", "subject_name", "subject_type", "subject_identity_status", "relation_type", "object_id", "object_name",
                    "object_type", "object_identity_status", "factual_status", "valid_from", "valid_to", "quarantine_classes", "discovery_methods", "n_evidence", "article_id", "publisher",
                    "source_url", "published_at", "evidence_start", "evidence_end", "extraction_method", "evidence_text"])
        for e in edges:
            s, o = ents[e["subject_key"]], ents[e["object_key"]]
            base = [e["edge_id"], e["tier"], int(e["tier"] in VALIDATED), e["subject_key"], s["name"], ntype(s), s["resolution_status"], e["predicate"], e["object_key"], o["name"], ntype(o),
                    o["resolution_status"], e["factual_status"], e["valid_from"], e["valid_to"], e["quarantine_classes"], e["discovery_methods"], e["n_evidence"]]
            rows = ev.get((e["edge_id"], e["tier"])) or [None]
            for r in rows:
                w.writerow(base + ([r["article_id"], publisher(r["source_url"]), r["source_url"], r["published_at"] or pub.get(r["article_id"]) or "", r["evidence_start"], r["evidence_end"],
                                    r["extraction_method"], r["evidence_text"]] if r else [""] * 8))
                n_rows += 1
    return ge.number_of_nodes(), n_rows


def export_viewer(out: Path, ents, edges, ev, pub, gv, ge, comp_v, comp_e, com_v, com_e, meta: dict) -> dict:
    data = out / "data"
    data.mkdir(exist_ok=True)
    nodes = sorted(ge.nodes)
    nid = {n: i for i, n in enumerate(nodes)}
    rels = sorted({e["predicate"] for e in edges})
    ridx = {r: i for i, r in enumerate(rels)}
    idx = lambda groups: {n: i for i, c in enumerate(groups) for n in c}
    cv, ce, mv, me = idx(comp_v), idx(comp_e), idx(com_v), idx(com_e)
    narr = [[ge.nodes[n]["name"], TYPES.index(ge.nodes[n]["entity_type"]) if ge.nodes[n]["entity_type"] in TYPES else 6, ge.nodes[n]["identity_status"],
             gv.degree(n) if n in gv else 0, ge.degree(n), cv.get(n, -1), ce[n], mv.get(n, -1), me[n], n] for n in nodes]
    earr, evmap = [], {}
    for i, e in enumerate(edges):
        earr.append([nid[e["subject_key"]], nid[e["object_key"]], ridx[e["predicate"]], TIERS.index(e["tier"]), e["factual_status"], e["valid_from"] or "", e["valid_to"] or "",
                     int(e["n_evidence"] or 0), e["quarantine_classes"] if e["tier"] == "QUARANTINE" else "", e["edge_id"]])
        rows = ev.get((e["edge_id"], e["tier"])) or []
        evmap[i] = [[r["article_id"], publisher(r["source_url"]), r["source_url"], r["published_at"] or pub.get(r["article_id"]) or "", (r["evidence_text"] or "")[:EV_TEXT_MAX], r["extraction_method"]] for r in rows]
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    (data / "graph.js").write_text(f"window.VCKG={{meta:{dump(meta)},types:{dump(TYPES)},tiers:{dump(list(TIERS))},rels:{dump(rels)},nodes:{dump(narr)},edges:{dump(earr)},comps_v:{dump([len(c) for c in comp_v])},comps_e:{dump([len(c) for c in comp_e])},coms_v:{dump([len(c) for c in com_v])},coms_e:{dump([len(c) for c in com_e])}}};", encoding="utf-8")
    (data / "evidence.js").write_text(f"window.VCKG_EV={dump(evmap)};", encoding="utf-8")  # loaded lazily on the first edge click
    shutil.copy(OUT / "lib" / "vis-network.min.js", data / "vis-network.min.js")
    shutil.copy(Path(__file__).with_name("preview_viewer.html"), out / "viewer.html")
    return {"nodes": len(narr), "edges": len(earr), "evidence_sets": len(evmap)}


def render_md(meta: dict, sv: dict, se: dict) -> str:
    def row(k, a, b):
        return f"| {k} | {a} | {b} |"
    L = [f"# Exploratory graph preview {meta['snapshot_id']}", "",
         (f"Snapshot taken {meta['taken_at']}; NLP-processed articles at snapshot: **{meta.get('articles_nlp_processed')}** (parsed {meta.get('articles_parsed')}, downloaded {meta.get('articles_downloaded')}, "
         f"Qwen live calls {meta.get('qwen_live_calls')}); aggregate last ingest {meta.get('aggregate_last_ingest')}."), "",
         ("**The exploratory graph (validated + QUARANTINE) is NOT validated. No gold labels exist: nothing here is precision/recall/F1. LEGACY_OFFICIAL and QA_PASS are rule/verifier outcomes, not ground truth.** "
         "REJECT and LEGACY_CANDIDATE are excluded; nothing was merged or promoted; unresolved text endpoints are kept as UNRESOLVED_TEXT nodes."), "",
         "| metric | validated (LEGACY_OFFICIAL + QA_PASS) | exploratory (+ QUARANTINE) |", "|---|---|---|",
         row("nodes", sv["nodes"], se["nodes"]), row("edge rows (edge, tier)", sv["edge_rows"], se["edge_rows"]),
         row("unique (subject, relation, object)", sv["unique_triples_ignoring_status_and_tier"], se["unique_triples_ignoring_status_and_tier"]),
         row("relation types", sv["relation_types"], se["relation_types"]), row("connected components", sv["connected_components"], se["connected_components"]),
         row("largest component (nodes)", sv["largest_component"], se["largest_component"]), row("singleton components", sv["singleton_components"], se["singleton_components"]),
         row("edges by tier", sv["edges_by_tier"], se["edges_by_tier"]), row("nodes by type", sv["nodes_by_type"], se["nodes_by_type"]),
         row("nodes by identity status", sv["nodes_by_identity_status"], se["nodes_by_identity_status"]), "",
         "## Targets (>=2,000 nodes, >=5,000 edges, >=10 relation types)", "| check | validated | exploratory |", "|---|---|---|"]
    for k in sv["thresholds"]:
        L.append(row(k, "PASS" if sv["thresholds"][k] else "no", "PASS" if se["thresholds"][k] else "no"))
    L += ["", "(edges: `edge_rows` counts one row per (edge, tier); `unique_triples` ignores factual status and tier.)", "", "## Edges by relation type"]
    rels = sorted(set(sv["edges_by_relation"]) | set(se["edges_by_relation"]))
    L += ["| relation | validated | exploratory |", "|---|---|---|"] + [row(r, sv["edges_by_relation"].get(r, 0), se["edges_by_relation"].get(r, 0)) for r in rels]
    for name, s in (("validated", sv), ("exploratory", se)):
        L += ["", f"## Top 20 nodes by degree ({name})", "| # | node | type | degree (in/out) |", "|---|---|---|---|"]
        L += [f"| {i + 1} | {t['name']} | {t['type']} | {t['degree']} ({t['in']}/{t['out']}) |" for i, t in enumerate(s["top20_degree"])]
    return "\n".join(L)


def build(out_root: Path = OUT, agg: Path = AGG, queue: Path = QUEUE, staging: Path | None = STAGING) -> dict:
    sid, d, meta = take_snapshot(out_root, agg, queue)
    ents, edges, ev, pub = load(d / "snapshot" / "staging_graph.sqlite", staging)
    gv, ge = build_graph(ents, edges, VALIDATED), build_graph(ents, edges, TIERS)
    comp_v, comp_e = components(gv), components(ge)
    com_v, com_e = communities(gv), communities(ge)
    write_graphml(gv, d / "validated.graphml")
    write_graphml(ge, d / "exploratory.graphml")
    nn, ne = export_csv(d, ents, edges, ev, pub, gv, ge, comp_v, comp_e, com_v, com_e)
    sv, se = stats_of(gv, comp_v, ents), stats_of(ge, comp_e, ents)
    se["communities"], sv["communities"] = len(com_e), len(com_v)
    viewer = export_viewer(d, ents, edges, ev, pub, gv, ge, comp_v, comp_e, com_v, com_e, {"snapshot_id": sid, "taken_at": meta["taken_at"], "nlp_processed": meta.get("articles_nlp_processed")})
    result = {"snapshot": meta, "validated": sv, "exploratory": se, "csv": {"nodes_rows": nn, "edges_rows": ne}, "viewer": viewer,
              "note": "exploratory graph is not validated; no gold accuracy"}
    (d / "stats.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (d / "stats.md").write_text(render_md(meta, sv, se), encoding="utf-8")
    (out_root / "LATEST.txt").write_text(sid, encoding="utf-8")
    result["dir"] = str(d)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="preview")
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--agg", default=str(AGG))
    ap.add_argument("--queue", default=str(QUEUE))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    r = build(Path(a.out), Path(a.agg), Path(a.queue))
    print(json.dumps({"dir": r["dir"], "validated": {k: r["validated"][k] for k in ("nodes", "edge_rows", "relation_types", "connected_components", "largest_component")},
                      "exploratory": {k: r["exploratory"][k] for k in ("nodes", "edge_rows", "relation_types", "connected_components", "largest_component")}, "csv": r["csv"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
