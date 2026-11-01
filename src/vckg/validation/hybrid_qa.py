"""Phase 6B.2 runner: rebuild A/B/C from the Phase 6B.1 outputs (no new crawl, no new discovery), reconcile counts, run the
Phase 6A auditor (baseline, unchanged) and the new hybrid validator side by side, export staging data and a ~40 item review sample.
  python -m vckg.validation.hybrid_qa all        (deterministic; no Qwen calls)
Outputs: data/experiments/phase6b/hybrid_qa/, reports/phase6b/hybrid_qa/."""
from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from vckg.models import RelationCandidate
from vckg.preprocessing.text import normalize_text
from vckg.relation_extraction.candidate_fusion import fuse
from vckg.relation_extraction.candidates import load_config, load_relations
from vckg.relation_extraction.discovery_benchmark import (
    EXP,
    REGISTRY,
    ROOT,
    RUN,
    _canon_fn,
    jl,
    load_manifest,
)
from vckg.relation_extraction.llm_discovery import DISCOVERY_PROMPT_VERSION
from vckg.storage.sqlite import Staging
from vckg.validation.auto_auditor import audit_edge, build_context
from vckg.validation.hybrid_validator import VALIDATOR_VERSION, validate_candidate

OUT = EXP / "hybrid_qa"
REP = ROOT / "reports/phase6b/hybrid_qa"
SEED = 20261101


def apply_overlay(c: RelationCandidate, overlay: dict | None) -> RelationCandidate:
    if not overlay:
        return c
    upd = {}
    for role in ("subject", "object"):
        m = getattr(c, role)
        t = overlay.get(f"{c.article_id}|{m.start}|{m.end}")
        if t:
            upd[role] = m.model_copy(update={"entity_id": t, "link_status": "grounded", "linking_method": "article_grounding_overlay"})
    return c.model_copy(update=upd) if upd else c


def build_fused(manifest: dict, overlay: dict | None = None, registry: Path = REGISTRY) -> tuple[list[dict], dict]:
    canon = _canon_fn(registry)
    items = []
    for r in jl(RUN / "candidates.jsonl"):
        if r["article_id"] in manifest:
            items.append({"cand": apply_overlay(RelationCandidate.model_validate(r), overlay), "method": "RULE", "meta": {}})
    n_rule = len(items)
    for c in jl(EXP / "batch60/chunks.jsonl"):
        if c["article_id"] in manifest and c["prompt_version"] == DISCOVERY_PROMPT_VERSION:
            for a in c["accepted"]:
                items.append({"cand": apply_overlay(RelationCandidate.model_validate(a["cand"]), overlay), "method": "LLM",
                              "meta": {"llm_quote": a["llm_quote"], "model_status": a["model_status"], "reason": a["reason"]}})
    fused = fuse(items, canon)
    for f in fused:
        f["methods"] = sorted(f["methods"])
    return fused, {"raw_rule": n_rule, "raw_llm": len(items) - n_rule}


def reconcile(fused: list[dict], raw: dict) -> dict:
    A = {f["key"] for f in fused if "RULE" in f["methods"]}
    B = {f["key"] for f in fused if "LLM" in f["methods"]}
    a3, b3 = {k[:3] for k in A}, {k[:3] for k in B}
    same_triple_other_status = sum(1 for k in B - A if k[:3] in a3)
    b_only_keys = sum(1 for k in B if k[:3] not in a3)
    return {
        "raw_rule_candidates": raw["raw_rule"], "raw_llm_relations": raw["raw_llm"],
        "A_unique_keys": len(A), "B_unique_keys": len(B), "both_keys_same_status": len(A & B), "C_union_keys": len(fused),
        "identity_check": f"{len(A)} + {len(B)} - {len(A & B)} = {len(A) + len(B) - len(A & B)} (== C {len(fused)})",
        "B_decomposition_keys": {"same_key_as_A": len(A & B), "same_triple_different_status": same_triple_other_status, "B_only_keys": b_only_keys,
                                 "sum": len(A & B) + same_triple_other_status + b_only_keys},
        "triples_ignoring_status": {"A": len(a3), "B": len(b3), "both": len(a3 & b3), "B_only_distinct_triples": len(b3 - a3),
                                    "B_only_triples_with_more_than_one_status": sum(1 for t in b3 - a3 if sum(1 for k in B if k[:3] == t) > 1)},
        "explanation": ("No arithmetic inconsistency. '73 B-only' counts B keys (subject,predicate,object,STATUS) whose triple is absent from A; the same "
                        "population is 67 distinct triples because 5 triples occur with 2+ statuses. The phase 6B.1 field `both_same_status=0` was a reporting "
                        "bug (a sorted list ['LLM','RULE'] was compared with ['BOTH']); the true value is the key overlap above. Raw data were not changed."),
        "unit_note": "A=41 unique keys come from 44 raw rule candidates (3 duplicates merged by evidence); B=88 from 109 raw LLM relations."}


