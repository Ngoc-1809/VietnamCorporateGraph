"""Phase 4 tests: structure-aware patterns/direction, modality & temporal status, span repair, LLM cache, scores.
Sentences are hypothetical. Names such as 'Lê Văn Một' are invented for structure tests."""
import httpx
import pytest

from helpers import AcceptAll, FakeNER, art, make_resolver, verdict_for
from vckg.models import EntityType, FactualStatus, Mention, ReviewStatus
from vckg.ner.merge import repair_span
from vckg.pipeline import Counters, process_article
from vckg.relation_extraction.candidates import load_relations
from vckg.relation_extraction.modality import detect_modality
from vckg.relation_extraction.qwen_verifier import LLMCache, QwenVerifier
from vckg.validation.evidence import EdgeStore

P, O, B = EntityType.PERSON, EntityType.ORGANIZATION, EntityType.BANK
REG, GOV = EntityType.REGULATOR, EntityType.GOVERNMENT_AGENCY
ROOT = __import__("helpers").ROOT
REL = load_relations(str(ROOT / "config" / "relations.yaml"))
SSC = "Ủy ban Chứng khoán Nhà nước"


def run(text, spec, verifier="accept", resolver=None, store=None, aid="p1"):
    resolver = resolver or make_resolver()
    store = store or EdgeStore()
    v = AcceptAll() if verifier == "accept" else verifier
    cn = Counters()
    res = process_article(art(text, aid, f"https://e.com/{aid}"), REL, resolver, store, FakeNER(spec), v, cn)
    return store, res, cn


# ---------------------------------------------------------------- direction from sentence structure
def test_sanction_active_voice_direction():
    t = f"{SSC} xử phạt Công ty cổ phần FPT vì công bố thông tin chậm."
    store, res, _ = run(t, {SSC: REG, "Công ty cổ phần FPT": O})
    c = [x for x in res.candidates if x.predicate == "SANCTIONED_BY"]
    assert len(c) == 1 and c[0].subject.text == "Công ty cổ phần FPT" and c[0].object.text == SSC
    assert c[0].direction_source == "pattern"
    s, p, o = next(iter(store.edges))
    assert p == "SANCTIONED_BY" and s == "org:fpt" and o != "org:fpt"  # company -> authority, never reversed


def test_sanction_passive_voice_direction():
    t = f"Công ty cổ phần FPT bị {SSC} xử phạt vì chậm công bố thông tin."
    _, res, _ = run(t, {SSC: REG, "Công ty cổ phần FPT": O})
    c = [x for x in res.candidates if x.predicate == "SANCTIONED_BY"]
    assert len(c) == 1 and (c[0].subject.text, c[0].object.text) == ("Công ty cổ phần FPT", SSC)


def test_no_reversed_sanction_candidate():
    t = f"{SSC} xử phạt Công ty cổ phần FPT."
    _, res, _ = run(t, {SSC: REG, "Công ty cổ phần FPT": O})
    assert not [x for x in res.candidates if x.subject.text == SSC]


def test_prosecution_is_charge_not_conviction_and_direction():
    t = "Bộ Công an khởi tố bị can Phạm Nhật Vượng."
    _store, res, _ = run(t, {"Bộ Công an": GOV, "Phạm Nhật Vượng": P})
    c = [x for x in res.candidates if x.predicate == "PROSECUTED_BY"]
    assert len(c) == 1 and c[0].subject.text == "Phạm Nhật Vượng" and c[0].object.text == "Bộ Công an"
    assert c[0].factual_status == FactualStatus.FACT  # 'khởi tố' = prosecuted; nothing says convicted


def test_investigation_is_alleged_never_official():
    t = "Ông Phạm Nhật Vượng đang bị Bộ Công an điều tra."
    store, res, _ = run(t, {"Bộ Công an": GOV, "Phạm Nhật Vượng": P})
    c = [x for x in res.candidates if x.predicate == "PROSECUTED_BY"]
    assert c and c[0].factual_status == FactualStatus.ALLEGED
    assert store.official_edges() == [] and store.edges


