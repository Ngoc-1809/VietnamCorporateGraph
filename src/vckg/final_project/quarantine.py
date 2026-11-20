"""Build a separate, unverified Quarantine mode beside an immutable Passed snapshot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import networkx as nx

from vckg.entity_linking.generic import is_generic_entity
from vckg.final_project.app import snapshot_dir
from vckg.final_project.build import OUT, SCHEMA, _identity, _read


def _network(selected: dict[str, dict], eligible: set[str]) -> tuple[dict, dict]:
    used = sorted({node for row in selected.values() for node in (row["subject_id"], row["object_id"])})
    graph, directed = nx.Graph(), nx.DiGraph()
    graph.add_nodes_from(used)
    directed.add_nodes_from(used)
    for uid, row in selected.items():
        subject, object_ = row["subject_id"], row["object_id"]
        if uid in eligible and subject != object_:  # retain excluded candidates in SQLite for review
            graph.add_edge(subject, object_)
            directed.add_edge(subject, object_)
    components = sorted(nx.connected_components(graph), key=lambda group: (-len(group), min(group)))
    component_of = {node: index for index, group in enumerate(components) for node in group}
    communities = sorted(nx.community.louvain_communities(graph, seed=7),
                         key=lambda group: (-len(group), min(group)))
    community_of = {node: index for index, group in enumerate(communities) for node in group}
    core = nx.core_number(graph)
    rank = nx.pagerank(directed, alpha=0.85, weight=None)
    per_node = {node: {"pagerank": rank[node], "degree": graph.degree(node),
                       "in_degree": directed.in_degree(node), "out_degree": directed.out_degree(node),
                       "community": community_of[node], "core_number": core[node],
                       "component": component_of[node]} for node in used}
    metrics = {"connected_components": len(components),
               "largest_component": len(components[0]) if components else 0,
               "largest_component_share": len(components[0]) / len(used) if used else 0,
               "simple_undirected_pairs": graph.number_of_edges(),
               "communities": len(communities), "max_core": max(core.values(), default=0),
               "self_loops_excluded_from_structural_measures": sum(
                   row["subject_id"] == row["object_id"] for row in selected.values()),
               "note": "Quarantine-only candidate network; descriptive structure, not validated facts or accuracy."}
    return metrics, per_node


def build(passed: Path, out_root: Path = OUT) -> dict:
    passed_meta = json.loads((passed / "metrics.json").read_text(encoding="utf-8"))
    er = Path(passed_meta["source_er"])
    if not er.is_absolute():
        er = (OUT.parents[1] / er).resolve()
    er_status = json.loads((er / "status.json").read_text(encoding="utf-8"))
    if er_status["state"] != "COMPLETED":
        raise ValueError("The source ER v2 run must be COMPLETED")
    nodes = {row["node_id"]: row for row in _read(er / "nodes_v2.csv")}
    selected: dict[str, dict] = {}
    evidence: dict[str, dict] = {}
    for row in _read(er / "edges_v2.csv"):
        if row["qa_tier"] != "QUARANTINE":
            continue
        uid = _identity(row)
        selected.setdefault(uid, row)
        key = "|".join((uid, row["article_id"], row["evidence_start"],
                        row["evidence_end"], row["evidence_text"]))
        evidence[hashlib.sha1(key.encode()).hexdigest()[:20]] = {**row, "edge_uid": uid}
    used = {node for row in selected.values() for node in (row["subject_id"], row["object_id"])}
    missing = used - nodes.keys()
    if missing:
        raise ValueError(f"Quarantine endpoints missing from ER nodes: {sorted(missing)[:5]}")
    generic = {node for node in used if is_generic_entity(nodes[node]["name"])}
    eligible = {uid for uid, row in selected.items()
                if row["subject_id"] not in generic and row["object_id"] not in generic
                and row["subject_id"] != row["object_id"]}
    analysis, per_node = _network(selected, eligible)
    analysis["network_candidate_edges"] = len(eligible)
    analysis["generic_endpoint_edges_excluded_from_network"] = sum(
        row["subject_id"] in generic or row["object_id"] in generic for row in selected.values())
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    out = out_root / f"{passed_meta['snapshot_id']}-dual-{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(passed / "profile.sqlite", out / "profile.sqlite")
    shutil.copy2(passed / "metrics.json", out / "metrics.json")
    db = sqlite3.connect(out / "quarantine.sqlite")
    try:
        db.executescript(SCHEMA)
        db.execute("ALTER TABLE nodes ADD COLUMN endpoint_quality TEXT")
        db.execute("ALTER TABLE edges ADD COLUMN quarantine_classes TEXT")
        db.execute("ALTER TABLE edges ADD COLUMN discovery_methods TEXT")
        db.execute("ALTER TABLE edges ADD COLUMN endpoint_quality TEXT")
        db.executemany("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            (node, nodes[node]["name"], nodes[node]["entity_type"], nodes[node]["identity_status"],
             nodes[node]["aliases"], metric["pagerank"], metric["degree"], metric["in_degree"],
             metric["out_degree"], metric["community"], metric["core_number"], metric["component"],
             "GENERIC_NAME" if node in generic else "ELIGIBLE")
            for node, metric in sorted(per_node.items())])
        ev_by_edge: dict[str, list[dict]] = defaultdict(list)
        for item in evidence.values():
            ev_by_edge[item["edge_uid"]].append(item)
        db.executemany("""
            INSERT INTO edges(edge_uid,edge_id,tier,subject_id,predicate,object_id,factual_status,
                              valid_from,valid_to,evidence_count,article_count,quarantine_classes,discovery_methods,
                              endpoint_quality)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
            (uid, row["edge_id"], "QUARANTINE", row["subject_id"], row["relation_type"],
             row["object_id"], row["factual_status"], row["valid_from"], row["valid_to"],
             len(ev_by_edge[uid]), len({item["article_id"] for item in ev_by_edge[uid]}),
             row["quarantine_classes"], row["discovery_methods"],
             "ELIGIBLE" if uid in eligible else "GENERIC_ENDPOINT" if
             row["subject_id"] in generic or row["object_id"] in generic else "SELF_LOOP")
            for uid, row in sorted(selected.items())])
        db.executemany("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)", [
            (eid, row["edge_uid"], row["article_id"], row["source_url"], row["publisher"],
             row["published_at"], row["evidence_text"], row["extraction_method"],
             int(row["evidence_start"] or 0), int(row["evidence_end"] or 0))
            for eid, row in sorted(evidence.items())])
        db.commit()
    finally:
        db.close()
    review_path = out / "generic_endpoint_review.csv"
    with review_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["edge_uid", "subject_name", "predicate", "object_name",
                                                   "generic_side", "article_id", "source_url", "evidence_text",
                                                   "quarantine_classes"])
        writer.writeheader()
        for uid, row in sorted(selected.items()):
            generic_side = ",".join(side for side in ("subject", "object") if row[f"{side}_id"] in generic)
            if not generic_side:
                continue
            for item in ev_by_edge[uid]:
                writer.writerow({"edge_uid": uid, "subject_name": nodes[row["subject_id"]]["name"],
                                 "predicate": row["relation_type"],
                                 "object_name": nodes[row["object_id"]]["name"],
                                 "generic_side": generic_side, "article_id": item["article_id"],
                                 "source_url": item["source_url"], "evidence_text": item["evidence_text"],
                                 "quarantine_classes": row["quarantine_classes"]})
    reasons = Counter()
    statuses = Counter()
    for row in selected.values():
        statuses[row["factual_status"]] += 1
        for reason in json.loads(row["quarantine_classes"] or "[]"):
            reasons[reason] += 1
    result = {"mode": "quarantine", "snapshot_id": f"{passed_meta['snapshot_id']}-quarantine-{stamp}",
              "source_snapshot_id": passed_meta["source_snapshot_id"], "source_er": str(er),
              "node_count": len(used), "edge_count": len(selected), "evidence_count": len(evidence),
              "relation_types": len({row["relation_type"] for row in selected.values()}),
              "generic_name_nodes": len(generic),
              "generic_review_sheet": str(review_path),
              "factual_statuses": dict(statuses), "quarantine_classes": dict(reasons),
              "analysis": analysis,
              "policy": "All ER v2 QUARANTINE candidates, including unresolved endpoints, non-official statuses and self-loops. None is promoted to Passed or counted as a verified relationship."}
    (out / "quarantine_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "modes.json").write_text(json.dumps({"passed": passed_meta["snapshot_id"],
                                                 "quarantine": result["snapshot_id"]}, indent=2), encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ACTIVE.txt").write_text(str(out.resolve()), encoding="utf-8")
    return {"snapshot": str(out), "passed_nodes": passed_meta["node_count"],
            "passed_edges": passed_meta["edge_count"], **result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passed", type=Path)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.passed or snapshot_dir(), args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
