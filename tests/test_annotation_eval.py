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


# ---------------------------------------------------------------- Phase 5 evaluation sections
def test_split_is_deterministic_and_roughly_70_30():
    from vckg.annotation import split_of
    ids = [f"art{i}" for i in range(400)]
    sp = [split_of(i) for i in ids]
    assert sp == [split_of(i) for i in ids]
    assert 0.6 < sp.count("development") / 400 < 0.8


def test_ner_per_type_and_linking_and_false_merge(tmp_path):
    import sqlite3
    db = tmp_path / "r.sqlite"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE entities(entity_id TEXT, canonical_name TEXT, merged_into TEXT)")
    c.executemany("INSERT INTO entities VALUES(?,?,?)", [("e1", "Công ty Alpha", None), ("e2", "Ông X", None), ("e3", "Công ty Beta", "e1")])
    c.commit(); c.close()
    spans = json.dumps([{"start": 0, "end": 5, "label": "ORGANIZATION", "entity_id": "e1"}, {"start": 10, "end": 15, "label": "PERSON", "entity_id": "e2"},
                        {"start": 20, "end": 25, "label": "ORGANIZATION", "entity_id": None}])
    gold_sp = json.dumps([{"start": 0, "end": 5, "label": "ORGANIZATION"}, {"start": 10, "end": 15, "label": "PERSON"}, {"start": 20, "end": 25, "label": "ORGANIZATION"}])
    gold_c = json.dumps({"0-5": "Công ty Alpha", "10-15": "Ông Y", "20-25": "UNRESOLVED"})
    rows = [_row("S1", entity_spans=spans, gold_entity_spans=gold_sp, gold_entity_canonical=gold_c, split="development")]
    out = evaluate(rows, db)
    assert out["ner"]["per_type"]["PERSON"]["tp"] == 1 and out["ner"]["span_and_type"]["fn"] == 0
    lk = out["entity_linking"]
    assert lk["exact_entity_accuracy"] == 0.5 and lk["wrong_entity"] == 1 and lk["correctly_left_unresolved"] == 1
    # false merge: two mentions linked to e1 but gold canonicals differ
    s2 = json.dumps([{"start": 0, "end": 5, "label": "ORGANIZATION", "entity_id": "e1"}])
    rows2 = [_row("S1", entity_spans=s2, gold_entity_canonical=json.dumps({"0-5": "Công ty Alpha"})),
             _row("S2", entity_spans=s2, gold_entity_canonical=json.dumps({"0-5": "Công ty Gamma"}))]
    assert evaluate(rows2, db)["entity_linking"]["false_merge_rate_pairs"] == 1.0
    assert evaluate(rows2)["entity_linking"].startswith("NOT EVALUATED (registry")


def test_candidate_recall_direction_and_full_article_recall():
    rows = [
        _row("S1", annotation_scope="sentence_sample", predicted_relation="CHAIR_OF", predicted_subject="A", predicted_object="B", predicted_outcome="rejected",
             predicted_status="FACT", gold_relation="CHAIR_OF", gold_subject="B", gold_object="A", gold_status="FACT"),   # generated, reversed
        _row("F1", annotation_scope="full_article", predicted_relation="CEO_OF", predicted_subject="C", predicted_object="D", predicted_outcome="official",
             predicted_status="FACT", gold_relation="CEO_OF", gold_subject="C", gold_object="D", gold_status="FACT"),
        _row("F2", annotation_scope="full_article", gold_relation="OWNS_SHARES_IN", gold_subject="E", gold_object="F", gold_status="FACT"),  # missed
    ]
    out = evaluate(rows)
    assert out["relations"]["candidate_recall"]["gold_relations"] == 3 and out["relations"]["candidate_recall"]["generated_as_candidate"] == 2
    assert out["relations"]["direction_accuracy_on_generated"] == 0.5
    e2e = out["end_to_end"]
    assert e2e["official_edge_precision"] == 1.0 and e2e["official_edge_recall_full_articles"] == 0.5
    assert evaluate(rows, split="blind_holdout")["annotated_sentences_relations"] == 0


def test_full_article_export_lists_cue_sentences_even_without_candidates(tmp_path):
    res, mentions, _outcomes = _build()
    from vckg.annotation import rows_for_article
    rows = rows_for_article(res.article, mentions, [], scope="full_article")
    assert rows and all(r["annotation_scope"] == "full_article" and r["split"] in ("development", "blind_holdout") for r in rows)
