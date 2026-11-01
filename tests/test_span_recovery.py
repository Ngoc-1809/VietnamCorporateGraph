"""Phase 6B.4 regression tests: safe NER span recovery (one test group per observed failure cause)."""
import unicodedata

from vckg.entity_linking.article_grounding import _truncated, ground_article
from vckg.entity_linking.store import RegistryStore
from vckg.models import RelationCandidate
from vckg.ner.span_recovery import recover_article
from vckg.validation import hybrid_qa
from vckg.validation.span_qa import corrected_mentions


def M(text, surface, label="ORGANIZATION", nth=0, method="gliner2.5", eid=None, score=0.9):
    i = -1
    for _ in range(nth + 1):
        i = text.index(surface, i + 1)
    return {"text": surface, "start": i, "end": i + len(surface), "label": label, "method": method, "entity_id": eid, "alias_of": None, "ner_score": score,
            "linking_method": "x", "sentence_index": 0}


def rec(text, ments):
    return recover_article("a1", text, ments, _truncated)


def one(fixes, original):
    return next(f for f in fixes if f.original_text == original)


def test_false_alarm_org_followed_by_person_is_confirmed_complete_not_extended():
    t = "Nhấn mạnh điều này, Chủ tịch HĐQT ABBank Vũ Văn Tiền khẳng định tại buổi lễ."
    f = one(rec(t, [M(t, "ABBank", "BANK"), M(t, "Vũ Văn Tiền", "PERSON")]), "ABBank")
    assert f.kind == "CONFIRMED_COMPLETE" and f.cause == "FALSE_ALARM" and f.new is None
    t2 = "Từ khi lên nắm quyền, Chủ tịch Fed Kevin Warsh đã chọn cách hạn chế phát ngôn."
    assert one(rec(t2, [M(t2, "Fed"), M(t2, "Kevin Warsh", "PERSON")]), "Fed").kind == "CONFIRMED_COMPLETE"


def test_gliner_truncated_legal_name_extended_with_exact_offsets_and_evidence():
    t = "Anh Mai Minh Vương - Chủ tịch HĐQT Công cổ phần Nhất Phong Vận được bầu giữ chức Chủ tịch Hội."
    f = one(rec(t, [M(t, "Công cổ phần Nhất"), M(t, "Mai Minh Vương", "PERSON")]), "Công cổ phần Nhất")
    assert f.kind == "EXTEND" and f.cause == "GLINER_TRUNCATED" and f.new_text == "Công cổ phần Nhất Phong Vận" and f.evidence == "LEGAL_FORM_RUN"
    assert t[f.new[0]:f.new[1]] == f.new_text and f.checks and f.version


def test_dictionary_partial_generic_alias_recovered_to_full_legal_name():
    t = "CTCP Đầu tư Lepus là công ty con do Masan Group sở hữu 98% vốn."
    f = one(rec(t, [M(t, "CTCP Đầu tư", "BANK", method="dictionary", score=None)]), "CTCP Đầu tư")
    assert f.kind == "EXTEND" and f.cause == "DICTIONARY_PARTIAL" and f.new_text == "CTCP Đầu tư Lepus"


def test_lowercase_sector_words_stay_inside_the_name_and_generic_dictionary_hits_are_absorbed():
    t = "Khi mới thành lập, Xây dựng Hạ tầng Crystal là công ty con. Sau đó Xây dựng Hạ tầng Crystal tăng vốn."
    f = rec(t, [M(t, "Xây dựng", method="dictionary", score=None)])[0]
    assert f.kind == "EXTEND" and f.new_text == "Xây dựng Hạ tầng Crystal" and f.evidence == "REPEATED_FULL_NAME"  # not "Xây dựng Hạ"
    t2 = "Gồm Công ty TNHH Thương mại và Xây dựng Việt Nam Korea góp 55% vốn điều lệ."
    xd, vn = M(t2, "Xây dựng", method="dictionary", score=None), M(t2, "Việt Nam", method="dictionary", score=None)
    g = one(rec(t2, [xd, vn]), "Xây dựng")
    assert g.kind == "EXTEND" and g.new_text == "Công ty TNHH Thương mại và Xây dựng Việt Nam Korea" and (vn["start"], vn["end"]) in g.absorbed


