"""Entity registry / resolver tests. All names are hypothetical or generic; no historical claims are asserted."""
import pytest

from vckg.entity_linking.identity import (
    HandwrittenSeedProvider,
    IdentityRecord,
    VietstockSitemapProvider,
    load_provider,
)
from vckg.entity_linking.normalize import normalize_name
from vckg.entity_linking.resolver import EntityResolver
from vckg.entity_linking.store import RegistryStore
from vckg.models import EntityType, Mention, ResolutionStatus
from vckg.preprocessing.text import normalize_text, split_sentences

ORG, BANK, PER = EntityType.ORGANIZATION, EntityType.BANK, EntityType.PERSON


def mk(text, surface, label, nth=0, score=0.9, method="gliner2.5"):
    i = -1
    for _ in range(nth + 1):
        i = text.index(surface, i + 1)
    return Mention(text=surface, start=i, end=i + len(surface), label=label, ner_score=score, method=method)


def resolve(res, aid, text, mentions):
    text = normalize_text(text)
    return res.resolve_article(aid, text, split_sentences(text), mentions)


@pytest.fixture()
def store():
    s = RegistryStore(":memory:")
    s.add_entity("ngan hang tmcp ngoai thuong viet nam", BANK, ticker="VCB", status=ResolutionStatus.VERIFIED,
                 provider="test_provider", source_url="https://example.test/VCB", identity_only=True,
                 source_type="identity_provider")
    return s


@pytest.fixture()
def res(store):
    return EntityResolver(store)


def test_normalization_prefix_accents_variants():
    a = normalize_name("Công ty Cổ phần Sữa Việt Nam")
    assert a == normalize_name("CTCP Sữa Việt Nam") == normalize_name("sua viet nam") == normalize_name("Cty CP Sữa Việt Nam")
    assert normalize_name("Ngân hàng TMCP Ngoại thương Việt Nam") == normalize_name("ngan hang tmcp ngoai thuong viet nam")


def test_add_entity_idempotent_across_prefix_variants():
    s = RegistryStore(":memory:")
    e1, c1 = s.add_entity("Công ty Cổ phần Sữa Việt Nam", ORG)
    e2, c2 = s.add_entity("CTCP Sữa Việt Nam", ORG)
    e3, c3 = s.add_entity("sua viet nam", ORG)
    assert e1 == e2 == e3 and (c1, c2, c3) == (True, False, False)
    assert s.count_entities() == 1


def test_person_requires_explicit_cluster_id():
    with pytest.raises(ValueError):
        RegistryStore(":memory:").add_entity("Nguyễn Văn An", PER)


def test_vcb_ticker_and_alias_resolution(store, res):
    store.add_alias("org:" + "viet-nam".replace("viet-nam", "ngoai-thuong-viet-nam"), "Vietcombank", "alias")
    t = "Cổ phiếu VCB tăng mạnh. Vietcombank công bố kết quả."
    out = resolve(res, "a1", t, [mk(t, "VCB", BANK), mk(t, "Vietcombank", BANK)])
    ids = {m.entity_id for m in out}
    assert ids == {"org:ngoai-thuong-viet-nam"} and all(m.link_status == "resolved" for m in out)  # VERIFIED entity


def test_ticker_without_context_is_unresolved(res):
    t = "VCB là viết tắt xuất hiện trong một bảng biểu."
    m = resolve(res, "a2", t, [mk(t, "VCB", BANK)])[0]
    assert m.entity_id is None and m.linking_method == "ticker_without_context"


def test_ticker_resolves_with_full_name_context(res):
    t = "Ngân hàng TMCP Ngoại thương Việt Nam báo lãi. Nhiều nhà đầu tư chú ý VCB."
    out = resolve(res, "a3", t, [mk(t, "VCB", BANK)])
    assert out[0].entity_id == "org:ngoai-thuong-viet-nam"


def test_ticker_colliding_with_common_abbreviation():
    s = RegistryStore(":memory:")
    s.add_entity("cong ty xyz holdings", ORG, ticker="ABC", status=ResolutionStatus.VERIFIED, provider="p", source_url="u")
    r = EntityResolver(s)
    t1 = "Phương án ABC được trình bày trong báo cáo."
    assert resolve(r, "b1", t1, [mk(t1, "ABC", ORG)])[0].entity_id is None
    t2 = "Cổ phiếu ABC đóng cửa tăng nhẹ."
    assert resolve(r, "b2", t2, [mk(t2, "ABC", ORG)])[0].entity_id == "org:xyz-holdings"


