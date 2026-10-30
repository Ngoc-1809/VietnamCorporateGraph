"""Evaluation on a human-annotated CSV (see annotation.py). Strict by design:
 - NER: exact (start, end[, label]) span match per sentence;
 - Edges: exact normalized (subject, relation, object) per sentence; status accuracy reported separately.
If no row has gold values, every metric is NOT EVALUATED - nothing is inferred from predictions."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from vckg.entity_linking.normalize import fold


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}


def _norm(s: str) -> str:
    return fold(s)


def load(path: str | Path) -> list[dict]:
    return list(csv.DictReader(Path(path).open(encoding="utf-8-sig")))


def evaluate(rows: list[dict]) -> dict:
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[r["sample_id"]].append(r)
    ner_sents = [sid for sid, rs in by.items() if any(r["gold_entity_spans"].strip() for r in rs)]
    rel_sents = [sid for sid, rs in by.items() if any(r["gold_relation"].strip() for r in rs)]
    out: dict = {"annotated_sentences_ner": len(ner_sents), "annotated_sentences_relations": len(rel_sents), "total_sentences": len(by)}
    # ---- strict span-level NER
    if not ner_sents:
        out["ner"] = "NOT EVALUATED (no gold_entity_spans filled)"
    else:
        tp_s = fp_s = fn_s = tp_t = fp_t = fn_t = 0
        for sid in ner_sents:
            r0 = by[sid][0]
            pred = {(m["start"], m["end"], m["label"]) for m in json.loads(r0["entity_spans"] or "[]")}
            gold_raw = next(r["gold_entity_spans"] for r in by[sid] if r["gold_entity_spans"].strip())
            gold = {(g["start"], g["end"], g["label"]) for g in json.loads(gold_raw)}
            ps, gs = {(a, b) for a, b, _ in pred}, {(a, b) for a, b, _ in gold}
            tp_s += len(ps & gs); fp_s += len(ps - gs); fn_s += len(gs - ps)
            tp_t += len(pred & gold); fp_t += len(pred - gold); fn_t += len(gold - pred)
        out["ner"] = {"span_only": _prf(tp_s, fp_s, fn_s), "span_and_type": _prf(tp_t, fp_t, fn_t)}
    # ---- edges
    if not rel_sents:
        out["edges"] = "NOT EVALUATED (no gold_relation filled)"
        return out
    tiers = {"official": {"official"}, "official_or_candidate": {"official", "candidate_edge"}, "all_predictions": {"official", "candidate_edge", "rejected"}}
    res = {}
    for tier, allowed in tiers.items():
        tp = fp = fn = status_ok = 0
        for sid in rel_sents:
            rs = by[sid]
            gold = {}
            for r in rs:
                g = r["gold_relation"].strip()
                if g and g.upper() != "NONE":
                    gold[(_norm(r["gold_subject"]), g.upper(), _norm(r["gold_object"]))] = r["gold_status"].strip().upper()
            pred = {}
            for r in rs:
                if r["predicted_relation"] and r["predicted_outcome"] in allowed:
                    pred[(_norm(r["predicted_subject"]), r["predicted_relation"].upper(), _norm(r["predicted_object"]))] = r["predicted_status"].upper()
            hit = set(pred) & set(gold)
            tp += len(hit); fp += len(set(pred) - set(gold)); fn += len(set(gold) - set(pred))
            status_ok += sum(1 for k in hit if gold[k] and gold[k] == pred[k])
        d = _prf(tp, fp, fn)
        d["status_accuracy_on_matched"] = status_ok / tp if tp else None
        res[tier] = d
    out["edges"] = res
    out["note"] = "Edge Precision is meaningful only on the annotated sample; it is not a corpus-level estimate."
    return out


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    print(json.dumps(evaluate(load(argv[0])), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
