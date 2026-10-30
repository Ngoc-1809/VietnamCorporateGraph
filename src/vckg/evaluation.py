"""Evaluation on a human-annotated CSV (see annotation.py). Strict by design; nothing is inferred from predictions.

Sections (each reads `NOT EVALUATED (...)` when the needed gold columns are empty):
  ner            strict span P/R/F1 (span only, span+type, per entity type)
  entity_linking exact canonical-name accuracy, unresolved rate, false-link rate, false-merge rate (needs registry DB for names)
  relations      candidate recall, relation P/R/F1 per tier, direction accuracy, status accuracy
  end_to_end     official-edge precision (all annotated sentences); official-edge RECALL only on annotation_scope=full_article rows
Use `--split development|blind_holdout` to report each split separately (blind_holdout must not be used for tuning)."""
from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from vckg.entity_linking.normalize import normalize_name


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}


def _norm(s: str) -> str:
    return normalize_name(s)


def load(path: str | Path) -> list[dict]:
    return list(csv.DictReader(Path(path).open(encoding="utf-8-sig")))


def canonical_names(registry_db: str | Path | None) -> dict[str, str]:
    if not registry_db or not Path(registry_db).exists():
        return {}
    db = sqlite3.connect(str(registry_db))
    rows = db.execute("SELECT entity_id, canonical_name, merged_into FROM entities").fetchall()
    db.close()
    by = {r[0]: r for r in rows}
    out = {}
    for eid in by:
        cur, seen = eid, set()
        while by[cur][2] and by[cur][2] in by and cur not in seen:
            seen.add(cur)
            cur = by[cur][2]
        out[eid] = by[cur][1]
    return out


def _ner(by: dict[str, list[dict]], sents: list[str]) -> dict | str:
    if not sents:
        return "NOT EVALUATED (no gold_entity_spans filled)"
    c = {k: [0, 0, 0] for k in ("span", "typed")}
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for sid in sents:
        r0 = by[sid][0]
        pred = {(m["start"], m["end"], m["label"]) for m in json.loads(r0["entity_spans"] or "[]")}
        gold = {(g["start"], g["end"], g["label"]) for g in json.loads(next(r["gold_entity_spans"] for r in by[sid] if r["gold_entity_spans"].strip()))}
        ps, gs = {(a, b) for a, b, _ in pred}, {(a, b) for a, b, _ in gold}
        c["span"][0] += len(ps & gs); c["span"][1] += len(ps - gs); c["span"][2] += len(gs - ps)
        c["typed"][0] += len(pred & gold); c["typed"][1] += len(pred - gold); c["typed"][2] += len(gold - pred)
        for lab in {x[2] for x in pred | gold}:
            pl, gl = {x[:2] for x in pred if x[2] == lab}, {x[:2] for x in gold if x[2] == lab}
            per[lab][0] += len(pl & gl); per[lab][1] += len(pl - gl); per[lab][2] += len(gl - pl)
    return {"span_only": _prf(*c["span"]), "span_and_type": _prf(*c["typed"]), "per_type": {k: _prf(*v) for k, v in sorted(per.items())}}


def _linking(by: dict[str, list[dict]], names: dict[str, str]) -> dict | str:
    sents = [sid for sid, rs in by.items() if any(r.get("gold_entity_canonical", "").strip() for r in rs)]
    if not sents:
        return "NOT EVALUATED (no gold_entity_canonical filled)"
    if not names:
        return "NOT EVALUATED (registry DB needed to map entity ids to canonical names)"
    correct = wrong = unresolved = false_link = gold_unres_ok = matched = 0
    groups: dict[str, list[str]] = defaultdict(list)
    for sid in sents:
        r0 = by[sid][0]
        pred = {(m["start"], m["end"]): m for m in json.loads(r0["entity_spans"] or "[]")}
        gold = json.loads(next(r["gold_entity_canonical"] for r in by[sid] if r["gold_entity_canonical"].strip()))
        for key, canon in gold.items():
            a, b = (int(x) for x in key.split("-"))
            m = pred.get((a, b))
            if m is None:
                continue  # NER span not matched: counted in NER recall, not here
            matched += 1
            eid = m.get("entity_id")
            if canon.upper() in ("UNRESOLVED", "NONE"):
                if eid:
                    false_link += 1
                else:
                    gold_unres_ok += 1
                continue
            if not eid:
                unresolved += 1
            elif _norm(names.get(eid, "")) == _norm(canon):
                correct += 1
                groups[eid].append(_norm(canon))
            else:
                wrong += 1
                groups[eid].append(_norm(canon))
    pairs = bad_pairs = 0
    for lst in groups.values():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                pairs += 1
                bad_pairs += lst[i] != lst[j]
    n_gold = correct + wrong + unresolved
    return {"matched_spans": matched, "exact_entity_accuracy": correct / n_gold if n_gold else None, "wrong_entity": wrong,
            "unresolved_rate": unresolved / n_gold if n_gold else None, "false_link_on_gold_unresolved": false_link,
            "correctly_left_unresolved": gold_unres_ok, "false_merge_rate_pairs": bad_pairs / pairs if pairs else None, "same_entity_pairs": pairs}