def test_dynamic_registry_growth_and_dedup(res, store):
    before = store.count_entities()
    t1 = "Công ty Cổ phần Bình Minh Xanh công bố kế hoạch mới."
    m1 = resolve(res, "g1", t1, [mk(t1, "Công ty Cổ phần Bình Minh Xanh", ORG)])[0]
    assert m1.link_status == "provisional" and m1.linking_method == "new_provisional"
    t2 = "CTCP Bình Minh Xanh tăng vốn điều lệ."
    m2 = resolve(res, "g2", t2, [mk(t2, "CTCP Bình Minh Xanh", ORG)])[0]
    assert m2.entity_id == m1.entity_id and m2.linking_method in ("exact_canonical", "alias")
    assert store.count_entities() == before + 1
    resolve(res, "g2", t2, [mk(t2, "CTCP Bình Minh Xanh", ORG)])  # rerun: nothing new
    assert store.count_entities() == before + 1
    assert store.db.execute("SELECT COUNT(*) FROM mentions WHERE article_id='g2'").fetchone()[0] == 1


def test_unknown_low_score_not_created(res, store):
    n = store.count_entities()
    t = "Công ty Mờ Nhạt Đông Nam được nhắc đến."
    m = resolve(res, "u1", t, [mk(t, "Công ty Mờ Nhạt Đông Nam", ORG, score=0.2)])[0]
    assert m.entity_id is None and m.linking_method == "low_ner_score" and store.count_entities() == n


def test_out_of_scope_not_created(res, store):
    n = store.count_entities()
    t = "Chỉ số VN-Index giảm điểm."
    m = resolve(res, "o1", t, [mk(t, "VN-Index", ORG)])[0]
    assert m.entity_id is None and m.linking_method.startswith("out_of_scope") and store.count_entities() == n


def test_person_single_token_unresolved(res):
    t = "Bà Phương cho biết kế hoạch."
    m = resolve(res, "p0", t, [mk(t, "Phương", PER)])[0]
    assert m.entity_id is None and m.linking_method == "person_single_token"


def test_same_name_persons_two_companies_not_merged(res, store):
    t1 = "Ông Nguyễn Văn An là Chủ tịch Công ty Cổ phần Sao Mai Alpha."
    t2 = "Ông Nguyễn Văn An là Tổng giám đốc Công ty Cổ phần Biển Xanh Beta."
    o1 = resolve(res, "n1", t1, [mk(t1, "Nguyễn Văn An", PER), mk(t1, "Công ty Cổ phần Sao Mai Alpha", ORG)])
    o2 = resolve(res, "n2", t2, [mk(t2, "Nguyễn Văn An", PER), mk(t2, "Công ty Cổ phần Biển Xanh Beta", ORG)])
    p1 = next(m for m in o1 if m.label == PER).entity_id
    p2 = next(m for m in o2 if m.label == PER).entity_id
    assert p1 != p2 and "@art:" in p1
    assert res.consolidate_persons() == 0  # different org contexts: stay separate
    assert store.canonical_id(p1) != store.canonical_id(p2)


def test_same_person_same_company_merges_with_history_idempotent(res, store):
    t1 = "Ông Trần Quốc Bình là Chủ tịch Công ty Cổ phần Hải Đăng Gamma."
    t2 = "Chủ tịch Công ty Cổ phần Hải Đăng Gamma, ông Trần Quốc Bình, phát biểu."
    resolve(res, "m1", t1, [mk(t1, "Trần Quốc Bình", PER), mk(t1, "Công ty Cổ phần Hải Đăng Gamma", ORG)])
    resolve(res, "m2", t2, [mk(t2, "Trần Quốc Bình", PER), mk(t2, "Công ty Cổ phần Hải Đăng Gamma", ORG)])
    assert res.consolidate_persons() == 1
    assert res.consolidate_persons() == 0  # idempotent
    keep = "person:tran-quoc-binh@art:m1"
    assert store.canonical_id("person:tran-quoc-binh@art:m2") == keep
    hist = store.get_resolution_history(keep)
    assert any(h["op"] == "merge" and "shared org" in h["detail"]["reason"] for h in hist)
    assert store.db.execute("SELECT entity_id FROM mentions WHERE article_id='m2' AND detected_type='PERSON'").fetchone()[0] == keep


