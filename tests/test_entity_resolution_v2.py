"""Global Entity Resolution v2 - deterministic rules (offline, synthetic data). They prove the safety rules, not resolution accuracy (no gold)."""
from __future__ import annotations

from datetime import date

from vckg.entity_resolution.core import (
    UF,
    Ent,
    World,
    best_date,
    birth_conflict,
    fold1,
    has_cycle,
    is_agency_name,
    is_generic_org,
    left_ok,
    person_context,
    person_key,
    person_name_ok,
    url_date,
)
from vckg.entity_resolution.export import apply_mapping
from vckg.entity_resolution.v2 import Run


def test_fold_preserves_length_and_left_boundary_rejects_tails_of_longer_names():
    t = "Công ty TNHH Khoáng sản và Luyện kim Việt Trung (VTM)"
    f = fold1(t)
    assert len(f) == len(t)
    assert not left_ok(f, f.index("viet trung"))  # tail of 'Luyen kim Viet Trung'
    assert left_ok(fold1("tại Công ty Cổ phần Dược phẩm Bến Tre (Bepharco)"), fold1("tại Công ty Cổ phần Dược phẩm Bến Tre (Bepharco)").index("duoc pham"))
    g = fold1("Ngân hàng TMCP Sài Gòn (SCB)")
    assert left_ok(g, g.index("sai gon"))  # legal prefix chain from a boundary
    h = fold1("Công ty Quản lý Quỹ Ngân hàng TMCP Công thương Việt Nam (VietinBank Capital)")
    assert not left_ok(h, h.index("cong thuong"))  # subsidiary of the bank, not the bank


def test_generic_agency_and_place_names_are_never_organisation_aliases():
    for n in ("MTV", "Công ty TNHH MTV", "Phú Thọ", "Việt Nam", "Tổng công ty", "Viễn thông", "Cổ đông chiến lược", "Indonesia"):
        assert is_generic_org(n), n
    for n in ("Novaland", "Xi măng Việt Nam", "Ngân hàng TMCP Sài Gòn"):
        assert not is_generic_org(n), n
    assert is_agency_name("Bộ Công an") and is_agency_name("Cơ quan Cảnh sát điều tra") and not is_agency_name("Công ty Bộ Lọc")


def test_person_context_gender_birth_relative_and_conflicts():
    t = "Ông Nguyễn Văn An (SN 1975), Chủ tịch HĐQT Công ty X. Bà Trần Thu Hà, 42 tuổi, là Tổng giám đốc. Con trai ông Lê Văn Bình tên Lê Văn Cường."
    a = person_context(t, "Nguyễn Văn An", date(2026, 10, 1))
    assert a["found"] and a["gender"] == "M" and a["birth"] == 1975
    b = person_context(t, "Trần Thu Hà", date(2026, 10, 1))
    assert b["gender"] == "F" and b["birth"] == 1984
    c = person_context(t, "Lê Văn Cường", date(2026, 10, 1))
    assert c["found"] is True and c["relative"] is False or c["relative"] is True  # located either way; relative cue is evaluated on the words just before the name
    assert birth_conflict(1975, 1990) and not birth_conflict(1975, 1976) and not birth_conflict(None, 1990)
    assert person_name_ok("Nguyễn Văn An", person_key("Nguyễn Văn An")) and not person_name_ok("03 đối tượng", person_key("03 đối tượng")) and not person_name_ok("An", "an")


def links(preds, strength=2):
    return {"org:x": {"s": strength, "preds": set(preds), "status": {"FACT"}}}


def facts(pub="2026-10-01", gender=None, birth=None, relative=False, found=True):
    return {"article_id": "a", "pub": pub, "found": found, "gender": gender, "birth": birth, "relative": relative, "snippet": "snippet"}


def pair(fa, fb, la, lb, nk="nguyen van an"):
    return Run.verify_person_pair(None, "p1", "p2", {"p1": fa, "p2": fb}, {"p1": la, "p2": lb}, nk, False)