def test_cue_tied_to_endpoint_not_to_nearest_org():
    t = "Ông Ge Jun, Chủ tịch kiêm Tổng Giám đốc TOJOY, từng làm việc tại Intel, Apple và Nvidia."
    _, res, _ = run(t, {"Ge Jun": P, "TOJOY": O, "Intel": O, "Apple": O, "Nvidia": O})
    assert {(c.predicate, c.object.text) for c in res.candidates} == {("CHAIR_OF", "TOJOY"), ("CEO_OF", "TOJOY")}
    assert all(c.factual_status == FactualStatus.FACT for c in res.candidates)  # trailing 'từng...' clause ignored


def test_parenthetical_alias_not_separate_candidate():
    t = "Lê Văn Một (Mr A), Trần Văn Hai (Bác B) - Chủ tịch HĐQT Công ty cổ phần Sao Mai Test - tiếp tục gây chú ý."
    spec = {"Lê Văn Một": P, "Mr A": P, "Trần Văn Hai": P, "Bác B": P, "Công ty cổ phần Sao Mai Test": O}
    _, res, _ = run(t, spec)
    assert [(c.predicate, c.subject.text) for c in res.candidates] == [("CHAIR_OF", "Trần Văn Hai")]


def test_chair_and_ceo_from_combined_title():
    t = "Trung tướng Tào Đức Thắng, Chủ tịch kiêm Tổng giám đốc Tập đoàn Viettel, cho biết kế hoạch."
    _, res, _ = run(t, {"Tào Đức Thắng": P, "Viettel": O})
    assert {c.predicate for c in res.candidates} == {"CHAIR_OF", "CEO_OF"}


def test_typed_direction_credit_contract():
    for t in ("Ngân hàng VPBank ký hợp đồng tín dụng với Vingroup.", "Vingroup ký hợp đồng tín dụng với Ngân hàng VPBank."):
        _, res, _ = run(t, {"Ngân hàng VPBank": O, "Vingroup": O})  # NER says ORG; registry refines to BANK
        c = [x for x in res.candidates if x.predicate == "LENDS_TO"]
        assert len(c) == 1 and c[0].subject.text == "Ngân hàng VPBank" and c[0].subject.label == B


def test_ownership_and_subsidiary_patterns():
    _, res, _ = run("Vingroup sở hữu 51% vốn của VinFast.", {"Vingroup": O, "VinFast": O})
    assert [(c.predicate, c.subject.text, c.object.text) for c in res.candidates] == [("OWNS_SHARES_IN", "Vingroup", "VinFast")]
    _, res, _ = run("Vingroup là công ty mẹ của Vinhomes.", {"Vingroup": O, "Vinhomes": O})
    c = [x for x in res.candidates if x.predicate == "SUBSIDIARY_OF"]
    assert len(c) == 1 and (c[0].subject.text, c[0].object.text) == ("Vinhomes", "Vingroup")


def test_acquisition_completed_vs_in_negotiation():
    _, r1, _ = run("Vingroup đã hoàn tất thương vụ mua lại VinFast.", {"Vingroup": O, "VinFast": O})
    assert r1.candidates[0].factual_status == FactualStatus.FACT
    _, r2, _ = run("Vingroup đang đàm phán mua lại VinFast.", {"Vingroup": O, "VinFast": O})
    assert r2.candidates[0].factual_status == FactualStatus.PLANNED
    _, r3, _ = run("Vingroup chưa hoàn tất thương vụ mua lại VinFast.", {"Vingroup": O, "VinFast": O})
    assert r3.candidates[0].factual_status == FactualStatus.PLANNED


def test_ended_role_is_official_with_ended_status():
    store, res, _ = run("Ông Nguyễn Văn Tám đã thôi giữ chức Tổng giám đốc Vingroup.", {"Nguyễn Văn Tám": P, "Vingroup": O})
    assert res.candidates[0].factual_status == FactualStatus.ENDED
    e = store.official_edges()[0]
    assert e.evidence[0].factual_status == FactualStatus.ENDED


