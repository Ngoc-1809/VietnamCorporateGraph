"""Graph-view contracts for filtering, bounded drawing, and review-only candidates."""
import sqlite3

from fastapi.testclient import TestClient

from vckg.final_project.app import app
from vckg.final_project.build import SCHEMA
from vckg.final_project.graph_view import overview, subgraph


def _snapshot(tmp_path):
    nodes = [
        ("a", "Alpha", "ORGANIZATION", 0),
        ("b", "Beta", "ORGANIZATION", 0),
        ("c", "Chi", "PERSON", 0),
        ("d", "Delta", "BANK", 1),
    ]
    for filename, quarantine in (("profile.sqlite", False), ("quarantine.sqlite", True)):
        with sqlite3.connect(tmp_path / filename) as db:
            db.executescript(SCHEMA)
            if quarantine:
                db.execute("ALTER TABLE edges ADD COLUMN endpoint_quality TEXT")
            db.executemany("INSERT INTO nodes(node_id,name,entity_type,identity_status,aliases,pagerank,"
                           "degree,in_degree,out_degree,community,core_number,component) "
                           "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", [
                (key, name, kind, "ARTICLE_GROUNDED", "[]", 0.25, 2, 1, 1, community, 1, 0)
                for key, name, kind, community in nodes])
            edges = [("ab", "a", "b", "PARTNERS_WITH", "FACT", "ELIGIBLE"),
                     ("ac", "a", "c", "CEO_OF", "FACT", "ELIGIBLE"),
                     ("bd", "b", "d", "LENDS_TO", "FACT", "ELIGIBLE")]
            if quarantine:
                edges.append(("generic", "c", "d", "CEO_OF", "DENIED", "GENERIC_ENDPOINT"))
            for uid, source, target, relation, status, quality in edges:
                db.execute("INSERT INTO edges(edge_uid,edge_id,tier,subject_id,predicate,object_id,"
                           "factual_status,valid_from,valid_to,evidence_count,article_count) "
                           "VALUES(?,?,?,?,?,?,?,?,?,?,?)", (uid, uid, "QUARANTINE" if quarantine else "QA_PASS",
                                                      source, relation, target, status, None, None, 1, 1))
                if quarantine:
                    db.execute("UPDATE edges SET endpoint_quality=? WHERE edge_uid=?", (quality, uid))
                db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)", (
                    uid, uid, uid, f"https://example.org/{uid}", "Example", "2026-11-01",
                    f"Source evidence for {uid}", "RULE", 0, 20))
    return str(tmp_path)


def test_filters_apply_before_limits_and_overview_preserves_communities(tmp_path):
    snapshot = _snapshot(tmp_path)
    filtered = subgraph(snapshot, "passed", "global", 2, 1, predicates=("CEO_OF",),
                        min_incident_edges=1)
    assert filtered["counts"]["filtered_nodes"] == 2
    assert filtered["counts"]["filtered_edges"] == 1
    assert {(edge["source"], edge["target"]) for edge in filtered["edges"]} == {("a", "c")}
    assert subgraph(snapshot, "passed", "global", 4, 3, predicates=("CEO_OF",),
                    min_incident_edges=2)["nodes"] == []
    overview_result = overview(snapshot, "passed")
    assert overview_result["counts"]["total_communities"] == 2
    assert overview_result["counts"]["filtered_edges"] == 3
    assert sum(item["member_count"] for item in overview_result["nodes"]) == 4


def test_focused_graph_is_bounded_and_keeps_edge_direction(tmp_path):
    snapshot = _snapshot(tmp_path)
    result = subgraph(snapshot, "passed", "neighborhood", 2, 1, node_id="a", hops=1)
    assert result["counts"]["filtered_nodes"] == 3
    assert result["counts"]["drawn_nodes"] == 2
    assert len(result["edges"]) == 1
    assert result["edges"][0]["source"] == "a"
    assert result["counts"]["truncated_nodes"]


def test_quarantine_review_edges_are_accessible_but_not_drawn(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    monkeypatch.setenv("VCKG_FINAL_SNAPSHOT", snapshot)
    client = TestClient(app)
    graph = client.get("/api/graph/subgraph", params={"mode": "quarantine", "scope": "global",
                                                      "max_nodes": 4, "max_edges": 4}).json()
    assert {edge["uid"] for edge in graph["edges"]} == {"ab", "ac", "bd"}
    review = client.get("/api/graph/review/c", params={"limit": 1}).json()
    assert review["total"] == 1
    assert review["relations"][0]["edge_uid"] == "generic"
    evidence = client.get("/api/graph/edge/generic", params={"mode": "quarantine"}).json()
    assert evidence["evidence"][0]["source_url"] == "https://example.org/generic"
    assert client.get("/api/graph/overview", params={"mode": "quarantine",
                                                     "predicates": "CEO_OF"}).json()["counts"]["filtered_edges"] == 1
