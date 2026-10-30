"""ARTICLE_GROUNDED identity tests (Phase 5). Sentences are modelled on structures seen in real articles."""
from helpers import FakeNER, art, make_resolver
from vckg.entity_linking.grounding import org_grounded, person_grounded
from vckg.models import EntityType, Mention
from vckg.pipeline import Counters, process_article
from vckg.relation_extraction.candidates import load_relations
from vckg.validation.evidence import EdgeStore

P, O, REG = EntityType.PERSON, EntityType.ORGANIZATION, EntityType.REGULATOR
REL = load_relations(str(__import__("helpers").ROOT / "config" / "relations.yaml"))


def run(t, spec, resolver=None, aid="g1", verifier="accept"):
    from helpers import AcceptAll
    resolver = resolver or make_resolver()
    store = EdgeStore()
    res = process_article(art(t, aid, f"https://e.com/{aid}"), REL, resolver, store, FakeNER(spec), AcceptAll(), Counters())
    return store, res, resolver


def M(text, label=O, score=0.9):
    return Mention(text=text, start=0, end=len(text), label=label, ner_score=score)


def test_viettel_ngan_luong_china_railway_become_official():
    cases = [
        ("Trung tướng Tào Đức Thắng, Chủ tịch kiêm Tổng giám đốc Tập đoàn Viettel, cho biết kế hoạch.", {"Tào Đức Thắng": P, "Tập đoàn Viettel": O}, {"CHAIR_OF", "CEO_OF"}),
        ("Nguyễn Hòa Bình (Shark Bình) - Chủ tịch HĐQT Công ty cổ phần Ngân Lượng - tiếp tục gây chú ý.",
         {"Nguyễn Hòa Bình": P, "Shark Bình": P, "Công ty cổ phần Ngân Lượng": O}, {"CHAIR_OF"}),
        ("Ông Zhang Qiang, Tổng Giám đốc Công ty TNHH China Railway Sixth Group Việt Nam, phát biểu.",
         {"Zhang Qiang": P, "Công ty TNHH China Railway Sixth Group Việt Nam": O}, {"CEO_OF"}),
    ]
    for i, (t, spec, preds) in enumerate(cases):
        store, _res, _ = run(t, spec, aid=f"c{i}")
        assert {e.predicate for e in store.official_edges()} == preds, t
        assert all(e.evidence[0].source_url for e in store.official_edges())


def test_identity_and_relation_confidence_are_independent():
    # well-grounded endpoints but the relation is planned -> identity fine, relation not official
    store, _, _ = run("Ông Trần Văn Hai dự kiến sẽ là Chủ tịch HĐQT Công ty cổ phần Sao Mai Test.", {"Trần Văn Hai": P, "Công ty cổ phần Sao Mai Test": O})
    assert store.edges and store.official_edges() == []
    # negated relation never an edge even with grounded endpoints
    store, _, _ = run("Ông Trần Văn Hai không phải là Chủ tịch HĐQT Công ty cổ phần Sao Mai Test.", {"Trần Văn Hai": P, "Công ty cổ phần Sao Mai Test": O}, aid="g2")
    assert not store.edges


def test_same_name_people_in_two_articles_not_merged_even_when_grounded():
    resolver = make_resolver()
    _, r1, _ = run("Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Sao Mai Alpha.", {"Nguyễn Văn An": P, "Công ty cổ phần Sao Mai Alpha": O}, resolver, "n1")
    _, r2, _ = run("Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Biển Xanh Beta.", {"Nguyễn Văn An": P, "Công ty cổ phần Biển Xanh Beta": O}, resolver, "n2")
    p1 = next(m for m in r1.mentions if m.label == P).entity_id
    p2 = next(m for m in r2.mentions if m.label == P).entity_id
    assert p1 != p2 and resolver.consolidate_persons() == 0


def test_person_without_org_context_or_single_name_not_grounded():
    assert not person_grounded(M("Nguyễn Văn An", P), has_org_context=False)
    assert not person_grounded(M("Nga", P), has_org_context=True)
    assert person_grounded(M("ông Nguyễn Văn An", P), has_org_context=True)


def test_org_grounding_rules():
    assert org_grounded(M("Công ty cổ phần Ngân Lượng"))
    assert org_grounded(M("Tập đoàn Viettel"))
    assert org_grounded(M("Điện Máy Xanh"))
    assert org_grounded(M("Bluemarq Group"))
    assert not org_grounded(M("VBOX"))                    # bare acronym
    assert not org_grounded(M("Sao Mai"))                 # two common words, no legal form
    assert not org_grounded(M("Công ty"))                 # generic
    assert not org_grounded(M("Công ty chứng khoán"))     # lowercase generic noun phrase
    assert not org_grounded(M("Công ty cổ phần Ngân Lượng", score=0.4))  # weak NER span
    assert org_grounded(M("Cục Thuế Hải Phòng", EntityType.GOVERNMENT_AGENCY))
    assert not org_grounded(M("cơ quan quản lý", EntityType.GOVERNMENT_AGENCY))


def test_identity_conflict_blocks_grounding_and_upgrade_is_logged():
    resolver = make_resolver()
    t1 = "Công ty Cổ phần Phú Mỹ Hưng Group mở bán dự án."
    run("Ông Lê Văn Một là Chủ tịch HĐQT Công ty Cổ phần Phú Mỹ Hưng Group.", {"Lê Văn Một": P, "Công ty Cổ phần Phú Mỹ Hưng Group": O}, resolver, "a")
    # near-duplicate spelling: similar-but-distinct entity gets listed as candidate -> must stay PROVISIONAL
    _, res, _ = run("Ông Lê Văn Hai là Chủ tịch HĐQT Công ty Phú Mỹ Hưng Grup.", {"Lê Văn Hai": P, "Công ty Phú Mỹ Hưng Grup": O}, resolver, "b")
    org = next(m for m in res.mentions if m.label == O)
    assert org.candidate_entity_ids and resolver.store.get_entity(org.entity_id)["resolution_status"] == "PROVISIONAL"
    first = resolver.store.get_entity("org:phu-my-hung-group")
    assert first["resolution_status"] == "ARTICLE_GROUNDED"
    assert any(h["op"] == "set_status" and h["detail"]["new"] == "ARTICLE_GROUNDED" for h in resolver.store.get_resolution_history("org:phu-my-hung-group"))
    assert t1


def test_status_never_downgrades():
    resolver = make_resolver()
    st = resolver.store
    eid, _ = st.add_entity("Công ty Cổ phần Alpha Test", O)
    from vckg.models import ResolutionStatus as R
    assert st.set_status(eid, R.ARTICLE_GROUNDED, "t") and not st.set_status(eid, R.PROVISIONAL, "t")
    assert st.set_status(eid, R.VERIFIED, "t") and not st.set_status(eid, R.ARTICLE_GROUNDED, "t")
