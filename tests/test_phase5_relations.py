"""Phase 5 recall structures (sentences are hypothetical, modelled on structures seen in dev articles)."""
from helpers import AcceptAll, FakeNER, art, make_resolver
from vckg.models import EntityType, FactualStatus, Mention
from vckg.ner.merge import merge_split_orgs, propagate_mentions
from vckg.pipeline import Counters, process_article
from vckg.reasons import ReasonCode
from vckg.relation_extraction.candidates import load_relations
from vckg.validation.evidence import EdgeStore

P, O, B = EntityType.PERSON, EntityType.ORGANIZATION, EntityType.BANK
GOV = EntityType.GOVERNMENT_AGENCY
REL = load_relations(str(__import__("helpers").ROOT / "config" / "relations.yaml"))


def run(t, spec, verifier="accept"):
    v = AcceptAll() if verifier == "accept" else verifier
    store = EdgeStore()
    res = process_article(art(t, "p5", "https://e.com/p5"), REL, make_resolver(), store, FakeNER(spec), v, Counters())
    return store, res


def triples(res):
    return sorted((c.predicate, c.subject.text, c.object.text) for c in res.candidates)


def test_one_person_two_orgs_in_a_list_and_two_roles():
    t = "Bà Nguyễn Thùy Nga là cổ đông lớn, đồng thời là Tổng giám đốc kiêm Chủ tịch HĐQT của cả Công ty cổ phần Beston Test và Công ty cổ phần Bellmont Test."
    _, res = run(t, {"Nguyễn Thùy Nga": P, "Công ty cổ phần Beston Test": O, "Công ty cổ phần Bellmont Test": O})
    got = set(triples(res))
    for org in ("Công ty cổ phần Beston Test", "Công ty cổ phần Bellmont Test"):
        assert ("CHAIR_OF", "Nguyễn Thùy Nga", org) in got and ("CEO_OF", "Nguyễn Thùy Nga", org) in got
    assert len(got) == 4


def test_role_in_parentheses():
    t = "Vụ án liên quan đến bà Trương Mỹ Lan (Chủ tịch Tập đoàn Vạn Thịnh Phát) và đồng phạm."
    _, res = run(t, {"Trương Mỹ Lan": P, "Tập đoàn Vạn Thịnh Phát": O})
    assert triples(res) == [("CHAIR_OF", "Trương Mỹ Lan", "Tập đoàn Vạn Thịnh Phát")]


def test_new_chair_before_org_and_name_after():
    _, res = run("Tân Tổng Giám đốc Toyota Việt Nam, ông Osamu Hirata, bắt đầu nhiệm kỳ.", {"Osamu Hirata": P, "Toyota Việt Nam": O})
    assert triples(res) == [("CEO_OF", "Osamu Hirata", "Toyota Việt Nam")]


def test_role_verb_variants_and_appointing_org_far_from_person():
    _, r1 = run("Ông Tiền Quốc Hào đảm nhiệm vị trí Chủ tịch Công ty Toyota Việt Nam từ tháng 1/2026.", {"Tiền Quốc Hào": P, "Công ty Toyota Việt Nam": O})
    assert ("CHAIR_OF", "Tiền Quốc Hào", "Công ty Toyota Việt Nam") in triples(r1)
    _, r2 = run("Quốc Cường Gia Lai cũng vừa có thay đổi quan trọng khi bổ nhiệm bà Nguyễn Thị Như Loan giữ chức Tổng Giám đốc.",
                {"Quốc Cường Gia Lai": O, "Nguyễn Thị Như Loan": P})
    assert triples(r2) == [("CEO_OF", "Nguyễn Thị Như Loan", "Quốc Cường Gia Lai")]


def test_subsidiary_without_preposition_and_with_sub():
    _, r1 = run("Hoa Lư Bình Phước là công ty con KSB sở hữu gián tiếp 93,24% vốn.", {"Hoa Lư Bình Phước": O, "KSB": O})
    assert ("SUBSIDIARY_OF", "Hoa Lư Bình Phước", "KSB") in triples(r1)
    _, r2 = run("KSB hợp tác kinh doanh với công ty con Hoa Lư Bình Phước.", {"KSB": O, "Hoa Lư Bình Phước": O})
    assert triples(r2) == [("SUBSIDIARY_OF", "Hoa Lư Bình Phước", "KSB")]