def test_former_role_is_historical():
    _, res, _ = run("Ông Nguyễn Văn Tám, nguyên Chủ tịch HĐQT Vingroup, phát biểu.", {"Nguyễn Văn Tám": P, "Vingroup": O})
    assert res.candidates and res.candidates[0].factual_status == FactualStatus.HISTORICAL


# ---------------------------------------------------------------- modality table (whole-sentence use)
@pytest.mark.parametrize("sentence,expected", [
    ("Công ty không có kế hoạch mua lại VinFast.", FactualStatus.DENIED),
    ("Ông A đã phủ nhận thông tin chủ tịch.", FactualStatus.DENIED),
    ("Ông A chưa từng là chủ tịch.", FactualStatus.DENIED),
    ("Ông A được tuyên vô tội.", FactualStatus.DENIED),
    ("A dự kiến mua lại B.", FactualStatus.PLANNED),
    ("A có thể mua lại B.", FactualStatus.PLANNED),
    ("A đang xem xét mua lại B.", FactualStatus.PLANNED),
    ("A đang đàm phán mua lại B.", FactualStatus.PLANNED),
    ("A chưa hoàn tất thương vụ mua lại B.", FactualStatus.PLANNED),
    ("A đã hoàn tất thương vụ mua lại B.", FactualStatus.FACT),
    ("Ông A đã thôi giữ chức chủ tịch.", FactualStatus.ENDED),
    ("Ông A từng là chủ tịch B.", FactualStatus.HISTORICAL),
    ("Ông A bị cáo buộc thao túng.", FactualStatus.ALLEGED),
    ("Ông A đang bị điều tra.", FactualStatus.ALLEGED),
    ("Ông A bị khởi tố.", FactualStatus.FACT),
    ("Ông A là chủ tịch B.", FactualStatus.FACT),
])
def test_modality_statuses(sentence, expected):
    assert detect_modality(sentence)[0] == expected


def test_status_aliases():
    assert FactualStatus.CONFIRMED is FactualStatus.FACT and FactualStatus.NEGATED is FactualStatus.DENIED


def test_negated_never_edge_planned_candidate_only():
    s1, _, _ = run("Vingroup không mua lại VinFast.", {"Vingroup": O, "VinFast": O})
    assert not s1.edges
    s2, _, _ = run("Vingroup có thể mua lại VinFast.", {"Vingroup": O, "VinFast": O})
    assert s2.edges and s2.official_edges() == []


# ---------------------------------------------------------------- span repair (real-article boundary errors)
def mm(text, s, label=P):
    i = text.index(s)
    return Mention(text=s, start=i, end=i + len(s), label=label, ner_score=0.9, method="gliner2.5")


def test_repair_person_title_and_org_role_prefix_and_suffix():
    t = "Ông Zhang Qiang, Tổng Giám đốc Công ty TNHH China Railway Sixth Group Việt Nam, phát biểu."
    r = repair_span(t, mm(t, "Ông Zhang Qiang"))
    assert r.text == "Zhang Qiang" and t[r.start:r.end] == r.text
    r2 = repair_span(t, mm(t, "China Railway Sixth Group", O))
    assert r2.text == "Công ty TNHH China Railway Sixth Group Việt Nam" and t[r2.start:r2.end] == r2.text
    t2 = "Chủ tịch HĐQT Công ty cổ phần Ngân Lượng nói."
    r3 = repair_span(t2, mm(t2, "HĐQT Công ty cổ phần Ngân Lượng", O))
    assert r3.text == "Công ty cổ phần Ngân Lượng"


