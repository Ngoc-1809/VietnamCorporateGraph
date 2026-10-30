"""Annotation export + evaluation tests (synthetic rows; no model is run)."""
import csv
import json

from helpers import FakeNER, art, make_resolver
from vckg.annotation import COLUMNS, rows_for_article, sample_rows, write_csv
from vckg.evaluation import evaluate, load
from vckg.models import EntityType
from vckg.pipeline import Counters, process_article
from vckg.relation_extraction.candidates import load_relations
from vckg.validation.evidence import EdgeStore

P, O = EntityType.PERSON, EntityType.ORGANIZATION
REL = load_relations(str(__import__("helpers").ROOT / "config" / "relations.yaml"))


def _outcomes(res, store):
    rows = []
    for c in res.candidates:
        oc = store.outcomes[c.candidate_id]
        v = res.verdicts.get(c.candidate_id)
        rows.append({"article_id": res.article.article_id, "evidence": c.evidence_text, "subject_text": c.subject.text,
                     "object_text": c.object.text, "predicate": c.predicate, "rule_status": c.factual_status.value,
                     "outcome": oc.outcome, "reasons": "|".join(r.value for r in oc.reasons),
                     "llm_valid": "" if v is None else str(v.valid), "llm_status": "" if v is None else v.factual_status.value})
    return rows


def _build():
    from helpers import AcceptAll
    text = ("Ông Phạm Nhật Vượng là Chủ tịch HĐQT Vingroup. Vingroup và Hòa Phát cùng có mặt trong danh sách. "
            "Vingroup đang đàm phán mua lại VinFast. Vinhomes ký thỏa thuận với Hòa Phát.")
    spec = {"Phạm Nhật Vượng": P, "Vingroup": O, "Hòa Phát": O, "VinFast": O, "Vinhomes": O}
    store, resolver = EdgeStore(), make_resolver()
    res = process_article(art(text), REL, resolver, store, FakeNER(spec), AcceptAll(), Counters())
    mentions = [{"article_id": "a1", **m.model_dump(mode="json")} for m in res.mentions]
    return res, mentions, _outcomes(res, store)


def test_export_has_empty_gold_and_all_columns(tmp_path):
    res, mentions, outcomes = _build()
    rows = rows_for_article(res.article, mentions, outcomes)
    assert rows and {"relation_accepted_or_candidate", "no_relation_control"} & {r["stratum"] for r in rows}
    sample = sample_rows(rows, n=10)
    p = tmp_path / "s.csv"
    write_csv(p, sample)
    back = list(csv.DictReader(p.open(encoding="utf-8-sig")))
    assert list(back[0].keys()) == COLUMNS
    assert all(r["gold_subject"] == r["gold_object"] == r["gold_relation"] == r["gold_status"] == r["gold_entity_spans"] == "" for r in back)
    assert any(r["predicted_relation"] == "CHAIR_OF" for r in back)  # model prediction lives only in predicted_* columns


def test_sampling_deterministic_and_stratified():
    res, mentions, outcomes = _build()
    rows = rows_for_article(res.article, mentions, outcomes) * 1
    a, b = sample_rows(rows, 3, seed=5), sample_rows(rows, 3, seed=5)
    assert a == b and len({r["sample_id"] for r in a}) <= 3
    assert len({r["stratum"] for r in a}) >= 2


def _row(sid, **kw):
    base = {c: "" for c in COLUMNS}
    base.update(sample_id=sid, entity_spans="[]")
    base.update(kw)
    return base


def test_evaluation_not_evaluated_without_gold():
    out = evaluate([_row("S1", predicted_relation="CHAIR_OF", predicted_subject="A", predicted_object="B", predicted_outcome="official")])
    assert out["ner"].startswith("NOT EVALUATED") and out["edges"].startswith("NOT EVALUATED")


def test_evaluation_strict_edge_and_ner_metrics():
    spans = json.dumps([{"start": 0, "end": 3, "label": "PERSON"}, {"start": 10, "end": 14, "label": "ORGANIZATION"}])
    gold = json.dumps([{"start": 0, "end": 3, "label": "PERSON"}, {"start": 10, "end": 15, "label": "ORGANIZATION"}])
    rows = [
        _row("S1", entity_spans=spans, gold_entity_spans=gold, predicted_relation="CHAIR_OF", predicted_subject="Ông An", predicted_object="Công ty B",
             predicted_outcome="official", predicted_status="FACT", gold_relation="CHAIR_OF", gold_subject="ong an", gold_object="cong ty b", gold_status="FACT"),
        _row("S2", predicted_relation="CEO_OF", predicted_subject="C", predicted_object="D", predicted_outcome="official", predicted_status="FACT",
             gold_relation="NONE"),
        _row("S3", predicted_relation="OWNS_SHARES_IN", predicted_subject="E", predicted_object="F", predicted_outcome="candidate_edge", predicted_status="FACT",
             gold_relation="OWNS_SHARES_IN", gold_subject="E", gold_object="F", gold_status="PLANNED"),
        _row("S4", gold_relation="ACQUIRED", gold_subject="G", gold_object="H", gold_status="FACT"),  # model missed it
    ]
    out = evaluate(rows)
    assert out["ner"]["span_only"]["tp"] == 1 and out["ner"]["span_only"]["fp"] == 1 and out["ner"]["span_only"]["fn"] == 1
    off = out["edges"]["official"]
    assert (off["tp"], off["fp"], off["fn"]) == (1, 1, 2) and off["precision"] == 0.5  # fn: E-F (candidate only) + G-H
    both = out["edges"]["official_or_candidate"]
    assert (both["tp"], both["fp"], both["fn"]) == (2, 1, 1)
    assert both["status_accuracy_on_matched"] == 0.5  # E-F predicted FACT, gold PLANNED


def test_load_roundtrip(tmp_path):
    p = tmp_path / "e.csv"
    write_csv(p, [_row("S1", stratum="x", source="s", source_url="u", article_id="a", sentence="câu", sentence_start=0, sentence_end=3)])
    assert load(p)[0]["sample_id"] == "S1"
