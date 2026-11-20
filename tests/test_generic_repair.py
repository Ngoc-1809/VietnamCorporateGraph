"""Evidence-local repairs must not turn vague agencies into false identities."""
from __future__ import annotations

from collections import defaultdict

from vckg.final_project.generic_repair import agency_key, propose
from vckg.final_project.quarantine import _network_eligible, _repair


def row(subject: str, object_: str, evidence: str, relation: str) -> dict[str, str]:
    return {"qa_tier": "QUARANTINE", "edge_id": "source", "article_id": "a1",
            "source_url": "https://example.test/article", "subject_id": "subject",
            "subject_name": subject, "subject_type": "ORGANIZATION", "subject_identity_status": "ARTICLE_GROUNDED",
            "object_id": "generic", "object_name": object_, "object_type": "GOVERNMENT_AGENCY",
            "object_identity_status": "PROVISIONAL", "relation_type": relation,
            "factual_status": "FACT", "valid_from": "", "valid_to": "",
            "evidence_start": "0", "evidence_end": str(len(evidence)), "evidence_text": evidence}


def test_named_tax_office_replaces_generic_node_with_source_verified() -> None:
    evidence = "Cục Thuế tỉnh Tiền Giang xử phạt CTCP Dược thú Y Cai Lậy."
    item = row("CTCP Dược thú Y Cai Lậy", "Cục Thuế", evidence, "SANCTIONED_BY")
    nodes = {"generic": {"name": "Cục Thuế"}, "subject": {"name": item["subject_name"]}}
    changed, log = _repair(item, evidence, defaultdict(set), nodes) or (None, None)
    assert changed is not None and log is not None
    assert changed["object_name"] == "Cục Thuế tỉnh Tiền Giang"
    assert changed["object_id"].startswith("repair:agency:tax:")
    assert changed["qa_tier"] == "QUARANTINE"
    assert log["source_edge_uid"] == "QUARANTINE:source"
    assert _repair(item, evidence + " ", defaultdict(set), nodes) is not None
    assert _repair(item, evidence.replace("Tiền", "Hậu"), defaultdict(set), nodes) is None


def test_police_name_stops_before_verb_and_normalizes_city() -> None:
    item = row("ông Diệp Dũng", "công an", "Công an TP.HCM đã khởi tố ông Diệp Dũng.", "PROSECUTED_BY")
    proposal = propose(item)
    assert proposal is not None and proposal.name == "Công an TP.HCM"
    assert agency_key("Công an TP.HCM") == agency_key("Công an TPHCM")


def test_inspector_cannot_be_inferred_from_another_sentence() -> None:
    item = row("Công ty A", "Thanh tra", "Công ty A bị xử phạt. Thanh tra Bộ Y tế xử phạt Công ty B.",
               "SANCTIONED_BY")
    assert propose(item) is None


def test_bare_authority_or_invalid_city_stays_generic() -> None:
    assert propose(row("Công ty A", "Cục Thuế", "Cục Thuế xử phạt Công ty A.", "SANCTIONED_BY")) is None
    assert propose(row("Công ty A", "công an", "Công an TP Quảng Ninh khởi tố Công ty A.",
                       "PROSECUTED_BY")) is None


def test_named_inspector_is_specific() -> None:
    item = row("APEC Group", "Thanh tra", "APEC Group bị Thanh tra Chứng khoán Nhà nước xử phạt.",
               "SANCTIONED_BY")
    assert propose(item).name == "Thanh tra Chứng khoán Nhà nước"


def test_group_is_replaced_only_when_one_named_group_and_relation_cue() -> None:
    item = row("Baoshang Bank", "Group", "Tomorrow Group đã vay vốn từ Baoshang Bank.", "LENDS_TO")
    assert propose(item).name == "Tomorrow Group"
    assert propose(row("Baoshang Bank", "Group", "Tomorrow Group và Other Group vay từ Baoshang Bank.",
                       "LENDS_TO")) is None


def test_subsidiary_repair_reverses_parent_to_child_only_with_explicit_name() -> None:
    evidence = "CTCP Phú Tài thành lập công ty con là Công ty TNHH MTV Phú Tài Home."
    item = row("CTCP Phú Tài", "công ty con", evidence, "SUBSIDIARY_OF")
    proposal = propose(item)
    assert proposal is not None and proposal.reverse
    nodes = {"generic": {"name": "công ty con"}, "subject": {"name": item["subject_name"]}}
    changed, _ = _repair(item, evidence, defaultdict(set), nodes) or (None, None)
    assert changed is not None
    assert changed["subject_name"] == "Công ty TNHH MTV Phú Tài Home"
    assert changed["object_name"] == "CTCP Phú Tài"


def test_subsidiary_does_not_guess_from_a_list_or_wrong_parent() -> None:
    item = row("Công ty A", "công ty con", "Công ty A có hai công ty con là Công ty B và Công ty C.",
               "SUBSIDIARY_OF")
    assert propose(item) is None
    item = row("công ty con", "CTCP Đầu tư LDG",
               "Công ty Đất Xanh - công ty con của Tập đoàn Đất Xanh - đã bán cổ phiếu CTCP Đầu tư LDG.",
               "SUBSIDIARY_OF")
    assert propose(item) is None


def test_denied_candidate_is_never_a_network_edge() -> None:
    item = {"subject_id": "a", "object_id": "b", "factual_status": "DENIED"}
    assert not _network_eligible(item, set())
    item["factual_status"] = "FACT"
    assert _network_eligible(item, set())