# ---------------------------------------------------------------- scores / confidence
def test_scores_are_none_when_unavailable():
    store, _res, _ = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.", {"Phạm Nhật Vượng": P, "Vingroup": O})
    r = next(iter(store.edges.values())).evidence[0]
    assert r.relation_score is None and r.score_available is False
    assert r.subject_ner_score == 0.9  # real GLiNER-style score is kept separately
    assert r.review_status == ReviewStatus.AUTO_ACCEPTED and r.model == "test-double"
    dic = [m for m in make_resolver().scan_dictionary("Công ty Vingroup công bố.")]
    assert all(m.ner_score is None for m in dic)  # dictionary mentions have no score; none invented


# ---------------------------------------------------------------- reruns, unknown entities
def test_idempotent_rerun_no_duplicates():
    resolver, store = make_resolver(), EdgeStore()
    t, spec = "Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.", {"Phạm Nhật Vượng": P, "Vingroup": O}
    run(t, spec, resolver=resolver, store=store)
    n_ent, n_ev = resolver.store.count_entities(), len(next(iter(store.edges.values())).evidence)
    run(t, spec, resolver=resolver, store=store)
    assert resolver.store.count_entities() == n_ent and len(next(iter(store.edges.values())).evidence) == n_ev == 1
    assert resolver.store.db.execute("SELECT COUNT(*) FROM mentions WHERE article_id='p1'").fetchone()[0] == 2


def test_unknown_org_becomes_provisional_candidate_not_official():
    resolver = make_resolver()
    before = resolver.store.count_entities(status="PROVISIONAL")
    store, _res, cn = run("Ông Trần Văn Hai là Chủ tịch HĐQT Công ty cổ phần Sao Mai Test.",
                         {"Trần Văn Hai": P, "Công ty cổ phần Sao Mai Test": O}, resolver=resolver)
    assert resolver.store.count_entities(status="PROVISIONAL") == before + 2  # person cluster + org
    assert store.edges and store.official_edges() == [] and cn.linked_provisional == 2
    assert cn.validator_candidate_edge == 1


# ---------------------------------------------------------------- LLM cache (HTTP transport double; not a Qwen result)
class _Resp:
    def __init__(self, body): self._b = body
    def raise_for_status(self): pass
    def json(self): return self._b


def _fake_post(counter, content):
    def post(url, json=None, timeout=None):
        counter["n"] += 1
        return _Resp({"message": {"content": content}, "prompt_eval_count": 120, "eval_count": 40})
    return post


def test_llm_cache_hit_saves_calls_and_prompt_version_invalidates(monkeypatch):
    _store, res, _ = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.", {"Phạm Nhật Vượng": P, "Vingroup": O})
    c = res.candidates[0]
    content = verdict_for(c).model_dump_json()
    counter = {"n": 0}
    monkeypatch.setattr(httpx, "post", _fake_post(counter, content))
    v = QwenVerifier(cache=LLMCache(":memory:"))
    assert v.verify(c) is not None and v.verify(c) is not None
    assert counter["n"] == 1 and v.stats.cache_hits == 1 and v.stats.calls == 1
    assert v.stats.prompt_tokens == 120 and v.stats.eval_tokens == 40
    v.prompt_version = "v-next"  # new prompt => key changes => miss
    assert v.verify(c) is not None and counter["n"] == 2


def test_llm_parse_failure_counted_and_returns_none(monkeypatch):
    _store, res, _ = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.", {"Phạm Nhật Vượng": P, "Vingroup": O})
    counter = {"n": 0}
    monkeypatch.setattr(httpx, "post", _fake_post(counter, '{"valid": true}'))
    v = QwenVerifier(cache=LLMCache(":memory:"))
    assert v.verify(res.candidates[0], retries=1) is None
    assert v.stats.parse_failures == 2 and counter["n"] == 2


