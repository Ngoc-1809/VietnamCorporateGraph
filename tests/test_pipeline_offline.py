"""Offline unit tests. Sentences are synthetic (hypothetical), not real articles. Test doubles for NER/LLM are
used only to exercise pipeline logic; they say nothing about GLiNER/Qwen quality."""
import unicodedata

import pytest

from helpers import AcceptAll, FakeNER, art, make_resolver, verdict_for
from vckg.entity_linking.linker import EntityLinker
from vckg.entity_linking.normalize import normalize_name
from vckg.entity_linking.registry import Registry, RegistryRecord
from vckg.graph.projection import company_company_projection, person_person_projection
from vckg.models import (
    Edge,
    EntityType,
    EvidenceRecord,
    FactualStatus,
    Mention,
    RelationCandidate,
    ReviewStatus,
    Verdict,
)
from vckg.pipeline import Counters, process_article
from vckg.preprocessing.text import normalize_text, split_sentences
from vckg.reasons import ReasonCode
from vckg.relation_extraction.candidates import generate_candidates
from vckg.relation_extraction.modality import detect_factuality
from vckg.storage.jsonl import read_jsonl, write_jsonl
from vckg.storage.sqlite import Staging, canonicalize_url
from vckg.validation.evidence import EdgeStore

P, O, B = EntityType.PERSON, EntityType.ORGANIZATION, EntityType.BANK
VIN = {"Phạm Nhật Vượng": P, "Vingroup": O, "Vinhomes": O, "VinFast": O, "Hòa Phát": O, "VPBank": B}


def run(text, spec=VIN, verifier="accept", resolver=None, store=None, aid="a1"):
    resolver = resolver or make_resolver()
    store = store or EdgeStore()
    from vckg.relation_extraction.candidates import load_relations
    rel = load_relations(str(__import__("helpers").ROOT / "config" / "relations.yaml"))
    v = AcceptAll() if verifier == "accept" else verifier
    cn = Counters()
    res = process_article(art(text, aid, f"https://e.com/{aid}"), rel, resolver, store, FakeNER(spec), v, cn)
    return store, res, cn


# ------------------------------------------------------------------ text / linking (Phase 1-3 behavior kept)
def test_unicode_nfc():
    decomposed = unicodedata.normalize("NFD", "Nguyễn Đức Vinh")
    assert decomposed != "Nguyễn Đức Vinh"
    assert normalize_text(decomposed) == "Nguyễn Đức Vinh"
    assert normalize_text("a\u200bb\u00a0\u00a0c") == "ab c"


def test_sentence_offsets_exact():
    text = normalize_text("Ông A là Chủ tịch. TS. Nguyễn Văn B cho biết điều đó. Giá tăng 3,5% hôm nay!")
    sents = split_sentences(text)
    assert len(sents) == 3
    for s in sents:
        assert text[s.start:s.end] == s.text


def test_dictionary_mention_offsets(matcher):
    text = "Ông Phạm Nhật Vượng là Chủ tịch Vingroup, cổ phiếu VIC tăng."
    ms = matcher.find(text)
    assert all(text[m.start:m.end] == m.text for m in ms)
    assert {"Phạm Nhật Vượng", "Vingroup", "VIC"} <= {m.text for m in ms}
    assert all(m.method == "dictionary" and m.ner_score is None for m in ms)  # dictionary has no score


def test_alias_normalization():
    assert normalize_name("Ngân hàng TMCP Kỹ thương Việt Nam") == normalize_name("Kỹ thương Việt Nam")
    assert normalize_name("Ông Trần Đình Long", is_person=True) == "tran dinh long"


def test_alias_variants_via_registry(linker):
    m = linker.link(Mention(text="Tập đoàn Hòa Phát", start=0, end=17, label=O))
    assert m.entity_id == "org:hoaphat"


def test_disambiguation_by_context():
    reg = Registry([
        RegistryRecord(entity_id="org:a", canonical_name="An Phát Holdings", type=O, aliases=["An Phát"], context_hints=["nhựa"]),
        RegistryRecord(entity_id="org:b", canonical_name="An Phát Bank", type=B, aliases=["An Phát"], context_hints=["tín dụng"]),
    ])
    lk = EntityLinker(reg)
    m = Mention(text="An Phát", start=0, end=7, label=O)
    assert lk.link(m, context="").link_status == "ambiguous"
    assert lk.link(m, context="lĩnh vực nhựa").entity_id == "org:a"
    assert lk.link(m, context="tăng trưởng tín dụng").entity_id == "org:b"


