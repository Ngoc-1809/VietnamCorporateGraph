"""Phase 6B.3 regression tests: article-grounded identity (staging registry, in-memory)."""
from vckg.entity_linking.article_grounding import alias_proven, ground_article, overlay_from
from vckg.entity_linking.store import RegistryStore
from vckg.models import EntityType, ResolutionStatus

ORG, PER = EntityType.ORGANIZATION, EntityType.PERSON


def setup(text, spec, aid="a1", seed=None):
    """spec: list of (surface, label, nth, ner_score). Registers PROVISIONAL entities like the Phase 5 resolver would."""
    store = seed or RegistryStore(":memory:")
    ments = []
    for surface, label, nth, score in spec:
        i = -1
        for _ in range(nth + 1):
            i = text.index(surface, i + 1)
        if label == "PERSON":
            eid, _ = store.add_entity(surface, PER, entity_id=f"person:{surface.lower().replace(' ', '-')}@art:{aid}", status=ResolutionStatus.PROVISIONAL)
        else:
            eid, _ = store.add_entity(surface, ORG, status=ResolutionStatus.PROVISIONAL)
        ments.append({"text": surface, "start": i, "end": i + len(surface), "label": label, "entity_id": eid, "alias_of": None, "sentence_index": 0,
                      "linking_method": "new_provisional", "ner_score": score})
    return store, ments


def run(text, spec, aid="a1", seed=None, apply=True):
    store, ments = setup(text, spec, aid, seed)
    dec = ground_article(store, aid, text, ments, apply=apply)
    return store, {d.text: d for d in dec}, ments


def status(store, eid):
    return store.get_entity(eid)["resolution_status"]


def test_full_legal_name_without_registry_entry_is_grounded_with_evidence():
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh Xanh."
    store, d, _ = run(t, [("Nguyễn Văn An", "PERSON", 0, 0.95), ("Công ty cổ phần Bình Minh Xanh", "ORGANIZATION", 0, 0.95)])
    o = d["Công ty cổ phần Bình Minh Xanh"]
    assert o.action == "PROMOTE" and o.method == "FULL_LEGAL_NAME" and status(store, o.resolved_entity_id) == "ARTICLE_GROUNDED"
    assert o.evidence == o.text and o.checks_passed and not o.conflicts and o.original_status == "PROVISIONAL" and o.version
    h = [x for x in store.get_resolution_history(o.resolved_entity_id) if x["op"] == "set_status"]
    assert h and "FULL_LEGAL_NAME" in h[0]["detail"]["reason"] and status(store, d["Nguyễn Văn An"].resolved_entity_id) == "ARTICLE_GROUNDED"


def test_never_promotes_to_verified_and_low_ner_or_truncated_or_generic_stay():
    t = "Công ty cổ phần Bình Minh Xanh công bố. Công ty cổ phần Sao Mai Tây Hồ báo cáo. Công ty cổ phần Việt Nam thông báo."
    store, d, _ = run(t, [("Công ty cổ phần Bình Minh Xanh", "ORGANIZATION", 0, 0.5), ("Công ty cổ phần Sao Mai", "ORGANIZATION", 0, 0.95)])
    assert d["Công ty cổ phần Bình Minh Xanh"].action == "KEEP" and d["Công ty cổ phần Bình Minh Xanh"].reason == "LOW_NER_SCORE"
    assert d["Công ty cổ phần Sao Mai"].reason == "NER_TRUNCATED"  # followed by capitalised 'Tây Hồ'
    assert all(status(store, x.original_entity_id) != "VERIFIED" for x in d.values())
    _store2, d2, _ = run("Công ty cổ phần Việt Nam thông báo kết quả kinh doanh quý ba.", [("Công ty cổ phần Việt Nam", "ORGANIZATION", 0, 0.95)])
    assert d2["Công ty cổ phần Việt Nam"].action == "KEEP"  # generic name


