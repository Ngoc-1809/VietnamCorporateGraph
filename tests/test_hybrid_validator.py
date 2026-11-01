"""Phase 6B.2 regression tests for the hybrid validator (synthetic sentences; no Qwen)."""
import inspect

from vckg.models import FactualStatus, Mention, RelationCandidate
from vckg.relation_extraction.candidates import load_relations
from vckg.validation import hybrid_validator as hv

REL = load_relations(str(hv.__file__).split("src")[0] + "config/relations.yaml")
G = {"status": "ARTICLE_GROUNDED"}
INFO = {k: {"name": k, **G} for k in ("p:a", "p:c", "o:b", "o:d", "o:e", "g:x", "o:v")}


def mk(text, subj, obj, pred, status="FACT", sl="PERSON", ol="ORGANIZATION", sid="p:a", oid="o:b", extra=None, aid="art1"):
    def m(surface, label, eid):
        i = text.index(surface)
        return {"text": surface, "start": i, "end": i + len(surface), "label": label, "entity_id": eid, "alias_of": None}
    s, o = m(subj, sl, sid), m(obj, ol, oid)
    ments = [s, o, *(extra or [])]

    def to(d):
        return Mention(text=d["text"], start=d["start"], end=d["end"], label=d["label"], entity_id=d["entity_id"], article_id=aid, link_status="grounded")
    c = RelationCandidate(candidate_id="c", article_id=aid, subject=to(s), object=to(o), predicate=pred, sentence_index=0, evidence_text=text, evidence_start=0,
                          evidence_end=len(text), factual_status=FactualStatus(status), method="llm")
    return c, ments


def val(text, subj, obj, pred, methods=("RULE",), **kw):
    info = kw.pop("info", INFO)
    c, ments = mk(text, subj, obj, pred, **kw)
    return hv.validate_candidate(c, text, ments, info, lambda x: x, REL, set(methods), False)


def test_module_does_not_call_the_candidate_generator():
    imports = [ln for ln in inspect.getsource(hv).splitlines() if ln.startswith(("import ", "from "))]
    assert not any(x in ln for ln in imports for x in ("generate_candidates", "auto_auditor", "qwen", "httpx", "llm"))


