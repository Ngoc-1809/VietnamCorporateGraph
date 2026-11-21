"""Quarantine aggregation keeps source decisions without promoting candidates."""
from __future__ import annotations

import json
import sqlite3

from vckg.final_project.app import _evidence
from vckg.final_project.quarantine_aggregate import aggregate, person_overlay, status_for_role


def _nodes() -> dict[str, dict]:
    return {
        "p1": {"node_id": "p1", "name": "Nguyễn Đức Vinh", "entity_type": "PERSON",
               "identity_status": "ARTICLE_GROUNDED", "aliases": ""},
        "p2": {"node_id": "p2", "name": "Nguyễn Đức Vinh", "entity_type": "PERSON",
               "identity_status": "ARTICLE_GROUNDED", "aliases": ""},
        "bank": {"node_id": "bank", "name": "VPBank", "entity_type": "BANK",
                 "identity_status": "VERIFIED", "aliases": ""},
    }


def _role_row(person_id: str, article_id: str, text: str, status: str = "FACT") -> dict:
    return {"qa_tier": "QUARANTINE", "edge_id": f"{person_id}:{article_id}:{status}",
            "subject_id": person_id, "object_id": "bank", "subject_name": "Nguyễn Đức Vinh",
            "object_name": "VPBank", "relation_type": "CEO_OF", "factual_status": status,
            "article_id": article_id, "evidence_text": text, "evidence_start": "0",
            "evidence_end": str(len(text)), "source_url": f"https://example.test/{article_id}",
            "publisher": "test", "published_at": "2020-01-01", "extraction_method": "RULE",
            "quarantine_classes": '["NON_OFFICIAL_STATUS"]' if status == "PLANNED" else '["HARD_BLOCK"]',
            "discovery_methods": '["RULE"]', "valid_from": "", "valid_to": ""}


def test_future_esop_does_not_make_existing_ceo_role_planned():
    nodes = _nodes()
    esop = _role_row("p1", "a1", "Tổng Giám đốc VPBank Nguyễn Đức Vinh sẽ được phân bổ cổ phiếu ESOP.", "PLANNED")
    future = _role_row("p1", "a2", "Nguyễn Đức Vinh sẽ được bổ nhiệm làm Tổng Giám đốc VPBank.", "PLANNED")
    assert status_for_role(esop, nodes)[0] == "FACT"
    assert status_for_role(future, nodes) == ("PLANNED", "")


def test_person_overlay_requires_shared_named_org_and_role():
    nodes = _nodes()
    rows = [_role_row("p1", "a1", "Tổng Giám đốc VPBank Nguyễn Đức Vinh cho biết."),
            _role_row("p2", "a2", "Ông Nguyễn Đức Vinh, Tổng Giám đốc VPBank, phát biểu.")]
    mapping, groups = person_overlay(rows, nodes)
    assert mapping["p1"] == mapping["p2"]
    assert len(groups) == 1
    assert nodes[mapping["p1"]]["identity_status"] == "PROVISIONAL"
    nodes["bank"]["identity_status"] = "PROVISIONAL"
    assert person_overlay(rows, nodes) == ({}, {})


def test_same_relation_aggregates_statuses_and_preserves_source_reasons():
    nodes = _nodes()
    first = _role_row("p1", "a1", "Tổng Giám đốc VPBank Nguyễn Đức Vinh cho biết.")
    second = _role_row("p2", "a2", "Tổng Giám đốc VPBank Nguyễn Đức Vinh sẽ nhận cổ phiếu ESOP.", "PLANNED")
    third = {**second, "edge_id": "another-qa-reason", "quarantine_classes": '["SEMANTIC_ONLY_CLEAN"]'}
    edges, evidence, sources, mapping, groups, metrics = aggregate(
        [(first, first), (second, second), (third, third)], nodes)
    assert len(groups) == len(edges) == 1
    assert len(evidence) == 2
    edge = next(iter(edges.values()))
    assert edge["factual_status"] == "FACT"
    assert json.loads(edge["quarantine_classes"]) == ["HARD_BLOCK", "NON_OFFICIAL_STATUS", "SEMANTIC_ONLY_CLEAN"]
    assert len(next(iter(sources.values()))) == 3
    assert len(set(mapping.values())) == 1
    esop = next(row for row in evidence.values() if row["article_id"] == "a2")
    assert json.loads(esop["source_factual_statuses"]) == ["PLANNED"]
    assert json.loads(esop["quarantine_classes"]) == ["NON_OFFICIAL_STATUS", "SEMANTIC_ONLY_CLEAN"]
    assert len(json.loads(esop["source_edge_uids"])) == 2
    assert metrics["source_evidence_rows"] == 3
    assert metrics["aggregated_evidence_rows"] == 2


def test_mixed_status_stays_per_evidence_and_denied_quote_is_not_path_support():
    nodes = _nodes()
    fact = _role_row("p1", "a1", "Tổng Giám đốc VPBank Nguyễn Đức Vinh cho biết.")
    denied = _role_row("p1", "a2", "Không có quan hệ CEO với VPBank.", "DENIED")
    edges, evidence, *_ = aggregate([(fact, fact), (denied, denied)], nodes)
    assert len(edges) == 1
    assert next(iter(edges.values()))["factual_status"] == "MIXED"
    assert {item["factual_status"] for item in evidence.values()} == {"FACT", "DENIED"}

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE evidence(edge_uid TEXT, article_id TEXT, source_url TEXT,
               publisher TEXT, published_at TEXT, evidence_text TEXT, extraction_method TEXT,
               factual_status TEXT, source_factual_statuses TEXT, quarantine_classes TEXT,
               source_edge_uids TEXT, status_adjustment TEXT)""")
    for row in evidence.values():
        db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   (row["edge_uid"], row["article_id"], row["source_url"], row["publisher"],
                    row["published_at"], row["evidence_text"], row["extraction_method"],
                    row["factual_status"], row["source_factual_statuses"], row["quarantine_classes"],
                    row["source_edge_uids"], row["status_adjustment"]))
    uid = next(iter(edges))
    assert len(_evidence(db, uid, mode="quarantine")) == 2
    assert [item["factual_status"] for item in _evidence(db, uid, mode="quarantine", path_only=True)] == ["FACT"]
    db.execute("UPDATE evidence SET factual_status='MIXED', source_factual_statuses='[\"FACT\",\"DENIED\"]' "
               "WHERE factual_status='FACT'")
    assert _evidence(db, uid, mode="quarantine", path_only=True) == []