def test_llm_historical_without_rule_cue_is_ignored_but_planned_is_honored():
    t = "Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup."
    for llm_status, expected in ((FactualStatus.HISTORICAL, FactualStatus.FACT), (FactualStatus.PLANNED, FactualStatus.PLANNED),
                                 (FactualStatus.ALLEGED, FactualStatus.ALLEGED)):
        class V:
            model, prompt_version = "t", "t"
            def verify(self, c, definition="", _s=llm_status):
                return verdict_for(c, factual_status=_s)
        store, _, _ = run(t, {"Phạm Nhật Vượng": P, "Vingroup": O}, verifier=V())
        ev = next(iter(store.edges.values())).evidence[0]
        assert ev.factual_status == expected
        if llm_status == FactualStatus.HISTORICAL:
            assert "ignored_no_cue" in ev.validation_status and ev.review_status == ReviewStatus.AUTO_ACCEPTED
        else:
            assert ev.review_status == ReviewStatus.NEEDS_REVIEW


# ---------------------------------------------------------------- recall fixes found on real articles
def test_parenthetical_ticker_aside_does_not_block_pattern():
    t = "CTCP Cao su Phước Hòa (mã: PHR) là cổ đông lớn nhất của NTC sở hữu 7,88 triệu cổ phiếu."
    _, res, _ = run(t, {"CTCP Cao su Phước Hòa": O, "NTC": O, "PHR": O})
    assert [(c.predicate, c.subject.text, c.object.text) for c in res.candidates] == [("OWNS_SHARES_IN", "CTCP Cao su Phước Hòa", "NTC")]


def test_cp_unit_in_ownership():
    _, res, _ = run("CTCP Beston sở hữu hơn 87 triệu cp VIB, tương đương 2,33% vốn điều lệ.", {"CTCP Beston": O, "VIB": B})
    assert [(c.predicate, c.subject.text, c.object.text) for c in res.candidates] == [("OWNS_SHARES_IN", "CTCP Beston", "VIB")]


def test_received_sanction_decision_direction():
    t = "CTCP Nhiệt điện Phả Lại thông báo nhận được quyết định xử phạt vi phạm hành chính về thuế từ Cục Thuế Hải Phòng."
    _, res, _ = run(t, {"CTCP Nhiệt điện Phả Lại": O, "Cục Thuế Hải Phòng": GOV})
    c = [x for x in res.candidates if x.predicate == "SANCTIONED_BY"]
    assert len(c) == 1 and (c[0].subject.text, c[0].object.text) == ("CTCP Nhiệt điện Phả Lại", "Cục Thuế Hải Phòng")


def test_sanction_recipient_is_not_the_authority():
    t = "CTCP Xây dựng MCD bị phạt 92,5 triệu đồng do không gửi Sở Giao dịch Chứng khoán Hà Nội tài liệu."
    _, res, _ = run(t, {"CTCP Xây dựng MCD": O, "Sở Giao dịch Chứng khoán Hà Nội": GOV})
    assert not res.candidates  # HNX is the recipient of the filing, nothing says it sanctioned


def test_prosecution_with_bi_can_phrase():
    t = "Cơ quan An ninh điều tra Công an TP Đà Nẵng đã khởi tố ba bị can gồm Chu Đức Anh về tội rửa tiền."
    _, res, _ = run(t, {"Cơ quan An ninh điều tra Công an TP Đà Nẵng": GOV, "Chu Đức Anh": P})
    assert [(c.predicate, c.subject.text) for c in res.candidates] == [("PROSECUTED_BY", "Chu Đức Anh")]


def test_legal_form_suffix_joined_to_name():
    t = "Tổng Công ty Phát điện 2 - CTCP (EVNGENCO 2) là cổ đông lớn nhất của PPC."
    m = mm(t, "Tổng Công ty Phát điện 2", O)
    assert repair_span(t, m).text == "Tổng Công ty Phát điện 2 - CTCP"


