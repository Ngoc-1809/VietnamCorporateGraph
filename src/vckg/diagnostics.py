"""Phase 4 / Task A: offline diagnostics over an existing pipeline output directory.

Reads entities/candidates/verdicts JSONL (+ staging SQLite for article text/URL) and explains, per
candidate, why it did / did not become an edge. No model is called."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from vckg.models import Article, Mention, RelationCandidate, Verdict
from vckg.ner.scope import classify_scope
from vckg.preprocessing.text import normalize_text
from vckg.reasons import IDENTITY_REASONS, diagnose_candidate
from vckg.relation_extraction.candidates import load_relations
from vckg.storage.sqlite import Staging

ROOT = Path(__file__).resolve().parents[2]


def _jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def mention_counters(mentions: list[dict]) -> dict:
    ms = [Mention.model_validate({k: v for k, v in m.items() if k != "article_id"}) for m in mentions]
    scope = [classify_scope(m) for m in ms]
    dom_labels = {"PERSON", "ORGANIZATION", "BANK"}
    in_dom = [(m, s) for m, s in zip(ms, scope, strict=True) if s[0]]
    pob = [m for m in ms if m.label.value in dom_labels]
    pob_in = [m for m, s in zip(ms, scope, strict=True) if s[0] and m.label.value in dom_labels]
    uniq = {(m.label.value, m.text) for m in ms}
    return {
        "mentions_total": len(ms),
        "mentions_unique_surface": len(uniq),
        "mentions_person_org_bank": len(pob),
        "mentions_person_org_bank_in_scope": len(pob_in),
        "mentions_in_scope_all_labels": len(in_dom),
        "out_of_scope_by_reason": dict(Counter(s[1] for s in scope if not s[0])),
        "linked_total": sum(1 for m in ms if m.entity_id),
        "linked_in_scope": sum(1 for m, s in zip(ms, scope, strict=True) if m.entity_id and s[0]),
        "unresolved_total": sum(1 for m in ms if not m.entity_id),
        "unresolved_in_scope": sum(1 for m, s in zip(ms, scope, strict=True) if not m.entity_id and s[0]),
        "by_label": dict(Counter(m.label.value for m in ms)),
    }


def run(out_dir: Path, db_path: Path, report_dir: Path) -> dict:
    cands = [RelationCandidate.model_validate(x) for x in _jl(out_dir / "candidates.jsonl")]
    raw_verdicts = {x["candidate_id"]: x["verdict"] for x in _jl(out_dir / "verdicts.jsonl")}
    verdicts = {k: (Verdict.model_validate(v) if v else None) for k, v in raw_verdicts.items()}  # legacy keys are mapped
    mentions = _jl(out_dir / "entities.jsonl")
    rels = load_relations(str(ROOT / "config/relations.yaml"))
    st = Staging(db_path)
    arts: list[Article] = st.get_articles()
    norm = {a.article_id: normalize_text(a.text) for a in arts}
    by_id = {a.article_id: a for a in arts}

    def find_article(c: RelationCandidate) -> str | None:
        for aid, txt in norm.items():  # candidates did not carry article_id in Phase 3 (traceability gap)
            if txt[c.evidence_start:c.evidence_end] == c.evidence_text and txt[c.subject.start:c.subject.end] == c.subject.text:
                return aid
        return None

    rows = []
    for c in cands:
        aid = find_article(c)
        text = norm.get(aid, "")
        v = verdicts.get(c.candidate_id)
        reasons = diagnose_candidate(text, c, v, rels[c.predicate])
        non_identity = [r for r in reasons if r not in IDENTITY_REASONS]
        rows.append({
            "article_id": aid or "", "source_url": by_id[aid].url if aid else "",
            "subject_text": c.subject.text, "subject_type": c.subject.label.value, "subject_linked_id": c.subject.entity_id or "",
            "object_text": c.object.text, "object_type": c.object.label.value, "object_linked_id": c.object.entity_id or "",
            "predicate": c.predicate, "evidence_sentence": c.evidence_text,
            "rule_cue": c.cue, "rule_factual_status": c.factual_status.value,
            "qwen_valid": "" if v is None else v.valid, "qwen_factual_status": "" if v is None else v.factual_status.value,
            "qwen_subject": "" if v is None else v.subject_text, "qwen_object": "" if v is None else v.object_text,
            "qwen_self_reported_confidence_raw": "" if v is None else (raw_verdicts[c.candidate_id] or {}).get("confidence", ""),
            "final_status": "ACCEPTED" if not reasons else "REJECTED",
            "rejection_reasons": "|".join(r.value for r in reasons),
            "primary_reason": reasons[0].value if reasons else "",
            "reasons_excluding_identity": "|".join(r.value for r in non_identity),
            "would_pass_if_endpoints_resolved": (not non_identity),
        })
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "phase4_candidate_diagnostics.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    mc = mention_counters(mentions)
    reason_hist = Counter(r for row in rows for r in row["rejection_reasons"].split("|") if r)
    summ = {"mention_counters": mc, "candidates": len(rows), "reason_histogram": dict(reason_hist),
            "accepted": sum(1 for r in rows if r["final_status"] == "ACCEPTED"),
            "would_pass_if_resolved": sum(1 for r in rows if r["would_pass_if_endpoints_resolved"]),
            "llm_valid_true": sum(1 for r in rows if r["qwen_valid"] is True),
            "llm_valid_false": sum(1 for r in rows if r["qwen_valid"] is False)}
    (report_dir / "phase4_baseline_counters.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    return summ


if __name__ == "__main__":
    s = run(ROOT / "data/outputs/baseline_phase3", ROOT / "data/staging/staging.sqlite", ROOT / "reports")
    print(json.dumps(s, ensure_ascii=False, indent=2))

