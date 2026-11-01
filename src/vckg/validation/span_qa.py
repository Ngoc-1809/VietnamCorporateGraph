"""Phase 6B.4 runner: diagnose truncated spans on the 60 articles, recover them safely (staging only), re-ground identities, re-run the
UNCHANGED hybrid QA and compare with the Phase 6B.3 configuration. Deterministic; no Qwen/NER inference, no crawl, no production writes.
  python -m vckg.validation.span_qa [--fresh]       Outputs: data/experiments/phase6b/span_recovery/, reports/phase6b/span_recovery/"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import Counter

from vckg.entity_linking.article_grounding import _truncated, ground_article, overlay_from
from vckg.entity_linking.store import RegistryStore
from vckg.models import EntityType, ResolutionStatus
from vckg.ner.span_recovery import SpanFix, recover_article
from vckg.relation_extraction.discovery_benchmark import EXP, REGISTRY, ROOT
from vckg.storage.sqlite import Staging
from vckg.validation import grounding_qa, hybrid_qa

OUT = EXP / "span_recovery"
REP = ROOT / "reports/phase6b/span_recovery"
G63 = EXP / "grounding"
REG64 = OUT / "registry_p6b4_staging.sqlite"


def flagged_heads(text: str, mentions: list[dict]) -> list[dict]:
    heads = [m for m in mentions if m.get("alias_of") is None and not str(m.get("linking_method", "")).startswith("out_of_scope") and m["label"] != "PERSON"]
    return [m for m in heads if _truncated(text, m)]


def corrected_mentions(text: str, mentions: list[dict], fixes: list[SpanFix], store: RegistryStore, article_id: str) -> tuple[list[dict], dict]:
    """Apply EXTEND fixes (non-overlapping, left to right). Returns (mentions, {original_span: new_mention_dict})."""
    ext = sorted((f for f in fixes if f.kind == "EXTEND"), key=lambda f: f.original)
    taken: list[tuple[int, int]] = []
    keep: list[SpanFix] = []
    for f in ext:
        if any(f.new[0] < b and a < f.new[1] for a, b in taken):
            continue
        taken.append(f.new)
        keep.append(f)
    drop = {f.original for f in keep} | {a for f in keep for a in f.absorbed}
    out = [m for m in mentions if (m["start"], m["end"]) not in drop]
    new_by_orig: dict[tuple[int, int], dict] = {}
    for f in keep:
        orig = next(m for m in mentions if (m["start"], m["end"]) == f.original)
        label = "BANK" if f.new_text.lower().startswith("ngân hàng") else ("ORGANIZATION" if orig["label"] == "BANK" else orig["label"])
        same = [m for m in mentions if m["text"] == f.new_text and m["label"] != "PERSON" and m.get("entity_id")]
        if same:
            eid = same[0]["entity_id"]
        else:
            eid, _ = store.add_entity(f.new_text, EntityType(label), status=ResolutionStatus.PROVISIONAL, source_type="article")
        nm = {**orig, "start": f.new[0], "end": f.new[1], "text": f.new_text, "label": label, "entity_id": eid, "method": "span_recovery",
              "linking_method": "span_recovery", "link_status": "provisional"}
        out.append(nm)
        new_by_orig[f.original] = nm
        for a in f.absorbed:
            new_by_orig[a] = nm
    out.sort(key=lambda m: (m["start"], m["end"]))
    return out, new_by_orig


def final_ids(mentions_by_art: dict, overlay: dict) -> dict:
    res = {}
    for aid, ms in mentions_by_art.items():
        for m in ms:
            v = overlay.get(f"{aid}|{m['start']}|{m['end']}")
            res[(aid, m["start"], m["end"])] = v["entity_id"] if isinstance(v, dict) else (v or m.get("entity_id"))
    return res


def run(fresh: bool = False) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    manifest, texts, ments = grounding_qa.load_world()
    arts = {a.article_id: a for a in Staging(ROOT / "data/staging/staging.sqlite").get_articles()}
    overlay63 = json.loads((G63 / "overlay.json").read_text(encoding="utf-8"))
    reg63 = G63 / "registry_p6b3_staging.sqlite"
    # ---- before: exactly the Phase 6B.3 configuration, re-run with the current code for comparable per-candidate keys
    hybrid_qa.run(registry=reg63, out_dir=OUT / "before_6b3", rep_dir=REP / "before_6b3", overlay=overlay63)
    # ---- diagnostics + recovery on the BASELINE mentions
    if fresh or not REG64.exists():
        shutil.copy(REGISTRY, REG64)
    store = RegistryStore(REG64)
    all_fixes: dict[str, list[SpanFix]] = {}
    n_flag_before = 0
    for aid in manifest:
        n_flag_before += len(flagged_heads(texts[aid], ments[aid]))
        all_fixes[aid] = recover_article(aid, texts[aid], ments[aid], _truncated)
    fix_rows = [f for fs in all_fixes.values() for f in fs]
    (OUT / "fixes.jsonl").write_text("\n".join(json.dumps(f.as_dict(), ensure_ascii=False) for f in fix_rows), encoding="utf-8")
    new_ments, new_by_orig_all, complete = {}, {}, {}
    for aid in manifest:
        new_ments[aid], new_by_orig_all[aid] = corrected_mentions(texts[aid], ments[aid], all_fixes[aid], store, aid)
        complete[aid] = {f.original for f in all_fixes[aid] if f.kind == "CONFIRMED_COMPLETE"}
    n_flag_after = sum(len([m for m in flagged_heads(texts[aid], new_ments[aid]) if (m["start"], m["end"]) not in complete[aid]]) for aid in manifest)
    # ---- re-ground on the corrected mentions (staging registry), build the overlay
    decisions = []
    for aid in manifest:
        decisions += ground_article(store, aid, texts[aid], new_ments[aid], apply=True, confirmed_complete=complete[aid])
    store.db.commit()
    resolve = overlay_from(decisions)
    overlay64: dict = {k: v for k, v in resolve.items()}
    for aid, mp in new_by_orig_all.items():
        for orig, nm in mp.items():
            tgt = resolve.get(f"{aid}|{nm['start']}|{nm['end']}") or nm["entity_id"]
            overlay64[f"{aid}|{orig[0]}|{orig[1]}"] = {"start": nm["start"], "end": nm["end"], "text": nm["text"], "label": nm["label"], "entity_id": tgt}
    (OUT / "overlay_span_recovery.json").write_text(json.dumps(overlay64, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "decisions.jsonl").write_text("\n".join(json.dumps(d.as_dict(), ensure_ascii=False) for d in decisions), encoding="utf-8")
    summary = hybrid_qa.run(registry=REG64, out_dir=OUT / "after", rep_dir=REP / "after", overlay=overlay64)
    hybrid_qa.OUT, hybrid_qa.REP = EXP / "hybrid_qa", ROOT / "reports/phase6b/hybrid_qa"
    # ---- compare
    before = [json.loads(x) for x in (OUT / "before_6b3/results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    after = [json.loads(x) for x in (OUT / "after/results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    cmp = compare(before, after, fix_rows, all_fixes, ments, overlay63, overlay64, store, reg63, n_flag_before, n_flag_after, manifest, texts, arts, summary)
    (REP / "comparison.json").write_text(json.dumps(cmp, ensure_ascii=False, indent=2, default=list), encoding="utf-8")
    write_diagnostics(all_fixes, ments, texts, arts, before)
    return cmp


def _okey(r):
    o = r.get("orig_spans")
    return (r["article_id"], r["predicate"], r["label_status"], tuple(o) if o else None, r["evidence"][:60])


def compare(before, after, fix_rows, all_fixes, ments, ov63, ov64, store, reg63, nfb, nfa, manifest, texts, arts, summary) -> dict:
    ab = {_okey(r): r for r in after}
    fixed_orig = {(f.article_id, f.original): f for f in fix_rows if f.kind in ("EXTEND", "CONFIRMED_COMPLETE")}
    twelve_spans = {(d["article_id"], d["start"], d["end"]) for d in map(json.loads, (G63 / "promotions.jsonl").read_text(encoding="utf-8").splitlines())
                    if d["action"] == "KEEP" and d["reason"] == "NER_TRUNCATED"}
    target = []
    for r in before:
        o = r.get("orig_spans")
        if not o:
            continue
        aid = r["article_id"]
        if (aid, (o[0], o[1])) in fixed_orig or (aid, (o[2], o[3])) in fixed_orig:
            target.append(r)
    twelve = [r for r in before if r.get("orig_spans") and r["hybrid"]["quarantine_class"] == "HARD_BLOCK"
              and set(r["hybrid"]["hard_failed"]) <= {"IDENTITY_NOT_GROUNDED"}
              and ((r["article_id"], r["orig_spans"][0], r["orig_spans"][1]) in twelve_spans or (r["article_id"], r["orig_spans"][2], r["orig_spans"][3]) in twelve_spans)]
    twelve_tr = Counter()
    for r in twelve:
        n = ab.get(_okey(r))
        twelve_tr[(r["hybrid"]["decision"], (n["hybrid"]["decision"] + "/" + (n["hybrid"]["quarantine_class"] or "-") + ("/" + ",".join(n["hybrid"]["hard_failed"][:2]) if n["hybrid"]["hard_failed"] else "")) if n else "MERGED")] += 1
    trans = Counter()
    resolved_span = 0
    for r in target:
        n = ab.get(_okey(r))
        trans[(r["hybrid"]["decision"] + "/" + (r["hybrid"]["quarantine_class"] or "-"), (n["hybrid"]["decision"] + "/" + (n["hybrid"]["quarantine_class"] or "-")) if n else "MERGED")] += 1
        if n and "SPAN_BOUNDARY_SUSPECT" not in n["hybrid"]["hard_failed"] and "IDENTITY_NOT_GROUNDED" not in n["hybrid"]["hard_failed"]:
            resolved_span += 1
    dec = lambda rows: dict(Counter(r["hybrid"]["decision"] for r in rows))
    pm = lambda rows: dict(Counter(("BOTH" if r["discovery_method"] == "BOTH" else r["discovery_method"] + "_ONLY") for r in rows if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT")))
    # non-target candidates must not change decision
    other = Counter()
    tkeys = {_okey(r) for r in target}
    for r in before:
        if _okey(r) in tkeys:
            continue
        n = ab.get(_okey(r))
        other[(r["hybrid"]["decision"], n["hybrid"]["decision"] if n else "MERGED")] += 1
    # entity-level safety: mentions that were grounded in 6B.3 and not touched by a span fix must keep their entity id
    st63 = RegistryStore(reg63)
    f63, f64 = final_ids(ments, ov63), final_ids(ments, ov64)
    touched = {(f.article_id, f.original[0], f.original[1]) for f in fix_rows if f.kind == "EXTEND"} | {(f.article_id, a[0], a[1]) for f in fix_rows if f.kind == "EXTEND" for a in f.absorbed}
    _changed_ok, changed_other = [], []
    for k, v in f63.items():
        if v is None or k in touched:
            continue
        s = st63.get_entity(v)
        if s and s["resolution_status"] in ("VERIFIED", "ARTICLE_GROUNDED") and f64.get(k) != v:
            changed_other.append({"mention": list(k), "before": v, "after": f64.get(k)})
    new_collisions = {"self_loops": sum(1 for r in after if r["subject_id"] and r["subject_id"] == r["object_id"]),
                      "extended_spans_resolved_to_existing_entity_of_other_name": 0}
    kinds = Counter((f.kind, f.cause) for f in fix_rows)
    ext = [f for f in fix_rows if f.kind == "EXTEND"]
    return {"flagged_truncated_mentions_before": nfb, "flagged_truncated_mentions_after": nfa,
            "fix_kinds": {f"{k[0]}:{k[1]}": v for k, v in kinds.items()}, "extend_fixes": len(ext),
            "extend_examples": [{"article_id": f.article_id, "original": f.original_text, "new": f.new_text, "evidence": f.evidence, "cause": f.cause} for f in ext][:15],
            "twelve_span_blocked_candidates": len(twelve), "twelve_outcomes_after": {f"{a} -> {b}": v for (a, b), v in twelve_tr.items()},
            "target_candidates": len(target), "target_resolved_span_and_identity": resolved_span,
            "target_transitions": {f"{a} -> {b}": v for (a, b), v in trans.items()},
            "decisions_before": dec(before), "decisions_after": dec(after), "pass_by_method_before": pm(before), "pass_by_method_after": pm(after),
            "non_target_transitions": {f"{a} -> {b}": v for (a, b), v in other.items()},
            "previously_grounded_mentions_whose_entity_changed": len(changed_other), "changed_examples": changed_other[:10],
            "new_collisions": new_collisions,
            "staging_before": staging_stats(before), "staging_after": staging_stats(after),
            "hard_failed_after": summary["C_union"]["hard_failed"], "note": "More PASS is not evidence of higher accuracy; no gold exists."}


def staging_stats(rows) -> dict:
    p = [r for r in rows if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT")]
    return {"validated": len(p), "unique_entities": len({x for r in p for x in (r["subject_id"], r["object_id"])}), "relation_types": sorted({r["predicate"] for r in p})}


def write_diagnostics(all_fixes, ments, texts, arts, before) -> None:
    cand_ep = {}
    for r in before:
        o = r.get("orig_spans")
        if o and r["hybrid"]["quarantine_class"] == "HARD_BLOCK":
            for span in ((o[0], o[1]), (o[2], o[3])):
                cand_ep.setdefault((r["article_id"], span), []).append(r["predicate"])
    rows = []
    for aid, fs in all_fixes.items():
        t = texts[aid]
        for f in fs:
            rows.append({"article_id": aid, "url": arts[aid].url, "original_text": f.original_text, "original_span": f"{f.original[0]}-{f.original[1]}",
                         "context": t[max(0, f.original[0] - 40):f.original[1] + 50].replace("\n", " "), "kind": f.kind, "cause": f.cause,
                         "new_text": f.new_text, "new_span": f"{f.new[0]}-{f.new[1]}" if f.new else "", "evidence": f.evidence, "reason": f.reason,
                         "safe_rule_fix": f.kind == "EXTEND", "candidates_using_this_endpoint": len(cand_ep.get((aid, f.original), []))})
    with (REP / "span_diagnostics.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["article_id"])
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    fresh = "--fresh" in (argv if argv is not None else sys.argv[1:])
    print(json.dumps(run(fresh), ensure_ascii=False, indent=2, default=list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