def test_no_merge_on_similar_person_names(linker):
    assert linker.link(Mention(text="Trần Đình Longg", start=0, end=15, label=P)).entity_id is None
    assert linker.link(Mention(text="Nguyễn Văn Vinh", start=0, end=15, label=P)).entity_id is None


def test_type_mismatch_not_linked(linker):
    assert linker.link(Mention(text="Vingroup", start=0, end=8, label=P)).entity_id is None


def test_mention_span_validation():
    with pytest.raises(ValueError):
        Mention(text="x", start=5, end=5, label=P)


# ------------------------------------------------------------------ relations through the full pipeline
def test_positive_fact_creates_official_edge():
    store, _res, cn = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.")
    assert ("person:pham-nhat-vuong", "CHAIR_OF", "org:vingroup") in store.edges
    assert store.official_edges() and cn.validator_official == 1


def test_negation_creates_no_edge_and_no_llm_call():
    v = AcceptAll()
    store, res, cn = run("Ông Phạm Nhật Vượng không phải là Chủ tịch HĐQT Vingroup.", verifier=v)
    assert res.candidates[0].factual_status == FactualStatus.DENIED
    assert not store.edges and v.calls == 0 and cn.llm_skipped == 1
    assert ReasonCode.NEGATED_RELATION in store.outcomes[res.candidates[0].candidate_id].reasons


def test_plan_is_not_official():
    store, _, _ = run("Vingroup dự kiến sẽ mua lại VinFast trong quý tới.")
    assert store.edges, "planned relation kept as candidate edge"
    for e in store.edges.values():
        assert all(r.factual_status == FactualStatus.PLANNED and r.review_status == ReviewStatus.NEEDS_REVIEW for r in e.evidence)
    assert store.official_edges() == []


def test_cooccurrence_without_cue_no_candidate():
    store, res, _ = run("Vingroup và Hòa Phát cùng có mặt trong danh sách VN30.")
    assert res.candidates == [] and not store.edges


def test_unresolved_mention_rejected_in_store():
    text = "Ông Lê Văn Zzz là Chủ tịch HĐQT Vingroup."
    p = Mention(text="Lê Văn Zzz", start=4, end=14, label=P)
    o = Mention(text="Vingroup", start=32, end=40, label=O, entity_id="org:vingroup", link_status="resolved")
    c = RelationCandidate(candidate_id="x", subject=p, object=o, predicate="CHAIR_OF", sentence_index=0,
                          evidence_text=text, evidence_start=0, evidence_end=len(text))
    store = EdgeStore()
    assert store.add(art(text), c, verdict_for(c), "t") is None
    assert store.outcomes["x"].reasons[0] == ReasonCode.SUBJECT_UNRESOLVED


def test_edge_dedup_across_articles_after_consolidation():
    resolver, store = make_resolver(), EdgeStore()
    t1 = "Ông Trần Quốc Bình là Chủ tịch HĐQT Vingroup."
    t2 = "Chủ tịch HĐQT Vingroup, ông Trần Quốc Bình, phát biểu tại đại hội."
    spec = {"Trần Quốc Bình": P, "Vingroup": O}
    run(t1, spec, resolver=resolver, store=store, aid="a0")
    run(t2, spec, resolver=resolver, store=store, aid="a1")
    run(t1, spec, resolver=resolver, store=store, aid="a0")  # identical rerun adds nothing
    assert len(store.edges) == 2  # two article-scoped person clusters before consolidation
    assert resolver.consolidate_persons() == 1
    store.remap(resolver.store.canonical_id)
    assert len(store.edges) == 1
    e = next(iter(store.edges.values()))
    assert len(e.evidence) == 2 and {r.article_id for r in e.evidence} == {"a0", "a1"}


def test_evidence_validation_rejects_bad_offsets_provenance_and_quote():
    _store0, res, _ = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.")
    c = res.candidates[0]
    text = res.article.text
    store = EdgeStore()
    bad = c.model_copy(update={"evidence_start": c.evidence_start + 1})
    assert store.add(art(text), bad, verdict_for(c), "t") is None
    assert ReasonCode.MISSING_EVIDENCE in store.outcomes[c.candidate_id].reasons
    nourl = art(text).model_copy(update={"url": ""})
    assert store.add(nourl, c, verdict_for(c), "t") is None
    assert store.add(art(text), c, verdict_for(c, evidence_text="câu không có trong bài"), "t") is None
    assert not store.edges