def test_acquirer_after_comma():
    _, res = run("Tại Cần Thơ, sau khi hoàn tất nhận chuyển nhượng 100% cổ phần CTCP Điện gió Phú Cường, REE đã khởi công hạng mục.",
                 {"CTCP Điện gió Phú Cường": O, "REE": O})
    assert triples(res) == [("ACQUIRED", "REE", "CTCP Điện gió Phú Cường")]


def test_pronoun_subject_is_coref_candidate_only_with_two_sentence_evidence():
    t = "Ông Tiền Quốc Hào là lãnh đạo cấp cao của Toyota. Song song đó, ông cũng đang đảm nhiệm vai trò Tổng Giám đốc điều hành Công ty Tài chính Toyota Châu Á."
    store, res = run(t, {"Tiền Quốc Hào": P, "Công ty Tài chính Toyota Châu Á": O, "Toyota": O})
    c = [x for x in res.candidates if x.direction_source == "coref"]
    assert len(c) == 1 and c[0].subject.text == "Tiền Quốc Hào" and c[0].predicate == "CEO_OF"
    assert c[0].subject.text in c[0].evidence_text and "Song song đó" in c[0].evidence_text  # antecedent + clause, contiguous
    assert res.article.text[c[0].evidence_start:c[0].evidence_end] == c[0].evidence_text
    assert store.official_edges() == [] and store.outcomes[c[0].candidate_id].outcome == "candidate_edge"
    assert ReasonCode.COREF_REVIEW in store.outcomes[c[0].candidate_id].reasons


def test_pronoun_not_resolved_when_antecedent_ambiguous():
    t = "Ông Lê Văn Một và ông Trần Văn Hai dự họp. Ông cũng đảm nhiệm vai trò Chủ tịch Công ty Cổ phần Sao Mai Test."
    _, res = run(t, {"Lê Văn Một": P, "Trần Văn Hai": P, "Công ty Cổ phần Sao Mai Test": O})
    assert not [c for c in res.candidates if c.direction_source == "coref"]


def test_elided_ownership_object_is_review_only():
    t = ("CTCP Cao su Phước Hòa là cổ đông lớn nhất của Công ty NTC Test sở hữu 7,88 triệu cổ phiếu. "
         "Tiếp đến, Tập đoàn Công nghiệp Cao su nắm giữ 4,9 triệu cổ phiếu, chiếm hơn 20% vốn.")
    store, res = run(t, {"CTCP Cao su Phước Hòa": O, "Công ty NTC Test": O, "Tập đoàn Công nghiệp Cao su": O})
    el = [c for c in res.candidates if c.direction_source == "elided_object"]
    assert len(el) == 1 and (el[0].subject.text, el[0].object.text) == ("Tập đoàn Công nghiệp Cao su", "Công ty NTC Test")
    assert store.outcomes[el[0].candidate_id].outcome == "candidate_edge"
    assert not any(c.direction_source == "elided_object" for c in res.candidates if c.subject.text == "CTCP Cao su Phước Hòa")


def test_split_org_rejoined_and_propagation():
    t = "Ông Đỗ Giang Nam được bổ nhiệm làm Chủ tịch HĐTV Nhà máy In tiền Quốc gia."
    i = t.index("Nhà máy")
    a = Mention(text="Nhà máy", start=i, end=i + 7, label=O, ner_score=0.9)
    j = t.index("tiền Quốc gia")
    b = Mention(text="tiền Quốc gia", start=j, end=j + 13, label=B, ner_score=0.9)
    merged = merge_split_orgs(t, [a, b])
    assert len(merged) == 1 and merged[0].text == "Nhà máy In tiền Quốc gia" and t[merged[0].start:merged[0].end] == merged[0].text
    # not merged across punctuation
    t2 = "Công ty, Beston Test"
    assert len(merge_split_orgs(t2, [Mention(text="Công ty", start=0, end=7, label=O), Mention(text="Beston Test", start=9, end=20, label=O)])) == 2
    t3 = "Công ty Cổ phần Bình Xanh công bố. Sau đó Công ty Cổ phần Bình Xanh tăng vốn."
    first = Mention(text="Công ty Cổ phần Bình Xanh", start=0, end=25, label=O, ner_score=0.9)
    out = propagate_mentions(t3, [first])
    assert len(out) == 2 and out[1].method == "propagated" and out[1].ner_score is None and t3[out[1].start:out[1].end] == first.text