def test_generic_names_never_become_legal_entities():
    t = "Việt Nam và Lào ký thỏa thuận hợp tác về đầu tư."
    assert all(f.kind != "EXTEND" for f in rec(t, [M(t, "Việt Nam", method="dictionary", score=None)]))
    t2 = "Đông Anh là huyện của Hà Nội với nhiều khu công nghiệp lớn."
    assert all(f.kind != "EXTEND" for f in rec(t2, [M(t2, "Đông Anh", method="dictionary", score=None)]))
    t3 = "Khi mới đây Việt Nam tăng trưởng mạnh và ổn định trong năm nay theo báo cáo."
    assert rec(t3, [M(t3, "Việt Nam", method="dictionary", score=None)]) == []


def test_connector_never_joins_two_entities_across_a_legal_form_word():
    t = "Cuộc họp giữa Công ty và UBND tỉnh Khánh Hòa là cuộc họp đầu tiên. Sau đó UBND tỉnh Khánh Hòa là bên ký kết."
    fixes = rec(t, [M(t, "UBND tỉnh", method="dictionary", score=None)])
    new = [f.new_text for f in fixes if f.kind == "EXTEND"]
    assert "Công ty và UBND tỉnh Khánh Hòa" not in new and new == ["UBND tỉnh Khánh Hòa"]


def test_unknown_boundary_or_unproven_name_keeps_original_span():
    t = "Công ty TNHH Đầu tư Xây dựng Giải trí Phương Nam là đơn vị mới thành lập."
    f = rec(t, [M(t, "Công ty TNHH Đầu tư Xây dựng Giải")])
    assert all(x.kind != "EXTEND" or x.new_text.endswith("Phương Nam") for x in f)  # never the cut-off 'Giải'
    t2 = "Sunshine công bố kế hoạch. Quỹ Alpha Beta cũng tham dự buổi họp."
    assert not any(x.kind == "EXTEND" for x in rec(t2, [M(t2, "Alpha", method="dictionary", score=None)]))  # no legal form, not repeated


def test_person_names_untouched_and_person_mentions_block_type_conflicts():
    t = "Ông Bình phát biểu tại hội nghị. Bình cũng có mặt cùng ông Nguyễn Văn An."
    assert rec(t, [M(t, "Bình", "PERSON"), M(t, "Nguyễn Văn An", "PERSON")]) == []
    t2 = "Shark Bình phát biểu. Trước đó Shark cũng nhắc tới Shark Bình trong buổi họp."
    f = rec(t2, [M(t2, "Shark", method="dictionary", score=None, nth=1), M(t2, "Shark Bình", "PERSON")])
    assert not any(x.kind == "EXTEND" for x in f)


def test_never_crosses_sentence_or_line_and_offsets_are_nfc_exact():
    t = "Ông A giữ chức tại CTCP Đầu tư\nLepus là công ty con của một tập đoàn lớn."
    assert not any(x.kind == "EXTEND" and "\n" in x.new_text for x in rec(t, [M(t, "CTCP Đầu tư", method="dictionary", score=None)]))
    nfd = unicodedata.normalize("NFD", "CTCP Đầu tư Lepus là công ty con.")
    assert rec(nfd, [M(nfd, unicodedata.normalize("NFD", "CTCP Đầu tư"), method="dictionary", score=None)]) == []  # unnormalised text is refused, never guessed