def test_alias_explained_in_article_resolves_only_that_article():
    t = "Ngân hàng TMCP An Bình (ABBank) ký thỏa thuận. Sau đó ABBank công bố kết quả kinh doanh quý ba."
    store, d, _ments = run(t, [("Ngân hàng TMCP An Bình", "ORGANIZATION", 0, 0.95), ("ABBank", "ORGANIZATION", 1, 0.9)])
    a = d["ABBank"]
    assert a.action == "RESOLVE_TO" and a.method == "PARENTHETICAL_DEFINITION" and a.resolved_entity_id == d["Ngân hàng TMCP An Bình"].resolved_entity_id
    assert "(ABBank" in a.evidence and overlay_from(list(d.values())) == {f"a1|{a.start}|{a.end}": a.resolved_entity_id}
    assert store.get_entity("org:abbank")["resolution_status"] == "PROVISIONAL"  # the registry entity itself is NOT merged or changed


def test_parenthetical_that_is_a_country_or_unproven_is_not_an_alias():
    assert alias_proven("ABBank", "Ngân hàng TMCP An Bình", False)
    assert alias_proven("Novaland", "Tập đoàn Đầu tư Địa ốc No Va", True)  # exchange/ticker cue next to it
    assert not alias_proven("Hàn Quốc", "Tập đoàn Young Poong", False) and not alias_proven("Hà Nội", "Công ty cổ phần Hà Nội", False)
    assert not alias_proven("Mr Pips", "Phó Đức Nam", False)


def test_person_full_name_then_short_name_short_stays_ungrounded():
    t = "Ông Lê Văn Hải là Tổng Giám đốc Công ty cổ phần Sao Mai Xanh. Sau đó ông Hải phát biểu. Bình cũng có mặt."
    _store, d, _ = run(t, [("Lê Văn Hải", "PERSON", 0, 0.95), ("Hải", "PERSON", 0, 0.9), ("Bình", "PERSON", 0, 0.9), ("Công ty cổ phần Sao Mai Xanh", "ORGANIZATION", 0, 0.95)])
    assert d["Lê Văn Hải"].action == "PROMOTE"
    for short in ("Hải", "Bình"):
        assert d[short].action == "KEEP" and d[short].reason == "SHORT_PERSON_NAME"  # single token never verified from the name alone


def test_same_name_person_in_two_articles_is_not_merged_and_cross_article_stays_scoped():
    t1 = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Sao Mai Alpha."
    t2 = "Ông Nguyễn Văn An là Tổng Giám đốc Công ty cổ phần Biển Xanh Beta."
    store, d1, _ = run(t1, [("Nguyễn Văn An", "PERSON", 0, 0.95), ("Công ty cổ phần Sao Mai Alpha", "ORGANIZATION", 0, 0.95)], aid="a1")
    store, d2, _ = run(t2, [("Nguyễn Văn An", "PERSON", 0, 0.95), ("Công ty cổ phần Biển Xanh Beta", "ORGANIZATION", 0, 0.95)], aid="a2", seed=store)
    p1, p2 = d1["Nguyễn Văn An"].resolved_entity_id, d2["Nguyễn Văn An"].resolved_entity_id
    assert p1 != p2 and p1.endswith("a1") and p2.endswith("a2")
    assert status(store, p1) == status(store, p2) == "ARTICLE_GROUNDED" and store.canonical_id(p1) != store.canonical_id(p2)  # grounded separately, never merged


def test_person_name_inside_fund_or_without_role_is_not_grounded():
    t = "Manulife đóng góp gần 200 triệu đồng cho quỹ Terry Fox của Công ty cổ phần Sao Mai Xanh."
    _, d, _ = run(t, [("Terry Fox", "PERSON", 0, 0.9), ("Công ty cổ phần Sao Mai Xanh", "ORGANIZATION", 0, 0.95)])
    assert d["Terry Fox"].action == "KEEP" and d["Terry Fox"].reason == "NAME_PART_OF_ORG_OR_FUND"


