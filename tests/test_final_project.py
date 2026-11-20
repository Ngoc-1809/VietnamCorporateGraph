"""Quality and traversal checks for the final-project graph snapshot."""

import csv
import json
import sqlite3

import networkx as nx
from fastapi.testclient import TestClient

from vckg.final_project.app import _cites_retrieved_sources, _path_sqlite, app
from vckg.final_project.build import SCHEMA, _endpoints_ok, _official, analyze
from vckg.final_project.quality_audit import evaluate, export_benchmark


def test_nonofficial_status_cannot_enter_profile_graph():
    row = {"qa_tier": "QA_PASS", "factual_status": "FACT", "in_validated_graph": "1"}
    assert _official(row)
    for status in ("PLANNED", "ALLEGED", "UNKNOWN", "DENIED"):
        assert not _official({**row, "factual_status": status})
    assert not _official({**row, "qa_tier": "QUARANTINE"})


def test_canonical_endpoint_gate_rejects_provisional_and_one_word_organization():
    edge = {"subject_id": "a", "object_id": "b", "subject_identity_status": "ARTICLE_GROUNDED",
            "object_identity_status": "VERIFIED"}
    nodes = {"a": {"name": "Hương", "entity_type": "ORGANIZATION", "identity_status": "ARTICLE_GROUNDED"},
             "b": {"name": "ACB", "entity_type": "BANK", "identity_status": "VERIFIED"}}
    assert not _endpoints_ok(edge, nodes)
    nodes["a"]["name"] = "CTCP Thiên Hương"
    assert _endpoints_ok(edge, nodes)
    edge["object_identity_status"] = "PROVISIONAL"
    assert not _endpoints_ok(edge, nodes)


def test_disconnected_graph_reports_no_whole_graph_mean_path():
    graph = nx.Graph([("a", "b"), ("b", "c")])
    graph.add_node("isolated")
    directed = nx.DiGraph([("a", "b"), ("b", "c")])
    directed.add_node("isolated")
    metrics, nodes = analyze(graph, directed, random_trials=0)
    assert metrics["whole_graph_average_shortest_path"] is None
    assert metrics["largest_component_average_shortest_path"] == 4 / 3
    assert metrics["largest_component"] == 3
    assert nodes["b"]["core_number"] == 1


def test_bounded_path_uses_edges_and_stops_at_three_hops():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE edges(subject_id TEXT,object_id TEXT,edge_uid TEXT)")
    db.executemany("INSERT INTO edges VALUES(?,?,?)", [("a", "b", "ab"), ("b", "c", "bc"),
                                                    ("c", "d", "cd"), ("d", "e", "de")])
    assert _path_sqlite(db, "a", "d") == (["a", "b", "c", "d"], ["ab", "bc", "cd"])
    assert _path_sqlite(db, "a", "e") is None
    db.close()


def test_ai_review_cannot_be_reported_as_gold_precision(tmp_path):
    sample = tmp_path / "sample.csv"
    sample.write_text("qa_tier,reviewer,review_mode,valid_relation,valid_endpoints,valid_evidence\n"
                      "QA_PASS,assistant,AI_ASSISTED,YES,YES,YES\n", encoding="utf-8")
    result = evaluate(sample)
    assert result["edge_precision_estimate"] is None
    assert result["independently_human_reviewed"] == 0


def test_balanced_diagnostic_sample_does_not_claim_overall_precision(tmp_path):
    sample = tmp_path / "diagnostic.csv"
    sample.write_text("sample_group,relation_type,reviewer,review_mode,valid_relation,valid_endpoints,valid_evidence,valid_status\n"
                      "VALIDATED,CEO_OF,human,HUMAN_FULL_ARTICLE,YES,YES,YES,YES\n", encoding="utf-8")
    result = evaluate(sample)
    assert result["diagnostic_validated_reviewed"] == 1
    assert result["edge_precision_estimate"] is None


def test_random_benchmark_requires_complete_review_and_checks_status(tmp_path):
    sample = tmp_path / "benchmark.csv"
    header = "sample_group,reviewer,review_mode,valid_relation,valid_endpoints,valid_evidence,valid_status\n"
    one = "BENCHMARK_RANDOM,human,HUMAN_FULL_ARTICLE,YES,YES,YES,YES\n"
    sample.write_text(header + one + "BENCHMARK_RANDOM,,,,,,\n", encoding="utf-8")
    assert evaluate(sample)["edge_precision_estimate"] is None
    sample.write_text(header + one + "BENCHMARK_RANDOM,human,HUMAN_FULL_ARTICLE,YES,YES,YES,NO\n", encoding="utf-8")
    result = evaluate(sample)
    assert result["edge_precision_estimate"] == 0.5
    assert result["benchmark_correct"] == 1
    assert result["wilson_95"][0] < 0.5 < result["wilson_95"][1]