def test_reject_merge_blocks_merge(store):
    a, _ = store.add_entity("Công ty Alpha Một", ORG)
    b, _ = store.add_entity("Công ty Alpha Hai", ORG)
    store.reject_merge(a, b, "different legal entities")
    assert store.merge_entities(a, b, "attempt") is False
    assert store.canonical_id(b) == b
    assert any(h["op"] == "reject_merge" for h in store.get_resolution_history(a))


def test_similar_company_names_not_merged_candidates_listed(res, store):
    t1 = "Công ty Cổ phần Phú Mỹ Hưng Group mở bán dự án."
    m1 = resolve(res, "s1", t1, [mk(t1, "Công ty Cổ phần Phú Mỹ Hưng Group", ORG)])[0]
    t2 = "Công ty Phú Mỹ Hưng Grup công bố tin."
    m2 = resolve(res, "s2", t2, [mk(t2, "Công ty Phú Mỹ Hưng Grup", ORG)])[0]
    assert m2.entity_id != m1.entity_id  # near-duplicate name is NOT auto-merged
    assert m1.entity_id in m2.candidate_entity_ids  # but surfaced for review


def test_company_rename_over_time(store):
    e, _ = store.add_entity("Ngân hàng Alpha Cũ", BANK)
    store.add_alias(e, "Ngân hàng Beta Mới", "alias", valid_from="2022-01-01")
    store.add_alias(e, "Ngân hàng Alpha Cũ", "alias", valid_to="2021-12-31")
    c_old = store.find_candidates("Ngân hàng Alpha Cũ", BANK)
    c_new = store.find_candidates("Ngân hàng Beta Mới", BANK)
    assert c_old[0].entity_id == c_new[0].entity_id == e
    row = store.db.execute("SELECT valid_from FROM aliases WHERE alias_text='Ngân hàng Beta Mới'").fetchone()
    assert row[0] == "2022-01-01"


def test_parenthetical_alias_same_entity(res, store):
    t = "Nguyễn Hòa Bình (Shark Bình) là Chủ tịch HĐQT Công ty cổ phần Ngân Lượng Test."
    out = resolve(res, "pa", t, [mk(t, "Nguyễn Hòa Bình", PER), mk(t, "Shark Bình", PER), mk(t, "Công ty cổ phần Ngân Lượng Test", ORG)])
    p = [m for m in out if m.label == PER]
    assert len({m.entity_id for m in p}) == 1 and p[1].linking_method == "parenthetical_alias"
    assert store.find_candidates("Shark Bình", PER)[0].entity_id == p[0].entity_id


def test_parenthetical_ticker_not_invented_as_ticker(res, store):
    t = "Công ty Cổ phần Rạng Đông Delta (RDD) công bố kết quả."
    out = resolve(res, "pt", t, [mk(t, "Công ty Cổ phần Rạng Đông Delta", ORG), mk(t, "RDD", ORG)])
    ent = store.get_entity(out[0].entity_id)
    assert ent["ticker"] is None  # alias recorded, but a ticker is never inferred from capital letters


def test_identity_provider_records_provenance_and_idempotent():
    prov = VietstockSitemapProvider(client=None)
    locs = ["https://finance.vietstock.vn/KVS-ctcp-chung-khoan-kenanga-viet-nam.htm",
            "https://finance.vietstock.vn/CTG-ngan-hang-tmcp-cong-thuong-viet-nam.htm",
            "https://finance.vietstock.vn/5015-nganh-san-xuat-san-pham-sua.htm",
            "https://finance.vietstock.vn/bo-loc-co-phieu.htm"]
    recs = list(prov.parse(locs, "2026-10-30T00:00:00+00:00"))
    assert [r.ticker for r in recs] == ["KVS", "CTG"]
    assert recs[1].entity_type == BANK and all(r.identity_only and r.source_url.startswith("https://") for r in recs)

    class P:
        name = "t"
        def fetch(self): return iter(recs)
    s = RegistryStore(":memory:")
    r1, r2 = load_provider(s, P()), load_provider(s, P())
    assert r1["entities_added"] == 2 and r2["entities_added"] == 0
    assert s.db.execute("SELECT COUNT(*) FROM identity_sources WHERE identity_only=1").fetchone()[0] == 2
    assert isinstance(recs[0], IdentityRecord)