def test_parent_and_subsidiary_short_names_are_not_confused():
    t = "Công ty cổ phần Đầu tư Lepus Xanh là công ty con của Tập đoàn Masan Group. Công ty cổ phần Hàng tiêu dùng Masan Foods cũng thuộc nhóm. Masan công bố."
    _, d, _ = run(t, [("Công ty cổ phần Đầu tư Lepus Xanh", "ORGANIZATION", 0, 0.95), ("Tập đoàn Masan Group", "ORGANIZATION", 0, 0.95),
                      ("Công ty cổ phần Hàng tiêu dùng Masan Foods", "ORGANIZATION", 0, 0.95), ("Masan", "ORGANIZATION", 2, 0.9)])
    assert d["Masan"].action == "KEEP" and d["Masan"].reason == "AMBIGUOUS_MULTI_MATCH"  # parent group and a sister company both contain it
    assert len(d["Masan"].conflicts) == 2


def test_short_name_resolves_to_unique_full_name_but_not_when_registry_has_other_entities():
    t = "Công ty cổ phần Đầu tư Lepus Xanh công bố kế hoạch. Sau giao dịch, Lepus Xanh sở hữu cổ phần."
    _store, d, _ = run(t, [("Công ty cổ phần Đầu tư Lepus Xanh", "ORGANIZATION", 0, 0.95), ("Lepus Xanh", "ORGANIZATION", 1, 0.9)])
    assert d["Lepus Xanh"].action == "RESOLVE_TO" and d["Lepus Xanh"].method == "SHORT_NAME_OF_UNIQUE_FULL_NAME"
    seed = RegistryStore(":memory:")
    seed.add_entity("Quỹ đầu tư Lepus Xanh Capital", ORG, status=ResolutionStatus.VERIFIED)
    _, d2, _ = run(t, [("Công ty cổ phần Đầu tư Lepus Xanh", "ORGANIZATION", 0, 0.95), ("Lepus Xanh", "ORGANIZATION", 1, 0.9)], seed=seed)
    assert d2["Lepus Xanh"].action == "KEEP" and d2["Lepus Xanh"].reason == "AMBIGUOUS_WITH_REGISTRY"


def test_near_identical_organization_names_are_not_promoted():
    t = "Công ty Cổ phần Phú Mỹ Hưng Group mở bán dự án mới tại thành phố."
    seed = RegistryStore(":memory:")
    seed.add_entity("Công ty Cổ phần Phú Mỹ Hưng Grup", ORG, status=ResolutionStatus.VERIFIED)
    _, d, _ = run(t, [("Công ty Cổ phần Phú Mỹ Hưng Group", "ORGANIZATION", 0, 0.95)], seed=seed)
    assert d["Công ty Cổ phần Phú Mỹ Hưng Group"].action == "KEEP" and d["Công ty Cổ phần Phú Mỹ Hưng Group"].reason == "NEAR_DUPLICATE_NAME"


def test_idempotent_rerun_and_dry_run_changes_nothing():
    t = "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh Xanh (BMX). Sau đó BMX công bố."
    spec = [("Nguyễn Văn An", "PERSON", 0, 0.95), ("Công ty cổ phần Bình Minh Xanh", "ORGANIZATION", 0, 0.95), ("BMX", "ORGANIZATION", 1, 0.9)]
    store, ments = setup(t, spec)
    dry = ground_article(store, "a1", t, ments, apply=False)
    assert all(status(store, d.original_entity_id) == "PROVISIONAL" for d in dry if d.original_entity_id)
    first = ground_article(store, "a1", t, ments, apply=True)
    n_hist = store.db.execute("SELECT COUNT(*) FROM history WHERE op='set_status'").fetchone()[0]
    second = ground_article(store, "a1", t, ments, apply=True)
    assert store.db.execute("SELECT COUNT(*) FROM history WHERE op='set_status'").fetchone()[0] == n_hist  # no new promotions
    assert overlay_from(second) == overlay_from(first) or not second  # already-grounded mentions are simply skipped
    third = ground_article(store, "a1", t, ments, apply=True)
    assert [d.as_dict() for d in third] == [d.as_dict() for d in second]