def test_benchmark_samples_unique_triples_with_a_source(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    with sqlite3.connect(snapshot / "profile.sqlite") as db:
        db.executescript("""
            CREATE TABLE nodes(node_id TEXT,name TEXT,entity_type TEXT);
            CREATE TABLE edges(edge_uid TEXT,edge_id TEXT,tier TEXT,subject_id TEXT,predicate TEXT,
                               object_id TEXT,factual_status TEXT);
            CREATE TABLE evidence(evidence_id TEXT,edge_uid TEXT,article_id TEXT,source_url TEXT,
                                  published_at TEXT,evidence_text TEXT);
            INSERT INTO nodes VALUES('a','A','PERSON'),('b','B','ORGANIZATION'),('c','C','ORGANIZATION');
            INSERT INTO edges VALUES('e1','id1','QA_PASS','a','CEO_OF','b','FACT'),
                                    ('e2','id2','QA_PASS','a','CEO_OF','b','FACT'),
                                    ('e3','id3','QA_PASS','a','CHAIR_OF','c','FACT');
            INSERT INTO evidence VALUES('q1','e1','art1','https://example.org/1','2026-01-01','A là CEO B'),
                                       ('q2','e2','art2','https://example.org/2','2026-01-02','A là CEO B'),
                                       ('q3','e3','art3','https://example.org/3','2026-01-03','A là chủ tịch C');
        """)
    output = tmp_path / "sample.csv"
    result = export_benchmark(snapshot, output, size=3)
    with output.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert result["population_unique_triples"] == 2
    assert len(rows) == 2
    assert {row["relation_type"] for row in rows} == {"CEO_OF", "CHAIR_OF"}
    assert all(row["source_url"] for row in rows)


def test_passed_and_quarantine_api_use_separate_graphs(tmp_path, monkeypatch):
    monkeypatch.setenv("VCKG_FINAL_SNAPSHOT", str(tmp_path))
    for mode, filename, endpoint in (("passed", "profile.sqlite", "Passed Firm"),
                                     ("quarantine", "quarantine.sqlite", "Candidate Firm")):
        with sqlite3.connect(tmp_path / filename) as connection:
            connection.executescript(SCHEMA)
            connection.executemany("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", [
                ("person", "Test Person", "PERSON", "ARTICLE_GROUNDED", "[]", 0.5, 1, 0, 1, 0, 1, 0),
                (endpoint, endpoint, "ORGANIZATION", "PROVISIONAL", "[]", 0.5, 1, 1, 0, 0, 1, 0),
            ])
            connection.execute("INSERT INTO edges VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                mode, mode, "QA_PASS" if mode == "passed" else "QUARANTINE",
                "person", "CEO_OF", endpoint, "FACT", "", "", 1, 1))
            connection.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)", (
                mode, mode, "article", "https://example.org", "Example", "2026-01-01",
                "Test Person is CEO", "RULE", 0, 18))
    client = TestClient(app)
    assert client.get("/api/search", params={"q": "Candidate", "mode": "passed"}).json() == []
    assert len(client.get("/api/search", params={"q": "Candidate", "mode": "quarantine"}).json()) == 1
    passed = client.get("/api/profile/person", params={"mode": "passed"}).json()
    quarantine = client.get("/api/profile/person", params={"mode": "quarantine"}).json()
    assert passed["relations"][0]["object_id"] == "Passed Firm"
    assert quarantine["relations"][0]["object_id"] == "Candidate Firm"
    assert quarantine["relations"][0]["tier"] == "QUARANTINE"
    (tmp_path / "quarantine_metrics.json").write_text(
        json.dumps({"snapshot_id": "test-quarantine"}), encoding="utf-8")
    monkeypatch.setattr("vckg.final_project.app._path_neo4j", lambda *_args: None)
    answer = client.post("/api/ask", json={"start_id": "person", "target_id": "Candidate Firm",
                                           "mode": "quarantine", "question": "What is their relation?"}).json()
    assert answer["path"]["found"]
    assert answer["model_used"] is False
    assert "QUARANTINE" in answer["warning"]


def test_graph_answer_references_only_retrieved_sources():
    assert _cites_retrieved_sources("Theo bài [1] và [2].", 2)
    assert not _cites_retrieved_sources("Theo bài [3].", 2)
    assert not _cites_retrieved_sources("Có liên hệ.", 2)