def test_evidence_must_match_article_and_missing_is_failsafe():
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên."
    c, ments = mk(t, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF")
    assert hv.validate_candidate(c, t, ments, INFO, lambda x: x, REL, {"RULE"}).decision == "PASS"
    assert hv.validate_candidate(c, t.replace("Ông", "Bà"), ments, INFO, lambda x: x, REL, {"RULE"}).decision == "QUARANTINE"  # article text differs
    assert hv.validate_candidate(c, "", ments, INFO, lambda x: x, REL, {"RULE"}).decision == "QUARANTINE"  # evidence unreachable
    short = "| Ông Nguyễn Văn An, Chủ tịch HĐQT Công ty cổ phần Bình Minh. |"
    assert val(short, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF").hard_failed == ["EVIDENCE_CAPTION_OR_SHORT"]


def test_invalid_entity_types_rejected_and_reversed_types_corrected():
    t = "Công ty cổ phần Bình Minh là Chủ tịch HĐQT Công ty cổ phần Bình Dương theo thông tin tổng hợp trong ngày."
    assert val(t, "Công ty cổ phần Bình Minh", "Công ty cổ phần Bình Dương", "CHAIR_OF", sl="ORGANIZATION", ol="ORGANIZATION", sid="o:b", oid="o:d").decision == "REJECT"
    t2 = "Công ty cổ phần Bình Minh có Chủ tịch HĐQT là ông Nguyễn Văn An theo bản tin tổng hợp trong ngày hôm nay."
    v = val(t2, "Công ty cổ phần Bình Minh", "Nguyễn Văn An", "CHAIR_OF", sl="ORGANIZATION", ol="PERSON", sid="o:b", oid="p:a")
    assert v.corrections.get("direction") == "SWAP"


def test_same_name_confusion_person_id_of_another_article():
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên."
    info = {**INFO, "person:nguyen-van-an@art:other": {"name": "x", **G}}
    v = val(t, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF", sid="person:nguyen-van-an@art:other", info=info)
    assert "SAME_NAME_CONFUSION" in v.hard_failed and v.decision == "QUARANTINE"
    assert val(t, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF", sid="person:nguyen-van-an@art:art1", info={**INFO, "person:nguyen-van-an@art:art1": {"name": "x", **G}}).decision == "PASS"


def test_short_person_name_and_generic_org_are_conservative():
    t = "Ông Bình là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên của công ty."
    assert "IDENTITY_SHORT_PERSON_NAME" in val(t, "Bình", "Công ty cổ phần Bình Minh", "CHAIR_OF").hard_failed
    t2 = "Công ty cổ phần Đầu tư Sunrise nắm 95% vốn điều lệ của doanh nghiệp tại Việt Nam trước tháng 11."
    v = val(t2, "Công ty cổ phần Đầu tư Sunrise", "Việt Nam", "OWNS_SHARES_IN", sl="ORGANIZATION", sid="o:d", oid="o:e")
    assert "IDENTITY_GENERIC_ORG_NAME" in v.hard_failed


def test_family_member_attribution_rejected_but_relative_introduced_before_subject_is_fine():
    ments_t = "Bà Chu Thị Lương là vợ ông Đỗ Quý Hải, Chủ tịch HĐQT Công ty cổ phần Hải Phát, theo công bố mới."
    i = ments_t.index("Đỗ Quý Hải")
    hai = {"text": "Đỗ Quý Hải", "start": i, "end": i + 10, "label": "PERSON", "entity_id": "p:c", "alias_of": None}
    wrong = val(ments_t, "Chu Thị Lương", "Công ty cổ phần Hải Phát", "CHAIR_OF", extra=[hai])
    assert wrong.decision == "REJECT" and wrong.semantic_code == "FAMILY_MEMBER_ATTRIBUTION"
    ok = val(ments_t, "Đỗ Quý Hải", "Công ty cổ phần Hải Phát", "CHAIR_OF", sid="p:c", extra=[{"text": "Chu Thị Lương", "start": ments_t.index("Chu Thị Lương"), "end": ments_t.index("Chu Thị Lương") + 13, "label": "PERSON", "entity_id": "p:a", "alias_of": None}])
    assert ok.decision == "PASS"


def test_acquisition_needs_an_act_and_the_right_buyer():
    own = "Sau đợt phát hành, Bolt Holdings nắm 62,82% vốn điều lệ, thay thế ông Cao Tấn Thành để trở thành cổ đông kiểm soát."
    v = val(own, "Bolt Holdings", "vốn điều lệ", "ACQUIRED", sl="ORGANIZATION", sid="o:b", oid="o:d")
    assert v.semantic_code == "ACQUISITION_ACT_MISSING" and v.decision == "QUARANTINE"
    done = "Elmet Group hoàn tất mua 55,14 triệu cp Công ty cổ phần Masan High-Tech từ Công ty TNHH Tầm Nhìn Masan trong tháng này."
    assert val(done, "Elmet Group", "Công ty cổ phần Masan High-Tech", "ACQUIRED", methods=("RULE",), sl="ORGANIZATION", sid="o:b", oid="o:d").decision == "PASS"
    sale = "Công ty TNHH Năng lượng REE thoái toàn bộ 8 triệu cp Công ty cổ phần Sử Pán cho Công ty cổ phần Phát triển Hà Thành với giá 282 tỷ đồng."
    assert val(sale, "Hà Thành", "Công ty cổ phần Sử Pán", "ACQUIRED", sl="ORGANIZATION", sid="o:b", oid="o:d").semantic == "OK"
    lep = "Công ty cổ phần Lepus, công ty con của Tập đoàn Masan, đã mua 73 triệu cp của Công ty cổ phần Hàng tiêu dùng Masan trong tháng."
    i = lep.index("Công ty cổ phần Lepus")
    lepus = {"text": "Công ty cổ phần Lepus", "start": i, "end": i + 21, "label": "ORGANIZATION", "entity_id": "o:v", "alias_of": None}
    v2 = val(lep, "Tập đoàn Masan", "Công ty cổ phần Hàng tiêu dùng Masan", "ACQUIRED", sl="ORGANIZATION", sid="o:b", oid="o:d", extra=[lepus])
    assert v2.semantic_code == "ACQUIRER_NOT_AGENT"


def test_registration_only_is_not_ownership_but_completed_purchase_is():
    reg = "Công ty cổ phần MB Capital đăng ký bán hơn 2 triệu cp của Công ty cổ phần Gas Petrolimex từ ngày 22/10 đến 19/11."
    assert val(reg, "Công ty cổ phần MB Capital", "Công ty cổ phần Gas Petrolimex", "OWNS_SHARES_IN", sl="ORGANIZATION", sid="o:b", oid="o:d").semantic_code in ("OWNERSHIP_CUE_MISSING", "REGISTRATION_ONLY")
    done = "Bà Chu Thị Lương báo cáo hoàn tất mua 15 triệu cp của Công ty cổ phần Đầu tư Hải Phát như đăng ký ban đầu."
    assert val(done, "Chu Thị Lương", "Công ty cổ phần Đầu tư Hải Phát", "OWNS_SHARES_IN").semantic == "OK"


def test_ownership_reduction_to_positive_percentage_is_not_ended():
    t = "Sau thoái vốn, TTC Group rút hoàn toàn khỏi SBT, tỷ lệ sở hữu của bà Huỳnh Bích Ngọc giảm xuống mức 0,23% vốn của công ty."
    v = val(t, "Huỳnh Bích Ngọc", "công ty", "OWNS_SHARES_IN", status="ENDED", info=INFO)
    assert v.corrections.get("factual_status") == "FACT" and v.final_status == "FACT"
    t2 = "Bà Huỳnh Bích Ngọc không còn sở hữu cổ phần của Công ty cổ phần Thành Thành Công kể từ tháng này, theo báo cáo công bố."
    v2 = val(t2, "Huỳnh Bích Ngọc", "Công ty cổ phần Thành Thành Công", "OWNS_SHARES_IN", status="ENDED")
    assert v2.corrections.get("factual_status") != "FACT"


def test_founder_is_not_just_a_shareholder_or_a_hired_proxy():
    cap = "Công ty cổ phần Bolt Holdings thành lập năm 2024, vốn điều lệ 10 tỷ đồng, do ông Đỗ Hoàng Minh góp 80% và ông Đinh Văn Hiệp 10%."
    assert val(cap, "Đỗ Hoàng Minh", "Công ty cổ phần Bolt Holdings", "FOUNDED").semantic == "INSUFFICIENT"
    proxy = "Để phục vụ giao dịch, bà Hải thuê ông Nguyễn Trung Hiếu thành lập Công ty TNHH Tư Gia làm vỏ bọc cho hoạt động này."
    assert val(proxy, "Nguyễn Trung Hiếu", "Công ty TNHH Tư Gia", "FOUNDED").semantic_code == "PROXY_FOUNDER"
    real = "Ông Nguyễn Văn An là người sáng lập Công ty cổ phần Bình Minh vào năm 2010 và điều hành đến nay một cách liên tục."
    assert val(real, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "FOUNDED").decision == "PASS"


def test_historical_positions_and_resignation_request():
    t = "Ông Nguyễn Văn An là Tổng Giám đốc Công ty cổ phần Bình Minh trong giai đoạn từ tháng 11/2020 đến giữa tháng 10/2026."
    v = val(t, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CEO_OF")
    assert v.decision == "AUTO_CORRECT" and v.final_status == "HISTORICAL" and v.corrections == {"factual_status": "HISTORICAL"}
    r = "Ngày 8/10, ông Nguyễn Văn An - Chủ tịch HĐQT Công ty cổ phần Bình Minh có đơn xin từ nhiệm vì lý do cá nhân của mình."
    assert "RESIGNATION_REQUEST_ONLY" in val(r, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF").hard_failed


def test_deputy_chair_maps_to_board_member():
    t = "Ông Nguyễn Văn An, Phó Chủ tịch HĐQT Công ty cổ phần Bình Minh, cho biết kế hoạch kinh doanh năm tới của công ty."
    v = val(t, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF")
    assert v.corrections.get("predicate") == "BOARD_MEMBER_OF"


def test_rule_disagreement_is_a_signal_not_a_blocker_and_semantic_only_never_passes():
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh và chủ trì cuộc họp thường niên."
    v = val(t, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF", methods=("LLM",))
    assert v.agreement == "SEMANTIC_ONLY" and v.decision == "QUARANTINE" and v.quarantine_class == "SEMANTIC_ONLY_CLEAN"
    assert not v.hard_failed and v.semantic == "OK"  # nothing independent failed
    assert val(t, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF", methods=("LLM", "RULE")).decision == "PASS"
    junk = "Ông Nguyễn Văn An phát biểu tại hội nghị nơi Công ty cổ phần Bình Minh trình bày báo cáo thường niên của mình."
    w = val(junk, "Nguyễn Văn An", "Công ty cổ phần Bình Minh", "CHAIR_OF", methods=("LLM",))
    assert w.agreement == "INSUFFICIENT_EVIDENCE" and w.possible_inference


def test_negation_strong_rejected_generic_not_and_planned_not_official():
    neg = "Bà Đỗ Thị Hoàng Yến không sở hữu cổ phiếu của Công ty cổ phần Mai Châu theo công bố của công ty ngày hôm nay."
    assert val(neg, "Đỗ Thị Hoàng Yến", "Công ty cổ phần Mai Châu", "OWNS_SHARES_IN").decision == "REJECT"
    plan = "Công ty cổ phần Bình Minh dự kiến sẽ mua lại Công ty cổ phần Bình Dương trong quý tới theo kế hoạch công bố."
    v = val(plan, "Công ty cổ phần Bình Minh", "Công ty cổ phần Bình Dương", "ACQUIRED", sl="ORGANIZATION", sid="o:b", oid="o:d")
    assert v.final_status == "PLANNED" and v.decision == "QUARANTINE" and v.quarantine_class == "NON_OFFICIAL_STATUS"


def test_subsidiary_needs_parent_child_grammar_and_fixes_direction():
    ok = "Hoa Lư Bình Phước là công ty con của Công ty cổ phần Khoáng sản Bình Dương, sở hữu gián tiếp 93,24% vốn điều lệ."
    assert val(ok, "Hoa Lư Bình Phước", "Công ty cổ phần Khoáng sản Bình Dương", "SUBSIDIARY_OF", sl="ORGANIZATION", sid="o:b", oid="o:d").decision == "PASS"
    rev = "Công ty cổ phần Khoáng sản Bình Dương là công ty mẹ của Hoa Lư Bình Phước, theo thông tin công bố mới nhất của công ty."
    assert val(rev, "Công ty cổ phần Khoáng sản Bình Dương", "Hoa Lư Bình Phước", "SUBSIDIARY_OF", sl="ORGANIZATION", sid="o:b", oid="o:d").corrections.get("direction") == "SWAP"
    coop = "Công ty cổ phần Bình Minh hợp tác với Công ty cổ phần Bình Dương, cả hai đều là công ty trong ngành công nghiệp thực phẩm."
    assert val(coop, "Công ty cổ phần Bình Minh", "Công ty cổ phần Bình Dương", "SUBSIDIARY_OF", sl="ORGANIZATION", sid="o:b", oid="o:d").semantic == "INSUFFICIENT"


def test_prosecution_stage_and_sanction_recipient():
    t = "Viện KSND Tối cao đã truy tố ông Nguyễn Văn An cùng bà Lan về hành vi lừa đảo chiếm đoạt tài sản trong vụ án lớn."
    v = val(t, "Nguyễn Văn An", "Viện KSND Tối cao", "PROSECUTED_BY", ol="GOVERNMENT_AGENCY")
    assert v.decision == "PASS" and any("INDICTMENT" in n for n in v.notes)
    inv = "Ông Nguyễn Văn An bị cáo buộc lừa đảo theo thông tin từ Viện KSND Tối cao trong buổi họp báo chiều nay của cơ quan."
    assert val(inv, "Nguyễn Văn An", "Viện KSND Tối cao", "PROSECUTED_BY", ol="GOVERNMENT_AGENCY").semantic_code == "PROSECUTION_VERB_MISSING"
    s = "Công ty cổ phần MCD bị phạt 92,5 triệu đồng do không gửi Sở Giao dịch Chứng khoán Hà Nội tài liệu theo quy định hiện hành."
    v2 = val(s, "Công ty cổ phần MCD", "Sở Giao dịch Chứng khoán Hà Nội", "SANCTIONED_BY", sl="ORGANIZATION", ol="GOVERNMENT_AGENCY", sid="o:b", oid="g:x")
    assert v2.decision == "REJECT" and v2.semantic_code == "AUTHORITY_IS_RECIPIENT"


def test_bond_facts_must_be_in_evidence():
    ev = "Công ty cổ phần Vinhomes đã phát hành 80.000 trái phiếu mã VHML12618, mệnh giá 100 triệu đồng, tổng giá trị phát hành 8.000 tỷ đồng."
    c, ments = mk(ev, "Công ty cổ phần Vinhomes", "trái phiếu mã VHML12618", "ISSUED_BOND", sl="ORGANIZATION", ol="BOND_ISSUE", sid="o:v", oid="o:b")
    ok = hv.validate_candidate(c, ev, ments, INFO, lambda x: x, REL, {"RULE"}, False, "Trái phiếu Vinhomes 8.000tỷđồng VHML12618")
    bad = hv.validate_candidate(c, ev, ments, INFO, lambda x: x, REL, {"RULE"}, False, "Trái phiếu Vinhomes 5.000tỷđồng VHML12618")
    assert ok.decision == "PASS" and bad.semantic_code == "BOND_FACT_NOT_IN_EVIDENCE" and bad.decision == "QUARANTINE"