def test_seed_provider_marks_provisional_not_verified(tmp_path):
    import shutil
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "data/registry/seed_registry.json"
    shutil.copy(src, tmp_path / "seed.json")
    s = RegistryStore(":memory:")
    load_provider(s, HandwrittenSeedProvider(tmp_path / "seed.json"))
    assert s.count_entities(status="VERIFIED") == 0 and s.count_entities(status="PROVISIONAL") > 0


def test_provider_suffix_and_prefix_variants_share_key():
    assert normalize_name("tap doan vingroup ctcp") == normalize_name("Tập đoàn Vingroup") == normalize_name("Vingroup") == "vingroup"
    assert normalize_name("tong cong ty khi viet nam ctcp") == normalize_name("Tổng công ty Khí Việt Nam")


def test_same_name_different_verified_tickers_are_not_merged():
    s = RegistryStore(":memory:")
    a, ca = s.add_entity("CTCP Hưng Vượng Test", ORG, ticker="HVT", status=ResolutionStatus.VERIFIED, provider="p", source_url="u1")
    b, cb = s.add_entity("Công ty Cổ phần Hưng Vượng Test", ORG, ticker="HVX", status=ResolutionStatus.VERIFIED, provider="p", source_url="u2")
    assert ca and cb and a != b and s.count_entities() == 2
    again, created = s.add_entity("CTCP Hưng Vượng Test", ORG, ticker="HVT", status=ResolutionStatus.VERIFIED, provider="p", source_url="u1")
    assert again == a and not created  # idempotent
    r = EntityResolver(s)
    t = "Hưng Vượng Test công bố kết quả."
    m = resolve(r, "c1", t, [mk(t, "Hưng Vượng Test", ORG)])[0]
    assert m.entity_id is None and m.link_status == "ambiguous" and set(m.candidate_entity_ids) == {a, b}


def test_single_token_person_resolves_only_to_unique_full_name_in_same_article(res):
    t = "Bà Nguyễn Thùy Nga là Chủ tịch Công ty Cổ phần Sao Mai Alpha. Hiện bà Nga nắm 3% vốn."
    out = resolve(res, "sn1", t, [mk(t, "Nguyễn Thùy Nga", PER), mk(t, "Nga", PER, nth=1), mk(t, "Công ty Cổ phần Sao Mai Alpha", ORG)])
    p = [m for m in out if m.label == PER]
    assert p[0].entity_id == p[1].entity_id and p[1].linking_method == "article_short_name"
    # ambiguous: two different full names ending in the same token -> unresolved
    t2 = "Ông Lê Văn Nam và ông Trần Quốc Nam dự họp. Ông Nam phát biểu."
    out2 = resolve(res, "sn2", t2, [mk(t2, "Lê Văn Nam", PER), mk(t2, "Trần Quốc Nam", PER), mk(t2, "Nam", PER, nth=2)])
    short = [m for m in out2 if m.text == "Nam"][-1]
    assert short.entity_id is None and short.linking_method == "person_single_token"
    # another article never inherits the short-name binding
    t3 = "Bà Nga cho biết kế hoạch."
    assert resolve(res, "sn3", t3, [mk(t3, "Nga", PER)])[0].entity_id is None


def test_role_words_are_not_organizations(res, store):
    n = store.count_entities()
    t = "Ông Nguyễn Văn An là thành viên HĐQT và Hội đồng thành viên."
    out = resolve(res, "rw", t, [mk(t, "HĐQT", ORG), mk(t, "Hội đồng thành viên", ORG)])
    assert all(m.entity_id is None and m.linking_method.startswith("out_of_scope") for m in out) and store.count_entities() == n