def test_llm_cannot_flip_structure_derived_direction():
    text = "Vinhomes là công ty con của Vingroup."
    st = EdgeStore()
    _, res, _ = run(text, resolver=make_resolver(), store=st)
    c = res.candidates[0]
    assert (c.subject.text, c.object.text, c.direction_source) == ("Vinhomes", "Vingroup", "pattern")
    assert (next(iter(st.edges))) == ("org:vinhomes", "SUBSIDIARY_OF", "org:vingroup")
    flipped = verdict_for(c, subject_mention="Vingroup", object_mention="Vinhomes", direction="REVERSED")
    st2 = EdgeStore()
    assert st2.add(res.article, c, flipped, "t", relations_spec=None) is None
    assert ReasonCode.INVALID_DIRECTION in st2.outcomes[c.candidate_id].reasons


def test_without_verifier_nothing_is_official():
    store, res, cn = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.", verifier=None)
    assert res.candidates and store.edges and store.official_edges() == []
    assert cn.llm_eligible == 0
    assert ReasonCode.NOT_VERIFIED in store.outcomes[res.candidates[0].candidate_id].reasons


def test_provisional_org_endpoint_is_review_not_official():
    from vckg.models import ResolutionStatus
    store, _, _ = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.", resolver=make_resolver(ResolutionStatus.PROVISIONAL))
    assert store.edges and store.official_edges() == []
    e = next(iter(store.edges.values()))
    assert "ENDPOINT_NOT_VERIFIED" in e.evidence[0].validation_status


def test_verdict_requires_all_fields():
    with pytest.raises(ValueError):
        Verdict.model_validate_json('{"valid": true, "factual_status": "FACT"}')


def test_llm_negated_verdict_creates_no_edge():
    class Denier:
        model, prompt_version = "t", "t"
        def verify(self, c, definition=""):
            return verdict_for(c, factual_status=FactualStatus.DENIED)
    store, _, _ = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.", verifier=Denier())
    assert not store.edges


def test_llm_valid_true_is_not_sufficient_when_rule_says_planned():
    store, res, _ = run("Ông Phạm Nhật Vượng dự kiến sẽ là Chủ tịch HĐQT Vingroup.")
    assert res.candidates and store.official_edges() == []


def test_article_dedup_url_and_content():
    st = Staging(":memory:")
    long = "Nội dung bài báo " * 40
    assert st.add_article("https://www.cafef.vn/x-1.chn?utm_source=fb", "cafef", "t", long, None)[0] == "inserted"
    assert st.add_article("https://cafef.vn/x-1.chn", "cafef", "t", long + " khác", None)[0] == "duplicate_url"
    assert st.add_article("https://vietstock.vn/y", "vietstock", "t", long.upper(), None)[0] == "duplicate_content"
    assert st.count_articles() == 1
    assert canonicalize_url("https://WWW.a.com/p/?b=1&utm_source=x#f") == "https://a.com/p?b=1"


def test_jsonl_roundtrip(tmp_path):
    store, res, _ = run("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup.")
    write_jsonl(tmp_path / "m.jsonl", res.mentions)
    assert read_jsonl(tmp_path / "m.jsonl", Mention) == res.mentions
    write_jsonl(tmp_path / "e.jsonl", store.edges.values())
    edges = read_jsonl(tmp_path / "e.jsonl", Edge)
    assert edges[0].evidence[0].source_url and edges[0].evidence[0].relation_score is None


def test_projections_are_labelled_derived():
    ev = EvidenceRecord(article_id="a", source_url="u", evidence_text="t", evidence_start=0, evidence_end=1,
                        extraction_method="m", review_status=ReviewStatus.AUTO_ACCEPTED, factual_status=FactualStatus.FACT)
    edges = [Edge(subject_id="p1", predicate="CHAIR_OF", object_id="o1", evidence=[ev]),
             Edge(subject_id="p2", predicate="CEO_OF", object_id="o1", evidence=[ev]),
             Edge(subject_id="p2", predicate="BOARD_MEMBER_OF", object_id="o2", evidence=[ev])]
    pp = person_person_projection(edges)
    assert pp.has_edge("p1", "p2") and pp["p1"]["p2"]["derived"] is True
    cc = company_company_projection(edges)
    assert cc["o1"]["o2"]["derived"] is True and cc["o1"]["o2"]["kind"] == "SHARED_LEADER"


def test_detect_factuality_back_compat():
    assert detect_factuality("A không phải là chủ tịch B") == FactualStatus.DENIED
    assert generate_candidates([], [], {}) == []