def test_list_expansion_keeps_status_and_dedups():
    _, res = run("Ông Nguyễn Văn Tám nguyên là Chủ tịch HĐQT của Công ty cổ phần Alpha Test và Công ty cổ phần Beta Test.",
                 {"Nguyễn Văn Tám": P, "Công ty cổ phần Alpha Test": O, "Công ty cổ phần Beta Test": O})
    assert len(res.candidates) == 2 and all(c.factual_status == FactualStatus.HISTORICAL for c in res.candidates)


# ---------------------------------------------------------------- ISSUED_BOND / BondIssue
def _bond(t, spec=None, aid="b1"):
    store = EdgeStore()
    resolver = make_resolver()
    res = process_article(art(t, aid, f"https://e.com/{aid}"), REL, resolver, store,
                          FakeNER(spec or {"Công ty cổ phần Sao Mai Test": O}), AcceptAll(), Counters())
    return store, res, resolver


def test_bond_specific_issue_is_grounded_official_and_not_invented():
    t = "Công ty cổ phần Sao Mai Test đã phát hành thành công 1.000 tỷ đồng trái phiếu kỳ hạn 3 năm, lãi suất 9,5%/năm."
    store, res, resolver = _bond(t)
    c = [x for x in res.candidates if x.predicate == "ISSUED_BOND"]
    assert len(c) == 1 and c[0].object.label == EntityType.BOND_ISSUE and c[0].subject.text == "Công ty cổ phần Sao Mai Test"
    assert t[c[0].object.start:c[0].object.end] == c[0].object.text
    row = resolver.store.get_entity(c[0].object.entity_id)
    assert row["resolution_status"] == "ARTICLE_GROUNDED" and row["entity_id"].startswith("bond:")
    assert len(store.official_edges()) == 1
    assert "mã" not in row["canonical_name"].lower() and "ngày" not in row["canonical_name"].lower()  # no invented code/date


def test_bond_without_detail_stays_candidate():
    store, res, resolver = _bond("Công ty cổ phần Sao Mai Test dự kiến phát hành trái phiếu trong thời gian tới.", aid="b2")
    c = [x for x in res.candidates if x.predicate == "ISSUED_BOND"]
    assert c and resolver.store.get_entity(c[0].object.entity_id)["resolution_status"] == "PROVISIONAL"
    assert store.official_edges() == [] and store.edges


def test_bond_same_event_in_two_articles_merges_only_with_code_or_date():
    resolver = make_resolver()
    t = "Công ty cổ phần Sao Mai Test phát hành 500 tỷ đồng trái phiếu mã SMT2128001, kỳ hạn 2 năm."
    ids = set()
    for aid in ("x1", "x2"):
        res = process_article(art(t, aid, f"https://e.com/{aid}"), REL, resolver, EdgeStore(), FakeNER({"Công ty cổ phần Sao Mai Test": O}), AcceptAll(), Counters())
        ids |= {c.object.entity_id for c in res.candidates if c.predicate == "ISSUED_BOND"}
    assert len(ids) == 1  # explicit code printed in both articles: same BondIssue
    t2 = "Công ty cổ phần Sao Mai Test phát hành 500 tỷ đồng trái phiếu kỳ hạn 2 năm."
    ids2 = set()
    for aid in ("y1", "y2"):
        res = process_article(art(t2, aid, f"https://e.com/{aid}"), REL, resolver, EdgeStore(), FakeNER({"Công ty cổ phần Sao Mai Test": O}), AcceptAll(), Counters())
        ids2 |= {c.object.entity_id for c in res.candidates if c.predicate == "ISSUED_BOND"}
    assert len(ids2) == 2  # no code/date: cannot assume the same issuance