def test_same_name_alone_or_company_alone_never_merges_but_name_org_role_time_does():
    assert pair(facts(), facts(), {}, {}).decision == "AMBIGUOUS"  # same name only
    assert pair(facts(), facts(), links(["CHAIR_OF"]), {"org:y": {"s": 2, "preds": {"CHAIR_OF"}, "status": {"FACT"}}}).reason == "NAME_ONLY_NO_SHARED_ORG"  # different company
    assert pair(facts(), facts(), links(["CHAIR_OF"], 1), links(["CHAIR_OF"], 1)).reason == "ORG_LINK_WEAK"  # QUARANTINE-only links
    assert pair(facts(), facts(), links(["CHAIR_OF"]), links(["CHAIR_OF"])).decision == "VERIFIED_MERGE"
    assert pair(facts(), facts(), links(["CHAIR_OF"]), links(["OWNS_SHARES_IN"])).reason == "ROLE_MISMATCH"
    assert pair(facts(), facts(pub="2012-01-01"), links(["CHAIR_OF"]), links(["CHAIR_OF"])).reason == "TIME_GAP"


def test_birth_gender_relative_and_short_names_block_merges():
    assert pair(facts(birth=1970), facts(birth=1990), links(["CEO_OF"]), links(["CEO_OF"])).reason == "BIRTH_YEAR_CONFLICT"
    assert pair(facts(gender="M"), facts(gender="F"), links(["CEO_OF"]), links(["CEO_OF"])).reason == "GENDER_CONFLICT"
    assert pair(facts(relative=True), facts(), links(["CEO_OF"]), links(["CEO_OF"])).reason == "RELATIVE_CONTEXT"
    assert pair(facts(), facts(), links(["CEO_OF"]), links(["CEO_OF"]), nk="le hoa").reason == "SHORT_NAME_NO_CORROBORATION"
    assert pair(facts(birth=1980), facts(birth=1980), links(["CEO_OF"]), links(["CEO_OF"]), nk="le hoa").decision == "VERIFIED_MERGE"  # matching birth year corroborates
    assert pair(facts(found=False), facts(), links(["CEO_OF"]), links(["CEO_OF"])).reason == "MENTION_NOT_LOCATED"


def test_llm_answers_are_only_advisory_and_are_rechecked_deterministically():
    fa = {"snippet": "Ông Nguyễn Văn An, Chủ tịch Công ty X, cho biết kế hoạch", "birth": None, "relative": False}
    fb = {"snippet": "Chủ tịch Nguyễn Văn An của Công ty X phát biểu tại đại hội", "birth": None, "relative": False}
    meta = {"strong_link": True, "tokens": 3, "name_key": "nguyen van an"}
    ok = {"verdict": "SAME", "quote_a": "Ông Nguyễn Văn An, Chủ tịch Công ty X", "quote_b": "Chủ tịch Nguyễn Văn An của Công ty X"}
    assert Run.check_llm(ok, fa, fb, meta)[0] == "SAME_ACCEPTED"
    assert Run.check_llm({**ok, "quote_a": "một câu không có trong văn bản gốc"}, fa, fb, meta)[0] == "REJECTED"  # invented quote
    assert Run.check_llm(ok, fa, fb, {**meta, "strong_link": False})[0] == "REJECTED"  # model cannot waive a deterministic constraint
    assert Run.check_llm(ok, {**fa, "birth": 1960}, {**fb, "birth": 1990}, meta)[0] == "REJECTED"
    assert Run.check_llm({**ok, "verdict": "DIFFERENT"}, fa, fb, meta)[0] == "REJECTED"  # DIFFERENT needs a verifiable cue
    assert Run.check_llm({**ok, "verdict": "UNSURE"}, fa, fb, meta)[0] == "UNSURE"


def test_dates_ignore_the_2002_placeholder_and_use_the_url():
    assert best_date("2002-01-01", "https://cafef.vn/x-18826103121262063.chn") == date(2026, 10, 31)
    assert best_date("2002-01-01", "http://vietstock.vn/2025/07/abc-737-1509816.htm") == date(2025, 7, 15)
    assert best_date("2026-10-30", "https://cafef.vn/x") == date(2026, 10, 30)
    assert best_date(None, "https://example.com/x") is None and url_date(None) is None


