"""Phase 6B.1 tests: structured output, evidence verbatim, entity mapping, modality, dedup/fusion, budget. The LLM is scripted (never a Qwen result)."""
import json

import httpx
import pytest

from vckg.models import FactualStatus
from vckg.preprocessing.text import split_sentences
from vckg.relation_extraction import llm_discovery as ld
from vckg.relation_extraction.candidate_fusion import fuse
from vckg.relation_extraction.candidates import load_relations
from vckg.relation_extraction.qwen_verifier import LLMCache

REL = load_relations(str(ld.__file__).split("src")[0] + "config/relations.yaml")
T = ("Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh. Công ty cổ phần Bình Minh sở hữu 51% vốn của Công ty cổ phần Sao Mai. "
     "Ông Nguyễn Văn An không phải là Tổng giám đốc Công ty cổ phần Sao Mai.")


def M(surface, label, eid, mid, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = T.index(surface, i + 1)
    return {"mid": mid, "text": surface, "start": i, "end": i + len(surface), "label": label, "entity_id": eid, "link_status": "grounded", "linking_method": "x",
            "ner_score": 0.9, "method": "gliner2.5", "sentence_index": None}


MS = {m["mid"]: m for m in [M("Nguyễn Văn An", "PERSON", "p:an", "M0"), M("Công ty cổ phần Bình Minh", "ORGANIZATION", "o:bm", "M1"),
                             M("Công ty cổ phần Bình Minh", "ORGANIZATION", "o:bm", "M2", 1), M("Công ty cổ phần Sao Mai", "ORGANIZATION", "o:sm", "M3")]}
SENTS = split_sentences(T)
WIN = {"start": 0, "end": len(T)}


def rel(**kw):
    return {"subject_mention_id": "M0", "subject_text": "", "object_mention_id": "M1", "object_text": "", "predicate": "CHAIR_OF",
            "evidence_text": "Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh.", "factual_status": "FACT", "discovery_reason": "x"} | kw


def val(r):
    for m in MS.values():
        m["sentence_index"] = next(s.index for s in SENTS if s.start <= m["start"] < s.end)
    return ld.validate_relation(r, T, WIN, SENTS, MS, REL, "a1")


def test_schema_is_closed_enum_and_excludes_issued_bond():
    props = ld.SCHEMA["properties"]["relations"]["items"]["properties"]
    assert "ISSUED_BOND" not in props["predicate"]["enum"] and set(props["factual_status"]["enum"]) == set(ld.STATUSES)
    assert "DENIED" not in props["factual_status"]["enum"]


def test_valid_relation_becomes_llm_candidate_only():
    out, why = val(rel())
    c = out["candidate"]
    assert why == "OK" and c.direction_source == "llm" and c.method == "llm" and c.predicate == "CHAIR_OF"
    assert (c.subject.entity_id, c.object.entity_id) == ("p:an", "o:bm") and T[c.evidence_start:c.evidence_end] == c.evidence_text


def test_quote_must_be_verbatim_or_ordered_subsequence():
    assert val(rel(evidence_text="Ông An chủ tịch của một công ty khác hoàn toàn"))[1] == "EVIDENCE_NOT_VERBATIM"
    assert val(rel(evidence_text="Ông Nguyễn Văn An là Chủ tịch HĐQT Công ty cổ phần Bình Minh ..."))[1] == "OK"  # trailing ellipsis tolerated
    assert val(rel(evidence_text=""))[1] == "EVIDENCE_NOT_VERBATIM"


def test_unknown_mention_wrong_types_self_loop_bad_predicate():
    assert val(rel(object_mention_id="M99"))[1] == "UNKNOWN_MENTION_ID"
    assert val(rel(subject_mention_id="M1", object_mention_id="M3"))[1] == "TYPE_MISMATCH"  # org cannot chair an org
    assert val(rel(object_mention_id="M0"))[1] == "SELF_LOOP"
    assert val(rel(predicate="ISSUED_BOND"))[1] == "BAD_PREDICATE" and val(rel(predicate="LOVES"))[1] == "BAD_PREDICATE"


def test_mention_id_of_earlier_occurrence_maps_to_occurrence_near_the_quote():
    out, why = val(rel(subject_mention_id="M2", subject_text="", predicate="OWNS_SHARES_IN", object_mention_id="M3",
                       evidence_text="Công ty cổ phần Bình Minh sở hữu 51% vốn của Công ty cổ phần Sao Mai."))
    assert why == "OK" and out["candidate"].subject.start == MS["M2"]["start"]
    out2, _ = val(rel(subject_mention_id="M1", predicate="OWNS_SHARES_IN", object_mention_id="M3",
                      evidence_text="Công ty cổ phần Bình Minh sở hữu 51% vốn của Công ty cổ phần Sao Mai."))
    assert out2["candidate"].subject.start == MS["M2"]["start"]  # M1 is in sentence 1, the quote is in sentence 2 -> nearest same-entity occurrence


def _mini(text, quote, pred="OWNS_SHARES_IN", status="FACT"):
    sents = split_sentences(text)
    a, b = "Công ty cổ phần Bình Minh", "Công ty cổ phần Sao Mai"
    ms = {"M0": {"mid": "M0", "text": a, "start": text.index(a), "end": text.index(a) + len(a), "label": "ORGANIZATION", "entity_id": "o:bm", "link_status": "grounded",
                 "linking_method": "x", "sentence_index": 0, "ner_score": 0.9, "method": "gliner2.5"},
          "M1": {"mid": "M1", "text": b, "start": text.index(b), "end": text.index(b) + len(b), "label": "ORGANIZATION", "entity_id": "o:sm", "link_status": "grounded",
                 "linking_method": "x", "sentence_index": 0, "ner_score": 0.9, "method": "gliner2.5"}}
    return ld.validate_relation(rel(subject_mention_id="M0", object_mention_id="M1", predicate=pred, evidence_text=quote, factual_status=status), text,
                                {"start": 0, "end": len(text)}, sents, ms, REL, "a1")


def test_negation_dropped_and_modality_only_makes_status_stricter():
    t = "Công ty cổ phần Bình Minh không sở hữu cổ phần của Công ty cổ phần Sao Mai theo công bố."
    assert _mini(t, t)[1] == "NEGATED"
    t2 = "Công ty cổ phần Bình Minh dự kiến sở hữu 51% vốn của Công ty cổ phần Sao Mai."
    out, why = _mini(t2, t2)  # model says FACT, rule layer sees 'dự kiến' -> PLANNED (stricter wins)
    assert why == "OK" and out["candidate"].factual_status == FactualStatus.PLANNED and out["rule_status"] == "PLANNED" and out["model_status"] == "FACT"
    t3 = "Công ty cổ phần Bình Minh sở hữu 51% vốn của Công ty cổ phần Sao Mai."
    assert _mini(t3, t3, status="PLANNED")[0]["candidate"].factual_status == FactualStatus.PLANNED  # model stricter than rules is kept


def test_unresolved_endpoint_has_no_identity_and_requires_exact_text():
    out, why = val(rel(object_mention_id="NONE", object_text="Công ty cổ phần Bình Minh"))
    assert why == "OK" and out["unresolved"] and out["object"]["entity_id"] is None
    assert val(rel(object_mention_id="NONE", object_text="Công ty bịa đặt"))[1] == "UNKNOWN_MENTION_ID"


def test_fusion_dedup_methods_status_conflict():
    out, _ = val(rel())
    llm_c = out["candidate"]
    rule_c = llm_c.model_copy(update={"candidate_id": "r1", "method": "pattern", "direction_source": "pattern"})
    hist = llm_c.model_copy(update={"candidate_id": "l2", "factual_status": FactualStatus.HISTORICAL})
    f = fuse([{"cand": rule_c, "method": "RULE", "meta": {}}, {"cand": llm_c, "method": "LLM", "meta": {"x": 1}}, {"cand": llm_c, "method": "LLM", "meta": {"x": 2}},
              {"cand": hist, "method": "LLM", "meta": {}}])
    both = next(x for x in f if x["factual_status"] == "FACT")
    assert len(f) == 2 and both["discovery_method"] == "BOTH" and both["raw_count"] == 3 and both["duplicate_raw"] == 2 and len(both["evidence"]) == 1
    assert all(x["status_conflict"] for x in f)  # same (s,p,o), different status: kept apart and flagged


def test_budget_cap_cache_and_failure_accounting(monkeypatch, tmp_path):
    calls = {"n": 0}
    good = json.dumps({"relations": []})

    class R:
        def __init__(self, c): self.c = c
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": self.c}, "prompt_eval_count": 10, "eval_count": 3}

    def post(url, json=None, timeout=None):
        calls["n"] += 1
        return R(good if calls["n"] != 2 else "not json")
    monkeypatch.setattr(httpx, "post", post)
    llm = ld.DiscoveryLLM(LLMCache(":memory:"), max_live_calls=3)
    ms = list(MS.values())
    assert llm.discover("t", "p1", ms)["parsed"] == {"relations": []}
    assert llm.discover("t", "p2", ms) is None and llm.stats.failures == 1  # invalid JSON -> None, still counted as a live call
    assert llm.discover("t", "p1", ms)["cached"] is True and llm.stats.cache_hits == 1 and llm.stats.calls == 2
    llm.discover("t", "p3", ms)
    with pytest.raises(ld.BudgetExceeded):
        llm.discover("t", "p4", ms)
    assert llm.stats.prompt_tokens == 20 and llm.stats.eval_tokens == 6


def test_window_selection_prefers_cue_sentences_and_reports_unexamined():
    sents = split_sentences("Câu một về thời tiết hôm nay. Ông A là Chủ tịch Công ty B. Câu ba. Ông C sở hữu cổ phần Công ty D. Câu năm.")
    ms = [{"sentence_index": s.index, "entity_id": f"e{s.index}{k}", "text": "x"} for s in sents for k in (0, 1)]
    wins = ld.window_sentences(sents, ms, __import__("re").compile("chủ tịch|sở hữu", 2), max_chars=40)
    chosen, left = ld.select_windows(wins, k=1)
    assert len(chosen) == 1 and chosen[0]["cue_sentences"] >= 1 and left == len(wins) - 1
