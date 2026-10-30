"""Integration tests: need CUDA GPU, cached GLiNER weights, Ollama with qwen3.5:9b, internet.
Run: uv run pytest -m integration -rs   (unavailable services => SKIPPED, never PASS)."""
import pytest

from vckg.models import EntityType, Mention, RelationCandidate

pytestmark = pytest.mark.integration


def _cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False


def test_gliner_real_inference_cuda():
    if not _cuda():
        pytest.skip("CUDA unavailable")
    from vckg.ner.gliner_adapter import GlinerNER
    ner = GlinerNER(device="cuda")
    text = "Ông Phạm Nhật Vượng là Chủ tịch Tập đoàn Vingroup."
    ms = ner.extract(text)
    assert ms, "GLiNER returned nothing"
    assert all(text[m.start:m.end] == m.text for m in ms)
    assert any(m.label == EntityType.PERSON for m in ms)


def test_qwen_real_verification():
    from vckg.relation_extraction.qwen_verifier import QwenVerifier
    v = QwenVerifier()
    if not v.is_available():
        pytest.skip("Ollama / qwen3.5:9b unavailable")
    t = "Ông Phạm Nhật Vượng là Chủ tịch HĐQT Tập đoàn Vingroup."
    s = Mention(text="Phạm Nhật Vượng", start=4, end=19, label=EntityType.PERSON, entity_id="p")
    o = Mention(text="Vingroup", start=t.index("Vingroup"), end=t.index("Vingroup") + 8, label=EntityType.ORGANIZATION, entity_id="o")
    c = RelationCandidate(candidate_id="i", subject=s, object=o, predicate="CHAIR_OF", sentence_index=0,
                          evidence_text=t, evidence_start=0, evidence_end=len(t))
    verdict = v.verify(c)
    assert verdict is not None  # schema-valid JSON came back from the real model


def test_live_rss_reachable():
    import httpx
    try:
        r = httpx.get("https://cafef.vn/doanh-nghiep.rss", timeout=15)
    except httpx.HTTPError:
        pytest.skip("internet unavailable")
    assert r.status_code == 200


def test_gliner_sentence_level_offsets_real():
    if not _cuda():
        pytest.skip("CUDA unavailable")
    from vckg.ner.gliner_adapter import GlinerNER
    from vckg.preprocessing.text import normalize_text, split_sentences
    text = normalize_text("Ông Phạm Nhật Vượng là Chủ tịch Tập đoàn Vingroup. Vinhomes là công ty con của Vingroup.")
    sents = split_sentences(text)
    ms = GlinerNER(device="cuda").extract_sentences(text, sents)
    assert ms and all(text[m.start:m.end] == m.text for m in ms)


def test_qwen_real_schema_and_direction_on_real_sentence():
    from helpers import FakeNER, art, make_resolver
    from vckg.pipeline import process_article
    from vckg.relation_extraction.candidates import load_relations
    from vckg.relation_extraction.qwen_verifier import QwenVerifier
    from vckg.validation.evidence import EdgeStore
    v = QwenVerifier()
    if not v.is_available():
        pytest.skip("Ollama / qwen3.5:9b unavailable")
    root = __import__("helpers").ROOT
    rel = load_relations(str(root / "config" / "relations.yaml"))
    t = "Vinhomes là công ty con của Vingroup."
    ner = FakeNER({"Vinhomes": EntityType.ORGANIZATION, "Vingroup": EntityType.ORGANIZATION})  # NER is a double HERE only; Qwen is real
    store = EdgeStore()
    res = process_article(art(t), rel, make_resolver(), store, ner, v)
    c = res.candidates[0]
    verdict = res.verdicts[c.candidate_id]
    assert verdict is not None, "real Qwen returned schema-invalid JSON"
    assert verdict.relation_type in ("SUBSIDIARY_OF", "NO_RELATION")
    assert v.stats.calls + v.stats.cache_hits >= 1 and v.stats.prompt_tokens >= 0


def test_live_identity_sitemap_and_baodautu_category_reachable():
    import httpx
    try:
        r = httpx.get("https://finance.vietstock.vn/sitemap.xml", timeout=40, headers={"User-Agent": "VCKG-research-bot/0.1 (academic)"})
        b = httpx.get("https://baodautu.vn/kinh-doanh-d3/", timeout=30, headers={"User-Agent": "VCKG-research-bot/0.1 (academic)"})
    except httpx.HTTPError:
        pytest.skip("internet unavailable")
    import re

    from vckg.entity_linking.identity import VietstockSitemapProvider
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
    recs = list(VietstockSitemapProvider(client=None).parse(locs, "t"))
    assert r.status_code == 200 and len(recs) > 500 and all(x.identity_only for x in recs)
    assert b.status_code == 200 and re.search(r"-d\d+\.html", b.text)