def test_corrected_mentions_reuse_existing_entity_and_register_new_provisional_once():
    t = "CTCP Đầu tư Lepus công bố. Sau đó CTCP Đầu tư Lepus sở hữu cổ phần; CTCP Đầu tư Lepus tăng vốn."
    store = RegistryStore(":memory:")
    full, _ = store.add_entity("CTCP Đầu tư Lepus", __import__("vckg.models", fromlist=["EntityType"]).EntityType.ORGANIZATION)
    ments = [M(t, "CTCP Đầu tư Lepus", eid=full), M(t, "CTCP Đầu tư", method="dictionary", score=None, nth=2, eid="org:dau-tu")]
    ments[1]["start"], ments[1]["end"] = t.rindex("CTCP Đầu tư"), t.rindex("CTCP Đầu tư") + len("CTCP Đầu tư")
    fixes = rec(t, ments)
    out, _mp = corrected_mentions(t, ments, fixes, store, "a1")
    assert len(out) == 2 and out[1]["text"] == "CTCP Đầu tư Lepus" and out[1]["entity_id"] == full  # reused, no duplicate entity
    out2, _ = corrected_mentions(t, ments, fixes, store, "a1")
    assert out2 == out and store.count_entities() == 1  # idempotent


def test_confirmed_complete_span_can_be_grounded_but_truncated_one_cannot():
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh Xanh Nguyễn Văn Tám."
    store = RegistryStore(":memory:")
    eid, _ = store.add_entity("Công ty cổ phần Bình Minh Xanh", __import__("vckg.models", fromlist=["EntityType"]).EntityType.ORGANIZATION)
    m = M(t, "Công ty cổ phần Bình Minh Xanh", eid=eid)
    m2 = {**M(t, "Nguyễn Văn Tám", "PERSON"), "entity_id": None}
    d0 = ground_article(store, "a1", t, [m], apply=False)[0]
    assert d0.reason == "NER_TRUNCATED"  # heuristic fires: capitalised words follow
    d1 = ground_article(store, "a1", t, [m], apply=False, confirmed_complete={(m["start"], m["end"])})[0]
    assert d1.reason != "NER_TRUNCATED" and m2["text"]


def test_overlay_dict_rewrites_span_only_inside_evidence_and_keeps_other_side():
    t = "Anh Mai Minh Vương - Chủ tịch HĐQT Công cổ phần Nhất Phong Vận được bầu."
    s, o = M(t, "Mai Minh Vương", "PERSON", eid="p:1"), M(t, "Công cổ phần Nhất", eid="o:1")
    from vckg.models import FactualStatus, Mention
    mk = lambda d: Mention(text=d["text"], start=d["start"], end=d["end"], label=d["label"], entity_id=d["entity_id"], article_id="a1", link_status="provisional")
    c = RelationCandidate(candidate_id="c", article_id="a1", subject=mk(s), object=mk(o), predicate="CHAIR_OF", sentence_index=0, evidence_text=t, evidence_start=0,
                          evidence_end=len(t), factual_status=FactualStatus.FACT)
    f = rec(t, [s, o])[0]
    ov = {f"a1|{o['start']}|{o['end']}": {"start": f.new[0], "end": f.new[1], "text": f.new_text, "label": "ORGANIZATION", "entity_id": "o:full"}}
    c2 = hybrid_qa.apply_overlay(c, ov)
    assert c2.object.text == "Công cổ phần Nhất Phong Vận" and c2.object.entity_id == "o:full" and c2.subject == c.subject
    assert t[c2.object.start:c2.object.end] == c2.object.text and c.object.text == "Công cổ phần Nhất"  # original object untouched
    narrow = c.model_copy(update={"evidence_end": o["end"] + 3})  # new span would leave the evidence slice -> no change
    assert hybrid_qa.apply_overlay(narrow, ov).object.text == "Công cổ phần Nhất"


def test_recovery_is_idempotent_and_deterministic():
    t = "CTCP Đầu tư Lepus là công ty con do Masan Group sở hữu 98% vốn."
    ms = [M(t, "CTCP Đầu tư", "BANK", method="dictionary", score=None)]
    a = [f.as_dict() for f in rec(t, ms)]
    assert a == [f.as_dict() for f in rec(t, ms)]
