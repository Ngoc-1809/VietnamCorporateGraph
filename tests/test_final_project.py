"""Quality and traversal checks for the final-project graph snapshot."""

import sqlite3

import networkx as nx

from vckg.final_project.app import _cites_retrieved_sources, _path_sqlite
from vckg.final_project.build import _endpoints_ok, _official, analyze
from vckg.final_project.quality_audit import evaluate


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


def test_graph_answer_references_only_retrieved_sources():
    assert _cites_retrieved_sources("Theo bài [1] và [2].", 2)
    assert not _cites_retrieved_sources("Theo bài [3].", 2)
    assert not _cites_retrieved_sources("Có liên hệ.", 2)
