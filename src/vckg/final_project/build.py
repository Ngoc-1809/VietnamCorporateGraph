"""Build a read-only application snapshot and reproducible network measures from ER v2 CSV.

The input ER output and all campaign databases are never modified. Only press-evidenced
LEGACY_OFFICIAL/QA_PASS relations with an official factual status enter this snapshot.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[3]
ER = ROOT / "data/entity_resolution/final_20261120"
OUT = ROOT / "data/final_project"
EXCLUSIONS = ROOT / "config/final_project_exclusions.csv"
TIERS = {"LEGACY_OFFICIAL", "QA_PASS"}
OFFICIAL_STATUSES = {"FACT", "HISTORICAL", "ENDED"}
GROUNDED_IDENTITIES = {"VERIFIED", "EXTERNAL_VERIFIED", "ARTICLE_GROUNDED"}

SCHEMA = """
CREATE TABLE nodes(node_id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_type TEXT NOT NULL,
 identity_status TEXT, aliases TEXT, pagerank REAL, degree INTEGER, in_degree INTEGER,
 out_degree INTEGER, community INTEGER, core_number INTEGER, component INTEGER);
CREATE TABLE edges(edge_uid TEXT PRIMARY KEY, edge_id TEXT NOT NULL, tier TEXT NOT NULL,
 subject_id TEXT NOT NULL, predicate TEXT NOT NULL, object_id TEXT NOT NULL,
 factual_status TEXT NOT NULL, valid_from TEXT, valid_to TEXT, evidence_count INTEGER,
 article_count INTEGER, FOREIGN KEY(subject_id) REFERENCES nodes(node_id),
 FOREIGN KEY(object_id) REFERENCES nodes(node_id));
CREATE TABLE evidence(evidence_id TEXT PRIMARY KEY, edge_uid TEXT NOT NULL, article_id TEXT,
 source_url TEXT, publisher TEXT, published_at TEXT, evidence_text TEXT,
 extraction_method TEXT, evidence_start INTEGER, evidence_end INTEGER,
 FOREIGN KEY(edge_uid) REFERENCES edges(edge_uid));