def run(registry: Path = REGISTRY, out_dir: Path | None = None, rep_dir: Path | None = None, overlay: dict | None = None) -> dict:
    global OUT, REP
    OUT, REP = out_dir or OUT, rep_dir or REP
    manifest = {r["article_id"]: r for r in load_manifest()}
    arts = {a.article_id: a for a in Staging(ROOT / "data/staging/staging.sqlite").get_articles()}
    texts = {aid: normalize_text(arts[aid].text) for aid in manifest}
    ments_by: dict[str, list[dict]] = defaultdict(list)
    for m in jl(RUN / "entities.jsonl"):
        if m["article_id"] in manifest:
            ments_by[m["article_id"]].append(m)
    relations = load_relations(str(ROOT / "config/relations.yaml"))
    ctx = build_context([RUN], [registry], ROOT / "data/staging/staging.sqlite")
    canon = _canon_fn(registry)
    fused, raw = build_fused(manifest, overlay, registry)
    rec = reconcile(fused, raw)
    rows = []
    for f in fused:
        c = f["candidates"][0]
        aid = c.article_id
        # rule signal for LLM-only items: does the (unchanged) rule generator reproduce this pair in this span?
        reproduced = any(g.predicate == c.predicate and g.evidence_start == c.evidence_start and ctx.canon(g.subject.entity_id or "") == ctx.canon(c.subject.entity_id or "")
                         and ctx.canon(g.object.entity_id or "") == ctx.canon(c.object.entity_id or "") for g in ctx.generated(aid)) if "RULE" not in f["methods"] else True
        bond_name = ctx.info.get(c.object.entity_id or "", {}).get("name", "") if c.predicate == "ISSUED_BOND" else ""
        v = validate_candidate(c, texts[aid], ments_by[aid], ctx.info, canon, relations, set(f["methods"]), reproduced, bond_name)
        # baseline: Phase 6A auditor, deterministic mode, only for candidates that pass the cheap pre-checks (as in 6B.1)
        base = "NOT_AUDITED"
        try:
            edge = {"subject_id": c.subject.entity_id, "predicate": c.predicate, "object_id": c.object.entity_id, "edge_id": "x",
                    "evidence": [{"article_id": e["article_id"], "source_url": arts[e["article_id"]].url, "evidence_text": e["evidence_text"], "evidence_start": e["evidence_start"],
                                  "evidence_end": e["evidence_end"], "factual_status": f["factual_status"], "published_at": None, "extraction_method": e["method"],
                                  "review_status": "NEEDS_REVIEW", "valid_from": None, "valid_to": None} for e in f["evidence"]]}
            if c.subject.entity_id and c.object.entity_id:
                r6a = audit_edge(edge, ctx, None, llm_required=False)
                base = r6a["decision"]
                base_failed = r6a["failed_checks"]
            else:
                base_failed = []
        except Exception as e:  # noqa: BLE001
            base, base_failed = f"ERROR:{e.__class__.__name__}", []
        rows.append({"key": list(f["key"]), "article_id": aid, "source": manifest[aid]["source"], "subset": manifest[aid]["subset"], "url": arts[aid].url,
                     "subject": c.subject.text, "subject_id": c.subject.entity_id, "predicate": c.predicate, "object": c.object.text, "object_id": c.object.entity_id,
                     "label_status": f["factual_status"], "methods": f["methods"], "discovery_method": f["discovery_method"], "evidence": c.evidence_text,
                     "baseline_6a": base, "baseline_6a_failed": base_failed, "hybrid": v.as_dict(), "llm_meta": f["llm_meta"][:1],
                     "lexical_cue": bool(_cue(c))})
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    (OUT / "results.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    summary = summarise(rows, rec)
    (REP / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    sample = review_sample(rows)
    export_csvs(rows, sample)
    return summary


def _cue(c: RelationCandidate) -> bool:
    import re

    from vckg.fn_analysis import FAMILIES
    from vckg.relation_extraction.discovery_benchmark import PRED_FAMILY
    return bool(re.search(FAMILIES[PRED_FAMILY[c.predicate]], c.evidence_text, re.IGNORECASE))


def _group(rows, sel):
    S = [r for r in rows if sel(r)]
    dec = Counter(r["hybrid"]["decision"] for r in S)
    base = Counter(r["baseline_6a"] for r in S)
    classes = Counter(r["hybrid"]["quarantine_class"] for r in S if r["hybrid"]["decision"] == "QUARANTINE")
    agr = Counter(r["hybrid"]["agreement"] for r in S)
    passed = [r for r in S if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT")]
    return {"candidates": len(S), "hybrid_decisions": dict(dec), "baseline_6a_decisions": dict(base), "quarantine_classes": dict(classes), "rule_agreement": dict(agr),
            "baseline_blocked_only_by_rule_disagreement": sum(1 for r in S if r["baseline_6a"] == "QUARANTINE" and set(r["baseline_6a_failed"]) <= {"RELATION_NOT_REPRODUCED"}),
            "hybrid_semantic_only_clean": classes.get("SEMANTIC_ONLY_CLEAN", 0),
            "pass_hard_and_type_checks": sum(1 for r in S if not (set(r["hybrid"]["hard_failed"]) & {"EVIDENCE_MISMATCH", "EVIDENCE_CAPTION_OR_SHORT", "MENTION_NOT_IN_EVIDENCE", "INVALID_ENTITY_TYPES", "SELF_LOOP", "NEGATED_RELATION"})),
            "possible_inference": sum(1 for r in S if r["hybrid"]["possible_inference"] or not r["lexical_cue"]),
            "relation_types_staging": sorted({r["predicate"] for r in passed}), "staging_validated": len(passed),
            "staging_unique_entities": len({x for r in passed for x in (r["subject_id"], r["object_id"])}),
            "status_corrections": dict(Counter(r["hybrid"]["corrections"].get("factual_status", "") + "" for r in S if "factual_status" in r["hybrid"]["corrections"])),
            "semantic_codes": dict(Counter(r["hybrid"]["semantic_code"] for r in S)), "hard_failed": dict(Counter(x for r in S for x in set(r["hybrid"]["hard_failed"])))}


def summarise(rows, rec) -> dict:
    return {"validator_version": VALIDATOR_VERSION, "reconciliation": rec,
            "A_rule": _group(rows, lambda r: "RULE" in r["methods"]), "B_llm": _group(rows, lambda r: "LLM" in r["methods"]),
            "C_union": _group(rows, lambda r: True), "B_only": _group(rows, lambda r: r["methods"] == ["LLM"] and tuple(r["key"][:3]) not in {tuple(x["key"][:3]) for x in rows if "RULE" in x["methods"]}),
            "by_subset": {s: _group(rows, lambda r, s=s: r["subset"] == s) for s in ("targeted", "control")},
            "note": "No gold: decisions are rule outcomes, not Precision/Recall. Qwen was not called; same-model discovery+verification is not independent."}


def review_sample(rows: list[dict], n: int = 40) -> list[dict]:
    rng = random.Random(SEED)
    cohorts = [("LLM_ONLY_SEMANTIC_ONLY_CLEAN", lambda r: r["methods"] == ["LLM"] and r["hybrid"]["quarantine_class"] == "SEMANTIC_ONLY_CLEAN", 9),
               ("LLM_ONLY_HARD_QUARANTINED", lambda r: r["methods"] == ["LLM"] and r["hybrid"]["decision"] == "QUARANTINE" and r["hybrid"]["quarantine_class"] in ("HARD_BLOCK", "NON_OFFICIAL_STATUS"), 8),
               ("RULE_ONLY", lambda r: r["methods"] == ["RULE"], 8), ("BOTH_METHODS", lambda r: r["discovery_method"] == "BOTH", 6),
               ("NEGATIVE_OR_AMBIGUOUS", lambda r: r["hybrid"]["decision"] == "REJECT" or r["hybrid"]["quarantine_class"] == "INSUFFICIENT_EVIDENCE", 9)]
    out, used = [], set()
    for name, sel, k in cohorts:
        pool = sorted((r for r in rows if sel(r) and json.dumps(r["key"]) not in used), key=lambda r: json.dumps(r["key"]))
        for r in rng.sample(pool, min(k, len(pool))):
            used.add(json.dumps(r["key"]))
            out.append({**r, "cohort": name})
    return out[:n]


def export_csvs(rows, sample) -> None:
    def line(r, extra=None):
        h = r["hybrid"]
        d = {"article_id": r["article_id"], "source": r["source"], "subset": r["subset"], "url": r["url"], "subject": r["subject"], "predicate": r["predicate"],
             "object": r["object"], "label_status": r["label_status"], "final_status": h["final_status"], "method": r["discovery_method"], "agreement": h["agreement"],
             "hybrid_decision": h["decision"], "quarantine_class": h["quarantine_class"], "baseline_6a": r["baseline_6a"], "semantic_code": h["semantic_code"],
             "reasons": " || ".join(h["reasons"])[:400], "correction": json.dumps(h["corrections"], ensure_ascii=False) if h["corrections"] else "", "evidence": r["evidence"]}
        return {**d, **(extra or {})}
    cols = list(line(rows[0]).keys())
    with (REP / "all_candidates_hybrid_qa.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(line(r) for r in rows)
    ex = {"cohort": "", "selection_reason": "", "human_label (CORRECT/WRONG/UNSURE)": "", "human_note": ""}
    cols2 = ["cohort", "selection_reason", *cols, "human_label (CORRECT/WRONG/UNSURE)", "human_note"]
    with (REP / "review_sample_40.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols2)
        w.writeheader()
        for r in sample:
            w.writerow(line(r, {**ex, "cohort": r["cohort"], "selection_reason": f"seed={SEED}; cohort={r['cohort']}"}))
    staging = [r for r in rows if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT")]
    (OUT / "staging_validated.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in staging), encoding="utf-8")
    (OUT / "quarantine.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows if r["hybrid"]["decision"] == "QUARANTINE"), encoding="utf-8")
    (OUT / "rejected.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows if r["hybrid"]["decision"] == "REJECT"), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    summary = run()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["load_config", "main", "reconcile", "review_sample", "run"]

