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
from vckg.entity_linking.normalize import fold, slugify
from vckg.final_project.app import snapshot_dir
from vckg.final_project.build import OUT, ROOT, SCHEMA, _identity, _read
from vckg.final_project.generic_repair import VERSION, agency_key, propose


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


def _repair(row: dict, article_text: str | None, named_nodes: dict[str, set[str]],
            nodes: dict[str, dict]) -> tuple[dict, dict] | None:
    """Repair one evidence row; never infer a name from another sentence or article."""
    if not article_text:
        return None
    try:
        start, end = int(row["evidence_start"]), int(row["evidence_end"])
    except (TypeError, ValueError):
        return None
    if start < 0 or end <= start or article_text[start:end] != row["evidence_text"]:
        return None
    proposal = propose(row)
    if proposal is None:
        return None
    is_agency = proposal.rule == "NAMED_AUTHORITY_SAME_SENTENCE"
    key = agency_key(proposal.name) if is_agency else f"org:{slugify(fold(proposal.name))}"
    if not key:
        return None
    existing = named_nodes.get(key, set()) if key else set()
    if len(existing) > 1:
        return None  # conflicting existing identities require manual review
    side = proposal.side
    old_id = row[f"{side}_id"]
    new_id = next(iter(existing)) if existing else f"repair:{'agency:' if is_agency else ''}{key}"
    if new_id == row[f"{'subject' if side == 'object' else 'object'}_id"]:
        return None
    if not existing and new_id not in nodes:
        grounded = is_agency or proposal.rule == "NAMED_GROUP_SAME_SENTENCE" or fold(proposal.name).startswith(
            ("cong ty", "ctcp", "tong cong ty"))
        nodes[new_id] = {"node_id": new_id, "name": proposal.name,
                         "entity_type": row[f"{side}_type"],
                         "identity_status": "ARTICLE_GROUNDED" if grounded else "PROVISIONAL",
                         "aliases": ""}
        named_nodes.setdefault(key, set()).add(new_id)
    changed = dict(row)
    changed[f"{side}_id"] = new_id
    changed[f"{side}_name"] = nodes[new_id]["name"]
    changed[f"{side}_identity_status"] = nodes[new_id]["identity_status"]
    changed[f"{side}_type"] = nodes[new_id]["entity_type"]
    if proposal.reverse:
        for field in ("id", "name", "identity_status", "type"):
            changed[f"subject_{field}"], changed[f"object_{field}"] = (
                changed[f"object_{field}"], changed[f"subject_{field}"])
    changed["edge_id"] = "repair:" + hashlib.sha1("|".join((
        changed["subject_id"], changed["relation_type"], changed["object_id"],
        changed["factual_status"], changed["valid_from"], changed["valid_to"])).encode()).hexdigest()[:20]
    changed["_repair_method"] = proposal.rule
    log = {"source_edge_uid": _identity(row), "repaired_edge_uid": _identity(changed),
           "article_id": row["article_id"], "source_url": row["source_url"],
           "old_node_id": old_id, "new_node_id": new_id, "old_name": row[f"{side}_name"],
           "new_name": nodes[new_id]["name"], "rule": proposal.rule,
           "evidence_start": start, "evidence_end": end, "evidence_text": row["evidence_text"]}
    return changed, log


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
    repair_log: list[dict] = []
    original_uids: set[str] = set()
    source_uids: dict[str, set[str]] = defaultdict(set)
    named_nodes: dict[str, set[str]] = defaultdict(set)
    for node_id, node in nodes.items():
        if not is_generic_entity(node["name"]):
            key = agency_key(node["name"])
            if key:
                named_nodes[key].add(node_id)
            if node["entity_type"] in {"ORGANIZATION", "BANK"}:
                named_nodes[f"org:{slugify(fold(node['name']))}"].add(node_id)
    source_db = ROOT / "data/staging/staging.sqlite"
    with sqlite3.connect(f"file:{source_db.as_posix()}?mode=ro", uri=True) as corpus:
        article_cache: dict[str, str | None] = {}
        for original in _read(er / "edges_v2.csv"):
            if original["qa_tier"] != "QUARANTINE":
                continue
            original_uids.add(_identity(original))
            row = original
            if is_generic_entity(original["subject_name"]) or is_generic_entity(original["object_name"]):
                article_id = original["article_id"]
                if article_id not in article_cache:
                    article = corpus.execute("SELECT text FROM articles WHERE article_id=?", (article_id,)).fetchone()
                    article_cache[article_id] = article[0] if article else None
                repaired = _repair(original, article_cache[article_id], named_nodes, nodes)
                if repaired:
                    row, log = repaired
                    repair_log.append(log)
            uid = _identity(row)
            selected.setdefault(uid, row)
            source_uids[uid].add(_identity(original))
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
        db.execute("ALTER TABLE edges ADD COLUMN repair_method TEXT")
        db.execute("ALTER TABLE edges ADD COLUMN source_edge_uids TEXT")
        db.execute("""CREATE TABLE repair_log(source_edge_uid TEXT, repaired_edge_uid TEXT,
                   article_id TEXT, source_url TEXT, old_node_id TEXT, new_node_id TEXT,
                   old_name TEXT, new_name TEXT, rule TEXT, evidence_start INTEGER,
                   evidence_end INTEGER, evidence_text TEXT)""")
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
                              endpoint_quality,repair_method,source_edge_uids)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
            (uid, row["edge_id"], "QUARANTINE", row["subject_id"], row["relation_type"],
             row["object_id"], row["factual_status"], row["valid_from"], row["valid_to"],
             len(ev_by_edge[uid]), len({item["article_id"] for item in ev_by_edge[uid]}),
             row["quarantine_classes"], row["discovery_methods"],
             "ELIGIBLE" if uid in eligible else "GENERIC_ENDPOINT" if
             row["subject_id"] in generic or row["object_id"] in generic else "SELF_LOOP",
             row.get("_repair_method", ""), json.dumps(sorted(source_uids[uid])))
            for uid, row in sorted(selected.items())])
        db.executemany("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)", [
            (eid, row["edge_uid"], row["article_id"], row["source_url"], row["publisher"],
             row["published_at"], row["evidence_text"], row["extraction_method"],
             int(row["evidence_start"] or 0), int(row["evidence_end"] or 0))
            for eid, row in sorted(evidence.items())])
        db.executemany("INSERT INTO repair_log VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", [
            tuple(log[key] for key in ("source_edge_uid", "repaired_edge_uid", "article_id",
                "source_url", "old_node_id", "new_node_id", "old_name", "new_name", "rule",
                "evidence_start", "evidence_end", "evidence_text")) for log in repair_log])
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
    repair_path = out / "generic_repair_log.csv"
    with repair_path.open("w", encoding="utf-8-sig", newline="") as file:
        fields = ["source_edge_uid", "repaired_edge_uid", "article_id", "source_url",
                  "old_node_id", "new_node_id", "old_name", "new_name", "rule",
                  "evidence_start", "evidence_end", "evidence_text"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(repair_log)
    reasons = Counter()
    statuses = Counter()
    for row in selected.values():
        statuses[row["factual_status"]] += 1
        for reason in json.loads(row["quarantine_classes"] or "[]"):
            reasons[reason] += 1
    result = {"mode": "quarantine", "snapshot_id": f"{passed_meta['snapshot_id']}-quarantine-{stamp}",
              "source_snapshot_id": passed_meta["source_snapshot_id"], "source_er": str(er),
              "node_count": len(used), "edge_count": len(selected), "evidence_count": len(evidence),
              "source_candidate_edges": len(original_uids),
              "relation_types": len({row["relation_type"] for row in selected.values()}),
              "generic_name_nodes": len(generic),
              "generic_repair_version": VERSION,
              "repaired_evidence_rows": len(repair_log),
              "repaired_source_edges": len({log["source_edge_uid"] for log in repair_log}),
              "repaired_candidate_edges": len({log["repaired_edge_uid"] for log in repair_log}),
              "new_specific_nodes": len({log["new_node_id"] for log in repair_log if log["new_node_id"].startswith("repair:")}),
              "repair_log": str(repair_path),
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