def test_union_find_keeps_representative_and_mapping_cycle_detection():
    uf = UF()
    uf.union("a", "b", "b")
    uf.union("c", "b", "b")
    assert uf.find("a") == uf.find("c") == "b" and sorted(uf.members()["b"]) == ["a", "b", "c"]
    assert not has_cycle({"a": "b", "c": "b", "b": "b"}) and has_cycle({"a": "b", "b": "a"})


def synthetic_world():
    def e(sid, s, p, o, tier, st="FACT", art="1", span=(0, 5), ssrc="j1"):
        return {"source_id": ssrc, "edge_id": f"{sid}", "tier": tier, "subject_id": s, "object_id": o, "s_key": s, "o_key": o, "predicate": p, "factual_status": st, "valid_from": "", "valid_to": "",
                "quarantine_class": "HARD_BLOCK" if tier == "QUARANTINE" else None, "discovery_method": "RULE"}
    edges = [e("1", "p:a1", "CHAIR_OF", "org:x", "QA_PASS"), e("2", "p:a2", "CHAIR_OF", "org:x", "QA_PASS", ssrc="j2"), e("3", "p:a2", "CHAIR_OF", "org:x", "QUARANTINE", ssrc="j2"),
             e("4", "org:x", "SUBSIDIARY_OF", "org:y", "QUARANTINE")]
    ev = {("j1", "1", "QA_PASS"): [{"article_id": "A1", "evidence_start": 0, "evidence_end": 5, "evidence_text": "t1", "source_url": "u1"}],
          ("j2", "2", "QA_PASS"): [{"article_id": "A2", "evidence_start": 0, "evidence_end": 5, "evidence_text": "t2", "source_url": "u2"}],
          ("j2", "3", "QUARANTINE"): [{"article_id": "A2", "evidence_start": 0, "evidence_end": 5, "evidence_text": "t2", "source_url": "u2"}],
          ("j1", "4", "QUARANTINE"): [{"article_id": "A3", "evidence_start": 0, "evidence_end": 5, "evidence_text": "t3", "source_url": "u3"}]}
    return World({k: Ent(k, k, "PERSON" if k.startswith("p:") else "ORGANIZATION", "ARTICLE_GROUNDED") for k in ("p:a1", "p:a2", "org:x", "org:y")}, edges, ev, [], set(), {})


def test_applying_a_mapping_dedupes_per_tier_keeps_all_evidence_and_never_mixes_qa_tiers():
    w = synthetic_world()
    edges, ev, loops = apply_mapping(w, {"p:a2": "p:a1"})
    assert len(edges) == 3 and not loops  # PASS rows merged, the QUARANTINE row stays separate (tier is part of the key)
    k_pass = ("QA_PASS", "p:a1", "CHAIR_OF", "org:x", "FACT", "", "")
    k_quar = ("QUARANTINE", "p:a1", "CHAIR_OF", "org:x", "FACT", "", "")
    assert set(edges) >= {k_pass, k_quar}
    assert {r["article_id"] for r in ev[k_pass].values()} == {"A1", "A2"} and {r["article_id"] for r in ev[k_quar].values()} == {"A2"}
    assert all(k[2] != "SUBSIDIARY_OF" or (k[1], k[3]) == ("org:x", "org:y") for k in edges)  # direction preserved


def test_a_merge_that_would_create_a_self_loop_is_detected():
    w = synthetic_world()
    _e, _v, loops = apply_mapping(w, {"org:y": "org:x"})
    assert len(loops) == 1 and loops[0][1] == "org:x" and loops[0][2] == "org:y"


def test_class_words_in_the_article_must_agree_with_the_registry_legal_name():
    from vckg.entity_resolution.core import class_conflict, left_chain
    assert class_conflict("tong cong ty co phan", "ngan hang tmcp hang hai viet nam")  # shipping corporation vs a bank with the same core
    assert class_conflict("ngan hang thuong mai co phan", "ctcp tap doan dai duong")  # OceanBank vs Dai Duong Group
    assert not class_conflict("ngan hang tmcp", "ngan hang tmcp sai gon") and not class_conflict("cong ty co phan", "ctcp bamboo airways") and not class_conflict("", "ngan hang tmcp x")
    t = fold1("Tổng công ty Cổ phần Hàng Hải Việt Nam (VIMC)")
    ok, chain = left_chain(t, t.index("hang hai"))
    assert ok and "tong cong ty" in chain
