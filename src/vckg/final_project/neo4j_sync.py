"""Import a versioned, quality-filtered graph into a separate Neo4j namespace."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from vckg.final_project.app import snapshot_dir
from vckg.graph.neo4j_sync import connect


def _rows(db: sqlite3.Connection, table: str) -> list[dict]:
    db.row_factory = sqlite3.Row
    return [dict(row) for row in db.execute(f"SELECT * FROM {table}")]


def _counts(session) -> dict:
    return {
        "legacy_nodes": session.run("MATCH (n:Entity) RETURN count(n) AS n").single()["n"],
        "legacy_edges": session.run("MATCH (:Entity)-[r]->(:Entity) WHERE r.edge_id IS NOT NULL RETURN count(r) AS n").single()["n"],
        "validated_nodes": session.run("MATCH (n:VEntity) RETURN count(n) AS n").single()["n"],
        "validated_edges": session.run("MATCH (:VEntity)-[r]->(:VEntity) RETURN count(r) AS n").single()["n"],
    }


def sync(snapshot_dir: Path, *, dry_run: bool = False) -> dict:
    meta = json.loads((snapshot_dir / "metrics.json").read_text(encoding="utf-8"))
    snapshot_id = meta["snapshot_id"]
    with sqlite3.connect(snapshot_dir / "profile.sqlite") as db:
        nodes, edges = _rows(db, "nodes"), _rows(db, "edges")
    if len(nodes) != meta["node_count"] or len(edges) != meta["edge_count"]:
        raise ValueError("Snapshot counts do not match SQLite")
    result = {"snapshot_id": snapshot_id, "nodes": len(nodes), "edges": len(edges), "dry_run": dry_run}
    if dry_run:
        return result
    with connect() as driver, driver.session() as session:
        before = _counts(session)
        session.run("CREATE CONSTRAINT final_entity_uid IF NOT EXISTS FOR (n:FEntity) REQUIRE n.uid IS UNIQUE").consume()
        for start in range(0, len(nodes), 500):
            batch = [{"uid": f"{snapshot_id}|{n['node_id']}", **n} for n in nodes[start:start + 500]]
            session.run("""
                UNWIND $rows AS x
                MERGE (n:FEntity {uid:x.uid})
                SET n.snapshot_id=$snapshot, n.node_id=x.node_id, n.name=x.name,
                    n.entity_type=x.entity_type, n.identity_status=x.identity_status,
                    n.pagerank=x.pagerank, n.degree=x.degree, n.community=x.community,
                    n.core_number=x.core_number, n.component=x.component
            """, rows=batch, snapshot=snapshot_id).consume()
        for start in range(0, len(edges), 500):
            batch = [{"uid": f"{snapshot_id}|{e['edge_uid']}",
                      "subject_uid": f"{snapshot_id}|{e['subject_id']}",
                      "object_uid": f"{snapshot_id}|{e['object_id']}", **e}
                     for e in edges[start:start + 500]]
            session.run("""
                UNWIND $rows AS x
                MATCH (a:FEntity {uid:x.subject_uid}), (b:FEntity {uid:x.object_uid})
                MERGE (a)-[r:F_RELATION {uid:x.uid}]->(b)
                SET r.snapshot_id=$snapshot, r.edge_uid=x.edge_uid, r.predicate=x.predicate,
                    r.qa_tier=x.tier, r.factual_status=x.factual_status,
                    r.evidence_count=x.evidence_count, r.article_count=x.article_count,
                    r.valid_from=x.valid_from, r.valid_to=x.valid_to
            """, rows=batch, snapshot=snapshot_id).consume()
        after = _counts(session)
        if before != after:
            raise RuntimeError(f"Legacy/validated layers changed: {before} -> {after}")
        actual_nodes = session.run("MATCH (n:FEntity {snapshot_id:$snapshot}) RETURN count(n) AS n", snapshot=snapshot_id).single()["n"]
        actual_edges = session.run("MATCH (:FEntity)-[r:F_RELATION {snapshot_id:$snapshot}]->(:FEntity) RETURN count(r) AS n", snapshot=snapshot_id).single()["n"]
        if (actual_nodes, actual_edges) != (len(nodes), len(edges)):
            raise RuntimeError(f"Import incomplete: {(actual_nodes, actual_edges)} != {(len(nodes), len(edges))}")
        result.update({"neo4j_nodes": actual_nodes, "neo4j_edges": actual_edges, "other_layers_unchanged": True})
    (snapshot_dir / "neo4j_sync.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def sync_quarantine(snapshot_dir: Path, *, dry_run: bool = False) -> dict:
    """Keep candidate relationships in Q* labels, never in the passed F* layer."""
    meta = json.loads((snapshot_dir / "quarantine_metrics.json").read_text(encoding="utf-8"))
    snapshot_id = meta["snapshot_id"]
    with sqlite3.connect(snapshot_dir / "quarantine.sqlite") as db:
        nodes, edges = _rows(db, "nodes"), _rows(db, "edges")
    if len(nodes) != meta["node_count"] or len(edges) != meta["edge_count"]:
        raise ValueError("Quarantine snapshot counts do not match SQLite")
    result = {"mode": "quarantine", "snapshot_id": snapshot_id, "nodes": len(nodes),
              "edges": len(edges), "dry_run": dry_run}
    if dry_run:
        return result
    with connect() as driver, driver.session() as session:
        before = _counts(session)
        passed_before = (
            session.run("MATCH (n:FEntity) RETURN count(n) AS n").single()["n"],
            session.run("MATCH (:FEntity)-[r:F_RELATION]->(:FEntity) RETURN count(r) AS n").single()["n"],
        )
        session.run("CREATE CONSTRAINT quarantine_entity_uid IF NOT EXISTS FOR (n:QEntity) REQUIRE n.uid IS UNIQUE").consume()
        for start in range(0, len(nodes), 500):
            batch = [{"uid": f"{snapshot_id}|{node['node_id']}", **node} for node in nodes[start:start + 500]]
            session.run("""
                UNWIND $rows AS x
                MERGE (n:QEntity {uid:x.uid})
                SET n.snapshot_id=$snapshot, n.node_id=x.node_id, n.name=x.name,
                    n.entity_type=x.entity_type, n.identity_status=x.identity_status,
                    n.pagerank=x.pagerank, n.degree=x.degree, n.community=x.community,
                    n.core_number=x.core_number, n.component=x.component,
                    n.review_status='QUARANTINE', n.official=false,
                    n.endpoint_quality=x.endpoint_quality,
                    n.aggregation_method=x.aggregation_method,
                    n.source_node_ids=x.source_node_ids
            """, rows=batch, snapshot=snapshot_id).consume()
        for start in range(0, len(edges), 500):
            batch = [{"uid": f"{snapshot_id}|{edge['edge_uid']}",
                      "subject_uid": f"{snapshot_id}|{edge['subject_id']}",
                      "object_uid": f"{snapshot_id}|{edge['object_id']}", **edge}
                     for edge in edges[start:start + 500]]
            session.run("""
                UNWIND $rows AS x
                MATCH (a:QEntity {uid:x.subject_uid}), (b:QEntity {uid:x.object_uid})
                MERGE (a)-[r:Q_RELATION {uid:x.uid}]->(b)
                SET r.snapshot_id=$snapshot, r.edge_uid=x.edge_uid, r.predicate=x.predicate,
                    r.review_status='QUARANTINE', r.official=false,
                    r.factual_status=x.factual_status, r.factual_statuses=x.factual_statuses,
                    r.quarantine_classes=x.quarantine_classes,
                    r.endpoint_quality=x.endpoint_quality, r.repair_method=x.repair_method,
                    r.source_edge_uids=x.source_edge_uids,
                    r.evidence_count=x.evidence_count, r.article_count=x.article_count,
                    r.valid_from=x.valid_from, r.valid_to=x.valid_to,
                    r.validity_windows=x.validity_windows
            """, rows=batch, snapshot=snapshot_id).consume()
        after = _counts(session)
        passed_after = (
            session.run("MATCH (n:FEntity) RETURN count(n) AS n").single()["n"],
            session.run("MATCH (:FEntity)-[r:F_RELATION]->(:FEntity) RETURN count(r) AS n").single()["n"],
        )
        if before != after or passed_before != passed_after:
            raise RuntimeError("Quarantine import changed a legacy, validated or passed layer")
        actual_nodes = session.run("MATCH (n:QEntity {snapshot_id:$sid}) RETURN count(n) AS n",
                                   sid=snapshot_id).single()["n"]
        actual_edges = session.run("MATCH (:QEntity)-[r:Q_RELATION {snapshot_id:$sid}]->(:QEntity) "
                                   "RETURN count(r) AS n", sid=snapshot_id).single()["n"]
        if (actual_nodes, actual_edges) != (len(nodes), len(edges)):
            raise RuntimeError(f"Quarantine import incomplete: {(actual_nodes, actual_edges)}")
        result.update({"neo4j_nodes": actual_nodes, "neo4j_edges": actual_edges,
                       "other_layers_unchanged": True})
    (snapshot_dir / "neo4j_quarantine_sync.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=["passed", "quarantine", "both"], default="both")
    args = parser.parse_args()
    snapshot = args.snapshot or snapshot_dir()
    result = {}
    if args.mode in {"passed", "both"}:
        result["passed"] = sync(snapshot, dry_run=args.dry_run)
    if args.mode in {"quarantine", "both"} and (snapshot / "quarantine.sqlite").exists():
        result["quarantine"] = sync_quarantine(snapshot, dry_run=args.dry_run)
    elif args.mode == "quarantine":
        raise FileNotFoundError(snapshot / "quarantine.sqlite")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