def test_role_word_mention_does_not_swallow_the_organization():
    t = "Ngoài Beston, bà Nguyễn Thùy Nga còn là Chủ tịch HĐQT kiêm Tổng giám đốc Công ty cổ phần Unicap Test."
    _, res = run(t, {"Nguyễn Thùy Nga": P, "HĐQT": O, "Công ty cổ phần Unicap Test": O, "Beston": O})
    got = set(triples(res))
    assert ("CHAIR_OF", "Nguyễn Thùy Nga", "Công ty cổ phần Unicap Test") in got and ("CEO_OF", "Nguyễn Thùy Nga", "Công ty cổ phần Unicap Test") in got


def test_acronym_expands_to_initials_of_full_name_in_same_article_only():
    t = "Tổng giám đốc Điện Máy Xanh, ông Đoàn Văn Hiểu Em cho biết kế hoạch. Ông Đoàn Văn Hiểu Em, Tổng giám đốc DMX công bố số liệu."
    spec = {"Điện Máy Xanh": O, "Đoàn Văn Hiểu Em": P, "DMX": O}
    _store, res = run(t, spec)
    dmx = next(m for m in res.mentions if m.text == "DMX")
    full = next(m for m in res.mentions if m.text == "Điện Máy Xanh")
    assert dmx.entity_id == full.entity_id and dmx.linking_method == "article_acronym_expansion"
    # a different article without the full name must not inherit the expansion
    _, r2 = run("Ông Đoàn Văn Hiểu Em, Tổng giám đốc DMX công bố số liệu.", spec)
    d2 = next(m for m in r2.mentions if m.text == "DMX")
    assert d2.entity_id != full.entity_id and d2.link_status == "provisional" and d2.linking_method == "new_provisional"


def test_parenthetical_acronym_defined_elsewhere_in_article_and_inconsistent_llm_note():
    t = ("Ông Đặng Đình Thích là Quyền Tổng giám đốc VAMC. Trước đó, ông là Thành viên HĐTV Công ty TNHH MTV Quản lý tài sản Test (VAMC).")
    _, res = run(t, {"Đặng Đình Thích": P, "VAMC": O, "Công ty TNHH MTV Quản lý tài sản Test": O})
    vs = [m for m in res.mentions if m.text == "VAMC" and m.alias_of is None]
    full = next(m for m in res.mentions if m.text.startswith("Công ty TNHH MTV"))
    assert vs and vs[0].entity_id == full.entity_id and vs[0].linking_method == "article_parenthetical_acronym"

    class Inconsistent:
        model, prompt_version = "t", "t"
        def verify(self, c, definition=""):
            from helpers import verdict_for
            return verdict_for(c, rejection_reason="NO_RELATION")
    store, _res2 = run("Ông Trần Văn Hai là Chủ tịch HĐQT Công ty cổ phần Sao Mai Test.", {"Trần Văn Hai": P, "Công ty cổ phần Sao Mai Test": O}, verifier=Inconsistent())
    ev = next(iter(store.edges.values())).evidence[0]
    assert "llm_inconsistent_rejection_reason=NO_RELATION" in ev.validation_status


def test_truncated_org_span_is_review_only():
    t = "Ông Đinh Hữu Thật đồng thời là Tổng Giám đốc CTCP Sunshine Tây Hồ, công ty con của CTCP Tập đoàn Sunshine."
    store, res = run(t, {"Đinh Hữu Thật": P, "CTCP Sunshine": O})  # NER cut the name before 'Tây Hồ'
    assert res.candidates and store.official_edges() == []
    assert ReasonCode.SPAN_BOUNDARY_SUSPECT in store.outcomes[res.candidates[0].candidate_id].reasons
    store2, _ = run("Ông Đinh Hữu Thật đồng thời là Tổng Giám đốc CTCP Sunshine Tây Hồ, công ty con.", {"Đinh Hữu Thật": P, "CTCP Sunshine Tây Hồ": O})
    assert len(store2.official_edges()) == 1  # full span: fine