def _relations(by: dict[str, list[dict]], rel_sents: list[str]) -> dict | str:
    if not rel_sents:
        return "NOT EVALUATED (no gold_relation filled)"
    tiers = {"official": {"official"}, "official_or_candidate": {"official", "candidate_edge"}, "all_predictions": {"official", "candidate_edge", "rejected"}}
    res: dict = {}
    for tier, allowed in tiers.items():
        tp = fp = fn = status_ok = 0
        for sid in rel_sents:
            gold, pred = {}, {}
            for r in by[sid]:
                g = r["gold_relation"].strip()
                if g and g.upper() != "NONE":
                    gold[(_norm(r["gold_subject"]), g.upper(), _norm(r["gold_object"]))] = r["gold_status"].strip().upper()
                if r["predicted_relation"] and r["predicted_outcome"] in allowed:
                    pred[(_norm(r["predicted_subject"]), r["predicted_relation"].upper(), _norm(r["predicted_object"]))] = r["predicted_status"].upper()
            hit = set(pred) & set(gold)
            tp += len(hit); fp += len(set(pred) - set(gold)); fn += len(set(gold) - set(pred))
            status_ok += sum(1 for k in hit if gold[k] and gold[k] == pred[k])
        d = _prf(tp, fp, fn)
        d["status_accuracy_on_matched"] = status_ok / tp if tp else None
        res[tier] = d
    # candidate recall (any outcome) + direction accuracy over unordered matches
    n_gold = found = dir_ok = 0
    for sid in rel_sents:
        golds = [(r["gold_subject"], r["gold_relation"].strip().upper(), r["gold_object"]) for r in by[sid]
                 if r["gold_relation"].strip() and r["gold_relation"].strip().upper() != "NONE"]
        preds = [(r["predicted_subject"], r["predicted_relation"].upper(), r["predicted_object"]) for r in by[sid] if r["predicted_relation"]]
        for s, p, o in golds:
            n_gold += 1
            for ps, pp, po in preds:
                if pp == p and {_norm(ps), _norm(po)} == {_norm(s), _norm(o)}:
                    found += 1
                    dir_ok += _norm(ps) == _norm(s)
                    break
    res["candidate_recall"] = {"gold_relations": n_gold, "generated_as_candidate": found, "recall": found / n_gold if n_gold else None}
    res["direction_accuracy_on_generated"] = dir_ok / found if found else None
    return res


def evaluate(rows: list[dict], registry_db: str | Path | None = None, split: str | None = None) -> dict:
    if split:
        rows = [r for r in rows if r.get("split", "") == split]
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[r["sample_id"]].append(r)
    ner_sents = [sid for sid, rs in by.items() if any(r["gold_entity_spans"].strip() for r in rs)]
    rel_sents = [sid for sid, rs in by.items() if any(r["gold_relation"].strip() for r in rs)]
    out: dict = {"split": split or "all", "annotated_sentences_ner": len(ner_sents), "annotated_sentences_relations": len(rel_sents),
                 "total_sentences": len(by)}
    out["ner"] = _ner(by, ner_sents)
    out["entity_linking"] = _linking(by, canonical_names(registry_db))
    rel = _relations(by, rel_sents)
    out["edges"] = {k: v for k, v in rel.items() if k in ("official", "official_or_candidate", "all_predictions")} if isinstance(rel, dict) else rel
    out["relations"] = rel
    if isinstance(rel, dict):
        full = [sid for sid in rel_sents if by[sid][0].get("annotation_scope") == "full_article"]
        e2e: dict = {"official_edge_precision": rel["official"]["precision"], "official_tp_fp": [rel["official"]["tp"], rel["official"]["fp"]]}
        if full:
            sub = _relations(by, full)
            e2e["official_edge_recall_full_articles"] = sub["official"]["recall"]
            e2e["full_article_sentences"] = len(full)
        else:
            e2e["official_edge_recall_full_articles"] = "NOT EVALUATED (needs annotation_scope=full_article rows with gold)"
        out["end_to_end"] = e2e
        out["note"] = "Metrics describe the annotated sample only; they are not corpus-level estimates."
    else:
        out["end_to_end"] = "NOT EVALUATED (no gold_relation filled)"
    return out


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--registry", default=None)
    ap.add_argument("--split", default=None, choices=[None, "development", "blind_holdout"])
    a = ap.parse_args(argv)
    print(json.dumps(evaluate(load(a.csv), a.registry, a.split), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