CREATE INDEX edges_subject ON edges(subject_id);
CREATE INDEX edges_object ON edges(object_id);
CREATE INDEX evidence_edge ON evidence(edge_uid);
"""


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _identity(row: dict) -> str:
    return row["qa_tier"] + ":" + row["edge_id"]


def _official(row: dict) -> bool:
    return row["qa_tier"] in TIERS and row["factual_status"] in OFFICIAL_STATUSES and row["in_validated_graph"] == "1"


def _endpoints_ok(row: dict, nodes: dict[str, dict]) -> bool:
    """Re-check canonical identity after ER; the old QA tier alone is insufficient."""
    for side in ("subject", "object"):
        node = nodes.get(row[f"{side}_id"])
        if node is None or row[f"{side}_identity_status"] not in GROUNDED_IDENTITIES:
            return False
        if node["identity_status"] not in GROUNDED_IDENTITIES:
            return False
        if node["identity_status"] == "ARTICLE_GROUNDED":
            name = node["name"].strip()
            if node["entity_type"] in {"ORGANIZATION", "BANK"} and len(name.split()) == 1:
                return False  # a lone word/acronym can absorb unrelated people or firms
            if node["entity_type"] == "PERSON" and len(name.split()) < 2:
                return False
    return True


def analyze(g: nx.Graph, directed: nx.DiGraph, *, random_trials: int = 20) -> tuple[dict, dict]:
    components = sorted(nx.connected_components(g), key=lambda group: (-len(group), min(group)))
    component_of = {node: i for i, group in enumerate(components) for node in group}
    communities = sorted(nx.community.louvain_communities(g, seed=7), key=lambda group: (-len(group), min(group)))
    community_of = {node: i for i, group in enumerate(communities) for node in group}
    core = nx.core_number(g) if g else {}
    rank = nx.pagerank(directed, alpha=0.85, weight=None) if directed else {}
    lcc = g.subgraph(components[0]).copy() if components else nx.Graph()
    path_length = nx.average_shortest_path_length(lcc) if len(lcc) > 1 else 0.0
    clustering = nx.average_clustering(lcc) if lcc else 0.0
    random_c, random_l = [], []
    for seed in range(random_trials):
        trial = lcc.copy()
        if trial.number_of_edges() > 2:
            nx.connected_double_edge_swap(trial, nswap=2 * trial.number_of_edges(), seed=seed)
        random_c.append(nx.average_clustering(trial) if trial else 0.0)
        random_l.append(nx.average_shortest_path_length(trial) if len(trial) > 1 else 0.0)
    cr = statistics.mean(random_c) if random_c else 0.0
    lr = statistics.mean(random_l) if random_l else 0.0
    sigma = (clustering / cr) / (path_length / lr) if cr and path_length and lr else None
    reachable_pairs = 0
    distance_sum = efficiency_sum = 0.0
    for _, lengths in nx.all_pairs_shortest_path_length(g):
        for distance in lengths.values():
            if distance:
                reachable_pairs += 1
                distance_sum += distance
                efficiency_sum += 1 / distance
    total_pairs = len(g) * (len(g) - 1)
    metrics = {
        "nodes": len(g), "simple_undirected_pairs": g.number_of_edges(),
        "connected_components": len(components), "largest_component": len(lcc),
        "largest_component_share": len(lcc) / len(g) if g else 0,
        "largest_component_average_shortest_path": path_length,
        "whole_graph_average_shortest_path": None if len(components) > 1 else path_length,
        "reachable_pair_average_shortest_path": distance_sum / reachable_pairs if reachable_pairs else None,
        "global_efficiency": efficiency_sum / total_pairs if total_pairs else 0,
        "largest_component_clustering": clustering,
        "random_baseline_clustering": cr, "random_baseline_path_length": lr,
        "small_world_sigma_largest_component": sigma, "random_trials": random_trials,
        "random_seed_range": [0, random_trials - 1],
        "max_core": max(core.values(), default=0), "communities": len(communities),
        "modularity": nx.community.modularity(g, communities) if communities and g.number_of_edges() else 0,
        "note": "Disconnected whole graph has no finite mean shortest path; sigma applies only to the largest connected component.",
    }
    per_node = {node: {"pagerank": rank.get(node, 0), "degree": g.degree(node),
                       "in_degree": directed.in_degree(node), "out_degree": directed.out_degree(node),
                       "community": community_of[node], "core_number": core[node],
                       "component": component_of[node]} for node in g}
    return metrics, per_node


def build(er: Path = ER, out_root: Path = OUT, random_trials: int = 20) -> dict:
    status = json.loads((er / "status.json").read_text(encoding="utf-8"))
    if status["state"] != "COMPLETED":
        raise ValueError("Entity Resolution must be COMPLETED")
    source_snapshot_id = Path(status["snapshot"]).name
    snapshot_id = f"{source_snapshot_id}-gate-v2"
    out = out_root / snapshot_id
    if out.exists():
        raise FileExistsError(f"Immutable application snapshot already exists: {out}")
    nodes = {row["node_id"]: row for row in _read(er / "nodes_v2.csv")}
    rows = _read(er / "edges_v2.csv")
    exclusions = {(r["qa_tier"], r["edge_id"]) for r in _read(EXCLUSIONS)} if EXCLUSIONS.exists() else set()
    exclusions_digest = hashlib.sha256(EXCLUSIONS.read_bytes()).hexdigest() if EXCLUSIONS.exists() else None
    selected: dict[str, dict] = {}
    evidence: dict[str, dict] = {}
    excluded = Counter()
    applied_exclusions = set()
    for row in rows:
        if not _official(row):
            if row["qa_tier"] in TIERS and row["factual_status"] not in OFFICIAL_STATUSES:
                excluded[row["factual_status"]] += 1
            continue
        exclusion_key = (row["qa_tier"], row["edge_id"])
        if exclusion_key in exclusions:
            excluded["AI_SCREENED_EVIDENCE_MISMATCH"] += 1
            applied_exclusions.add(exclusion_key)
            continue
        if not _endpoints_ok(row, nodes):
            excluded["ENDPOINT_IDENTITY"] += 1
            continue
        uid = _identity(row)
        selected.setdefault(uid, row)
        if row["article_id"]:
            key = "|".join((uid, row["article_id"], row["evidence_start"], row["evidence_end"], row["evidence_text"]))
            evidence[hashlib.sha1(key.encode()).hexdigest()[:20]] = {**row, "edge_uid": uid}
    used = {node for row in selected.values() for node in (row["subject_id"], row["object_id"])}
    missing = used - nodes.keys()
    if missing:
        raise ValueError(f"Missing canonical node records: {sorted(missing)[:5]}")
    g, directed = nx.Graph(), nx.DiGraph()
    g.add_nodes_from(sorted(used))
    directed.add_nodes_from(sorted(used))
    for _, row in sorted(selected.items()):
        s, o = row["subject_id"], row["object_id"]
        if s != o:
            g.add_edge(s, o)
            directed.add_edge(s, o)
    metrics, per_node = analyze(g, directed, random_trials=random_trials)
    out.mkdir(parents=True)
    db = sqlite3.connect(out / "profile.sqlite")
    try:
        db.executescript(SCHEMA)
        db.executemany("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", [
            (node, nodes[node]["name"], nodes[node]["entity_type"], nodes[node]["identity_status"], nodes[node]["aliases"],
             m["pagerank"], m["degree"], m["in_degree"], m["out_degree"], m["community"], m["core_number"], m["component"])
            for node, m in sorted(per_node.items())])
        ev_by_edge: dict[str, list[dict]] = {}
        for item in evidence.values():
            ev_by_edge.setdefault(item["edge_uid"], []).append(item)
        db.executemany("INSERT INTO edges VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
            (uid, row["edge_id"], row["qa_tier"], row["subject_id"], row["relation_type"], row["object_id"], row["factual_status"],
             row["valid_from"], row["valid_to"], len(ev_by_edge.get(uid, [])), len({r["article_id"] for r in ev_by_edge.get(uid, [])}))
            for uid, row in sorted(selected.items())])
        db.executemany("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)", [
            (eid, row["edge_uid"], row["article_id"], row["source_url"], row["publisher"], row["published_at"],
             row["evidence_text"], row["extraction_method"], int(row["evidence_start"] or 0), int(row["evidence_end"] or 0))
            for eid, row in sorted(evidence.items())])
        db.commit()
    finally:
        db.close()
    result = {"snapshot_id": snapshot_id, "source_snapshot_id": source_snapshot_id, "source_er": str(er),
              "created_at": datetime.now().astimezone().isoformat(),
              "node_count": len(used), "edge_count": len(selected), "evidence_count": len(evidence),
              "relation_types": len({r["relation_type"] for r in selected.values()}),
              "excluded_nonofficial_evidence_rows": dict(excluded), "analysis": metrics,
              "screened_exclusions_applied": len(applied_exclusions), "exclusions_sha256": exclusions_digest,
              "policy": "Only LEGACY_OFFICIAL/QA_PASS with FACT/HISTORICAL/ENDED and canonical grounded endpoints; single-word article-grounded organizations and AI-screened evidence mismatches excluded. AI QA outcomes are not gold accuracy."}
    (out / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_root / "LATEST.txt").write_text(snapshot_id, encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ACTIVE.txt").write_text(str(out.resolve()), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--er", type=Path, default=ER)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--random-trials", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(build(args.er, args.out, args.random_trials), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
