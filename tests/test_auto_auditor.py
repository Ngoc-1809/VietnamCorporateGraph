"""Auto-auditor regression tests: one per observed real-data failure mode. Texts are synthetic; the LLM is a fake object (never a Qwen result)."""
import json

from vckg.relation_extraction.candidates import load_relations
from vckg.validation import auto_auditor as aa

REL = load_relations(str(aa.ROOT / "config/relations.yaml"))


class FakeLLM:
    model, calls, hits, failures, latency = "fake", 0, 0, 0, 0.0

    def __init__(self, **kw):
        self.out = {"subject_holds_relation": True, "relation_tense": "CURRENT", "belongs_to_other_person": False, "evidence_sufficient": True, "note": "ok"} | kw

    def check(self, *a):
        return self.out


def M(text, sent, surface, label, eid, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = text.index(surface, i + 1)
    return {"article_id": "a1", "text": surface, "start": i, "end": i + len(surface), "label": label, "entity_id": eid, "link_status": "grounded",
            "linking_method": "x", "sentence_index": 0, "alias_of": None, "method": "gliner2.5", "ner_score": 0.9, "candidate_entity_ids": []}


def make(text, ments, info, pred, sid, oid, status="FACT", aliases=None):
    ev = {"article_id": "a1", "source_url": "https://e.com/a1", "evidence_text": text, "evidence_start": 0, "evidence_end": len(text), "published_at": None,
          "extraction_method": "t", "relation_score": None, "score_available": False, "validation_status": "ACCEPTED", "review_status": "AUTO_ACCEPTED",
          "factual_status": status, "valid_from": None, "valid_to": None, "model": "", "prompt_version": ""}
    ctx = aa.Context(lambda a: text if a == "a1" else None, lambda a: ments if a == "a1" else [], lambda x: x, info,
                     lambda e: set((aliases or {}).get(e, [])), REL)
    return {"subject_id": sid, "predicate": pred, "object_id": oid, "evidence": [ev], "edge_id": "e1"}, ctx


G = {"status": "ARTICLE_GROUNDED"}
INFO = {"p:a": {"name": "A", "type": "PERSON", **G}, "o:b": {"name": "B", "type": "ORGANIZATION", **G}, "p:c": {"name": "C", "type": "PERSON", **G}}


def audit(text, pred="CHAIR_OF", llm=None, required=True, status="FACT", sname="Nguyễn Văn An", oname="Công ty cổ phần Bình Minh", extra=None, info=None):
    ments = [M(text, 0, sname, "PERSON", "p:a"), M(text, 0, oname, "ORGANIZATION", "o:b"), *(extra or [])]
    e, ctx = make(text, ments, info or INFO, pred, "p:a", "o:b", status)
    return aa.audit_edge(e, ctx, llm, required)


def test_clean_edge_passes_only_with_llm_crosscheck():
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên."
    assert audit(t, llm=FakeLLM())["decision"] == "PASS"
    assert audit(t, llm=None)["decision"] == "QUARANTINE"  # fail-safe: LLM required but unavailable
    assert audit(t, llm=None, required=False)["decision"] == "PASS"


def test_llm_valid_alone_is_never_enough_and_llm_cannot_reject():
    t = "Ông Nguyễn Văn An từng là Chủ tịch HĐQT Công ty cổ phần Bình Minh trong nhiệm kỳ trước."
    r = audit(t, llm=FakeLLM(subject_holds_relation=True))
    assert r["decision"] == "AUTO_CORRECT" and r["proposed_correction"] == {"factual_status": "HISTORICAL"}  # lexical proof, not LLM
    t2 = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên."
    r2 = audit(t2, llm=FakeLLM(belongs_to_other_person=True))
    assert r2["decision"] == "QUARANTINE" and "LLM_CONTRADICTION" in r2["failed_checks"]  # downgrade only, never REJECT


def test_tenure_range_becomes_historical_not_dates():
    t = "Ông Nguyễn Văn An là Tổng Giám đốc Công ty cổ phần Bình Minh trong giai đoạn từ tháng 11/2020 đến giữa tháng 10/2026."
    r = audit(t, pred="CEO_OF", llm=FakeLLM())
    assert r["decision"] == "AUTO_CORRECT" and r["proposed_correction"] == {"factual_status": "HISTORICAL"}
    assert all(e["valid_to"] is None and e["valid_from"] is None for e in r["corrected_edge"]["evidence"])  # no inferred dates


def test_resignation_request_is_quarantined():
    t = "Ngày 08/10, ông Nguyễn Văn An - Chủ tịch HĐQT Công ty cổ phần Bình Minh có đơn xin từ nhiệm vì lý do cá nhân."
    assert "RESIGNATION_REQUEST_ONLY" in audit(t, llm=FakeLLM())["failed_checks"]


def test_role_inside_criminal_case_sentence_is_quarantined():
    t = "Chi trả cho các bị hại trong vụ án Nguyễn Văn An (Chủ tịch Công ty cổ phần Bình Minh) và đồng phạm."
    assert "ROLE_IN_CRIMINAL_CONTEXT" in audit(t, llm=FakeLLM())["failed_checks"]


def test_kinship_between_endpoints_and_other_person_between():
    t = "Ông Nguyễn Văn An, cha của bà Trần Thị Lan, Chủ tịch HĐQT Công ty cổ phần Bình Minh, phát biểu tại hội nghị lớn."
    extra = [M(t, 0, "Trần Thị Lan", "PERSON", "p:c")]
    r = audit(t, llm=FakeLLM(), extra=extra)
    assert r["decision"] == "QUARANTINE" and ({"OTHER_PERSON_BETWEEN", "KINSHIP_BETWEEN_ENDPOINTS"} & set(r["failed_checks"]))
    ok = "Bà Trần Thị Lan là vợ ông Nguyễn Văn An, Chủ tịch HĐQT Công ty cổ phần Bình Minh, theo thông tin công bố."
    r2 = audit(ok, llm=FakeLLM(), extra=[M(ok, 0, "Trần Thị Lan", "PERSON", "p:c")])
    assert r2["decision"] == "PASS"  # relative is introduced BEFORE the subject; the role cue follows the subject directly


def test_caption_only_evidence_is_quarantined_but_other_evidence_can_carry_edge():
    cap = "| Ông Nguyễn Văn An, Chủ tịch HĐQT Công ty cổ phần Bình Minh. |"
    assert audit(cap, llm=FakeLLM())["decision"] == "QUARANTINE"
    long = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên."
    ms = [M(long, 0, "Nguyễn Văn An", "PERSON", "p:a"), M(long, 0, "Công ty cổ phần Bình Minh", "ORGANIZATION", "o:b")]
    e, ctx = make(long, ms, INFO, "CHAIR_OF", "p:a", "o:b")
    ctx.mentions_all = ms
    e["evidence"].append({**e["evidence"][0], "article_id": "a2", "evidence_text": cap, "evidence_end": len(cap)})
    ctx.article_text = lambda a: {"a1": long, "a2": cap}.get(a)
    ctx.mentions = lambda a: ctx.mentions_all if a == "a1" else []
    r = aa.audit_edge(e, ctx, FakeLLM(), True)
    assert r["decision"] == "PASS" and len(r["corrected_edge"]["evidence"]) == 1


def test_evidence_mismatch_or_missing_article_fails_safe():
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên."
    e, ctx = make(t, [], INFO, "CHAIR_OF", "p:a", "o:b")
    e["evidence"][0]["evidence_text"] = "khác"
    assert aa.audit_edge(e, ctx, FakeLLM(), True)["decision"] == "QUARANTINE"
    ctx2 = aa.Context(lambda a: None, lambda a: [], lambda x: x, INFO, lambda e: set(), REL)
    assert aa.audit_edge(e, ctx2, FakeLLM(), True)["decision"] == "QUARANTINE"


def test_reversed_direction_auto_corrected_with_type_proof_and_revalidated():
    t = "Công ty cổ phần Bình Minh là Chủ tịch HĐQT ông Nguyễn Văn An theo bản tin tổng hợp trong ngày hôm nay."
    ments = [M(t, 0, "Công ty cổ phần Bình Minh", "ORGANIZATION", "p:a"), M(t, 0, "Nguyễn Văn An", "PERSON", "o:b")]
    info = {"p:a": {"name": "B", "type": "ORGANIZATION", **G}, "o:b": {"name": "A", "type": "PERSON", **G}}
    e, ctx = make(t, ments, info, "CHAIR_OF", "p:a", "o:b")
    r = aa.audit_edge(e, ctx, FakeLLM(), True)
    assert r["proposed_correction"] == {"direction": "SWAP"} and r["decision"] in ("AUTO_CORRECT", "QUARANTINE")
    if r["decision"] == "AUTO_CORRECT":
        assert (r["corrected_edge"]["subject_id"], r["corrected_edge"]["object_id"]) == ("o:b", "p:a")
    assert r["original_edge"]["subject_id"] == "p:a"  # original untouched


def test_both_directions_invalid_types_is_rejected():
    t = "Công ty cổ phần Bình Minh là Chủ tịch HĐQT Công ty cổ phần Bình Dương theo thông tin tổng hợp trong ngày."
    ments = [M(t, 0, "Công ty cổ phần Bình Minh", "ORGANIZATION", "p:a"), M(t, 0, "Công ty cổ phần Bình Dương", "ORGANIZATION", "o:b")]
    e, ctx = make(t, ments, INFO, "CHAIR_OF", "p:a", "o:b")
    assert aa.audit_edge(e, ctx, FakeLLM(), True)["decision"] == "REJECT"


def test_negation_rejected_and_planned_status_not_official():
    neg = "Ông Nguyễn Văn An không phải là Chủ tịch HĐQT Công ty cổ phần Bình Minh theo xác nhận của công ty."
    assert audit(neg, llm=FakeLLM())["decision"] == "REJECT"
    plan = "Ông Nguyễn Văn An dự kiến sẽ là Chủ tịch HĐQT Công ty cổ phần Bình Minh sau đại hội cổ đông sắp tới."
    r = audit(plan, llm=FakeLLM())
    assert r["decision"] == "QUARANTINE" and any("REVALIDATION_FAILED" in x for x in r["reasons"])  # PLANNED cannot be official


def test_prosecution_stage_and_allegation_scope():
    ctx_t = "Viện KSND Tối cao đã truy tố Shark Thủy cùng bà Lan về hành vi lừa đảo; 25 bị can cấp dưới cũng bị cáo buộc tham gia lừa đảo."
    ments = [M(ctx_t, 0, "Viện KSND Tối cao", "GOVERNMENT_AGENCY", "o:b"), M(ctx_t, 0, "Shark Thủy", "PERSON", "p:a")]
    info = {"o:b": {"name": "Viện KSND Tối cao", "type": "GOVERNMENT_AGENCY", **G}, "p:a": {"name": "Shark Thủy", "type": "PERSON", **G}}
    e, ctx = make(ctx_t, ments, info, "PROSECUTED_BY", "p:a", "o:b")
    r = aa.audit_edge(e, ctx, FakeLLM(), True)
    assert r["decision"] == "PASS" and any("INDICTMENT" in n for a in r["evidence_audits"] for n in a["notes"])
    only = "Ông Shark Thủy bị cáo buộc lừa đảo theo thông tin từ Viện KSND Tối cao trong buổi họp báo chiều nay."
    ments2 = [M(only, 0, "Viện KSND Tối cao", "GOVERNMENT_AGENCY", "o:b"), M(only, 0, "Shark Thủy", "PERSON", "p:a")]
    e2, ctx2 = make(only, ments2, info, "PROSECUTED_BY", "p:a", "o:b")
    assert "PROSECUTION_VERB_MISSING" in aa.audit_edge(e2, ctx2, FakeLLM(), True)["failed_checks"]


def test_acronym_needs_alias_record():
    t = "Ông Nguyễn Văn An, Tổng Giám đốc DMX, công bố những con số tài chính đáng chú ý của doanh nghiệp."
    ments = [M(t, 0, "Nguyễn Văn An", "PERSON", "p:a"), M(t, 0, "DMX", "ORGANIZATION", "o:b")]
    e, ctx = make(t, ments, INFO, "CEO_OF", "p:a", "o:b")
    assert "ACRONYM_NOT_IN_REGISTRY" in aa.audit_edge(e, ctx, FakeLLM(), True)["failed_checks"]
    e, ctx = make(t, ments, INFO, "CEO_OF", "p:a", "o:b", aliases={"o:b": ["dmx"]})
    assert aa.audit_edge(e, ctx, FakeLLM(), True)["decision"] == "PASS"


def test_unreproducible_relation_is_quarantined_as_inference():
    t = "Ông Nguyễn Văn An phát biểu tại hội nghị nơi Công ty cổ phần Bình Minh trình bày báo cáo thường niên."
    assert "RELATION_NOT_REPRODUCED" in audit(t, llm=FakeLLM())["failed_checks"]


def test_deputy_chair_maps_to_board_member():
    t = "Ông Nguyễn Văn An, Phó Chủ tịch HĐQT Công ty cổ phần Bình Minh, cho biết kế hoạch kinh doanh năm tới."
    r = audit(t, pred="CHAIR_OF", llm=FakeLLM())
    assert r["proposed_correction"] == {"predicate": "BOARD_MEMBER_OF"} or r["decision"] == "QUARANTINE"


# ---------------------------------------------------------------- bonds
BT = ("Vinhomes đã phát hành 80.000 trái phiếu mã VHML12618, mệnh giá 100 triệu đồng/trái phiếu, tương ứng tổng giá trị phát hành 8.000 tỷ đồng.")
BT2 = "Ngày 24/9/2026, Vinhomes đã phát hành 80.000 trái phiếu mã VHML12618 tương ứng tổng giá trị phát hành 8.000 tỷ đồng."


def bond_ctx(texts, names, issuer_same=True):
    arts = {f"b{i}": t for i, t in enumerate(texts)}
    ments = {f"b{i}": [{"article_id": f"b{i}", "text": "Vinhomes", "start": t.index("Vinhomes"), "end": t.index("Vinhomes") + 8, "label": "ORGANIZATION",
                        "entity_id": "o:v" if (issuer_same or i == 0) else "o:w", "link_status": "grounded", "linking_method": "x", "sentence_index": 0,
                        "alias_of": None, "method": "gliner2.5", "ner_score": 0.9, "candidate_entity_ids": []} for _ in [0]] for i, t in enumerate(texts)}
    info = {"o:v": {"name": "ctcp vinhomes", "type": "ORGANIZATION", **G}, "o:w": {"name": "other", "type": "ORGANIZATION", **G}}
    edges = []
    for i, (t, n) in enumerate(zip(texts, names, strict=True)):
        info[f"bond:{i}"] = {"name": n, "type": "BOND_ISSUE", **G}
        ev = {"article_id": f"b{i}", "source_url": f"https://e.com/b{i}", "evidence_text": t, "evidence_start": 0, "evidence_end": len(t), "published_at": None,
              "extraction_method": "t", "relation_score": None, "score_available": False, "validation_status": "ACCEPTED", "review_status": "AUTO_ACCEPTED",
              "factual_status": "FACT", "valid_from": None, "valid_to": None, "model": "", "prompt_version": ""}
        edges.append({"subject_id": "o:v" if (issuer_same or i == 0) else "o:w", "predicate": "ISSUED_BOND", "object_id": f"bond:{i}", "evidence": [ev], "edge_id": f"e{i}"})
    ctx = aa.Context(arts.get, lambda a: ments[a], lambda x: x, info, lambda e: set(), REL)
    return edges, ctx


def run_bonds(texts, names, **kw):
    edges, ctx = bond_ctx(texts, names, **kw)
    res = [aa.audit_edge(e, ctx, FakeLLM(), True) for e in edges]
    return aa.resolve_bond_duplicates(json.loads(json.dumps(res)), ctx)


def test_duplicate_bond_merged_with_arithmetic_proof():
    res = run_bonds([BT, BT2], ["Trái phiếu Vinhomes 100triệuđồng VHML12618", "Trái phiếu Vinhomes 8.000tỷđồng VHML12618"])
    assert [r["decision"] for r in res] == ["AUTO_CORRECT", "AUTO_CORRECT"]
    assert res[0]["corrected_edge"]["object_id"] == res[1]["corrected_edge"]["object_id"] == "bond:1"
    assert len(res[0]["corrected_edge"]["evidence"]) == 2 and "stated total" in res[0]["proposed_correction"]["merge_duplicate_bond"]["proof"]


def test_same_code_without_proof_or_other_issuer_is_not_merged():
    bad = BT2.replace("8.000 tỷ", "9.000 tỷ")
    res = run_bonds([BT, bad], ["Trái phiếu Vinhomes 100triệuđồng VHML12618", "Trái phiếu Vinhomes 9.000tỷđồng VHML12618"])
    assert [r["decision"] for r in res] == ["QUARANTINE", "QUARANTINE"] and any("BOND_CONFLICT" in x for x in res[0]["reasons"])
    other = run_bonds([BT, BT2], ["Trái phiếu Vinhomes 100triệuđồng VHML12618", "Trái phiếu Vinhomes 8.000tỷđồng VHML12618"], issuer_same=False)
    assert all(r["decision"] == "PASS" for r in other)  # different issuer ids: never grouped


def test_bond_fact_missing_from_evidence_is_quarantined():
    res = run_bonds([BT2], ["Trái phiếu Vinhomes 5.000tỷđồng VHML12618"])
    assert res[0]["decision"] == "QUARANTINE" and "BOND_FACT_NOT_IN_EVIDENCE" in res[0]["failed_checks"]


# ---------------------------------------------------------------- runner
def test_runner_checkpoint_resume_idempotent_and_outputs(tmp_path):
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên."
    e, ctx = make(t, [M(t, 0, "Nguyễn Văn An", "PERSON", "p:a"), M(t, 0, "Công ty cổ phần Bình Minh", "ORGANIZATION", "o:b")], INFO, "CHAIR_OF", "p:a", "o:b")
    llm = FakeLLM()
    s1 = aa.run([e], ctx, tmp_path, llm, log=lambda *_: None)
    s2 = aa.run([e], ctx, tmp_path, llm, log=lambda *_: None)
    assert s1["decisions"] == {"PASS": 1} and s2["resumed_from_checkpoint"] == 1 and s2["decisions"] == s1["decisions"]
    assert len((tmp_path / "checkpoint.jsonl").read_text(encoding="utf-8").splitlines()) == 1  # nothing re-audited or duplicated
    assert len((tmp_path / "validated_edges.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    assert (tmp_path / "audit_results.csv").exists() and s1["validated_unique_entities"] == 2
    assert json.loads((tmp_path / "audit_results.jsonl").read_text(encoding="utf-8"))["original_edge"] == e  # original preserved
    aa.run([e], ctx, tmp_path, llm, fresh=True, log=lambda *_: None)
    assert list(tmp_path.glob("checkpoint.*.bak.jsonl"))  # fresh run keeps the old history