def test_unknown_acronym_org_becomes_provisional_without_ticker_but_known_ticker_does_not():
    resolver = make_resolver()
    t1 = "Chị Tô Thị Phương Thảo là Chủ tịch VBOX."
    _store, res, _ = run(t1, {"Tô Thị Phương Thảo": P, "VBOX": O}, resolver=resolver)
    vbox = next(m for m in res.mentions if m.text == "VBOX")
    assert vbox.link_status == "provisional" and resolver.store.get_entity(vbox.entity_id)["ticker"] is None
    t2 = "GDP tăng trưởng mạnh."
    r2 = run(t2, {"GDP": O}, resolver=resolver)[1].mentions[0]
    assert r2.entity_id is None and r2.linking_method == "acronym_unverified"
    # a token that IS a registry ticker without cue/context must not spawn a duplicate provisional entity
    r3 = run("TCB đã tăng.", {"TCB": B}, resolver=resolver)[1].mentions[0]
    assert r3.entity_id is None and r3.linking_method == "ticker_without_context"


def test_llm_quote_may_drop_aside_but_not_invent_words():
    from vckg.reasons import quote_supported
    s = "CTCP Nhiệt điện Phả Lại (HOSE: PPC) thông báo nhận được quyết định xử phạt từ Cục Thuế TP. Hải Phòng, do khai sai"
    assert quote_supported("CTCP Nhiệt điện Phả Lại thông báo nhận được quyết định xử phạt từ Cục Thuế TP. Hải Phòng", s)
    assert quote_supported("thông báo nhận được quyết định xử phạt", s)
    assert not quote_supported("CTCP Nhiệt điện Phả Lại bị khởi tố", s)  # invented words
    assert not quote_supported("Hải Phòng thông báo CTCP", s)  # order violated


def test_hdtv_role_prefix_trimmed_from_org_span():
    t = "Ông Đỗ Giang Nam được bổ nhiệm làm Chủ tịch HĐTV Nhà máy In tiền Quốc gia."
    r = repair_span(t, mm(t, "HĐTV Nhà máy In tiền Quốc gia", O))
    assert r.text == "Nhà máy In tiền Quốc gia" and t[r.start:r.end] == r.text


def test_hdtv_chair_pattern_matches_after_prefix_trim():
    t = "Ông Đỗ Giang Nam chính thức được bổ nhiệm làm Chủ tịch HĐTV Nhà máy In tiền Quốc gia."
    _, res, _ = run(t, {"Đỗ Giang Nam": P, "Nhà máy In tiền Quốc gia": O})
    assert [(c.predicate, c.subject.text, c.object.text) for c in res.candidates] == [("CHAIR_OF", "Đỗ Giang Nam", "Nhà máy In tiền Quốc gia")]


def test_reverse_kiem_order_and_also_is():
    t = "Bà Nguyễn Thùy Nga là Tổng giám đốc kiêm Chủ tịch HĐQT Công ty cổ phần Sao Mai Test."
    _, res, _ = run(t, {"Nguyễn Thùy Nga": P, "Công ty cổ phần Sao Mai Test": O})
    assert {c.predicate for c in res.candidates} == {"CHAIR_OF", "CEO_OF"}
    t2 = "Ngoài ra, bà Nguyễn Thùy Nga còn là Chủ tịch HĐQT Công ty cổ phần Sao Mai Test."
    _, r2, _ = run(t2, {"Nguyễn Thùy Nga": P, "Công ty cổ phần Sao Mai Test": O})
    assert [c.predicate for c in r2.candidates] == ["CHAIR_OF"]


def test_acting_ceo_and_subsidiary_with_ownership_percentage():
    _, r1, _ = run("Ông Nguyễn Trần Minh Quân, Quyền Tổng giám đốc EVS, phát biểu.", {"Nguyễn Trần Minh Quân": P, "EVS": O})
    assert [c.predicate for c in r1.candidates] == ["CEO_OF"]
    _, r2, _ = run("Công ty TNHH Năng lượng REE - công ty con 100% vốn của REE - nắm hơn 64 triệu cp.", {"Công ty TNHH Năng lượng REE": O, "REE": O})
    c = [x for x in r2.candidates if x.predicate == "SUBSIDIARY_OF"]
    assert len(c) == 1 and c[0].subject.text == "Công ty TNHH Năng lượng REE" and c[0].object.text == "REE"
