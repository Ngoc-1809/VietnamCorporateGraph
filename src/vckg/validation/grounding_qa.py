"""Phase 6B.3 runner: analyse why 53 candidates are blocked only by IDENTITY_NOT_GROUNDED, apply article grounding on a STAGING registry
copy, re-run the (unchanged) hybrid QA on the same 60 articles and compare. Deterministic; no Qwen, no crawl, no production writes.
  python -m vckg.validation.grounding_qa [--fresh]
Outputs: data/experiments/phase6b/grounding/ , reports/phase6b/grounding/"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import Counter, defaultdict

from vckg.entity_linking.article_grounding import ground_article, overlay_from
from vckg.entity_linking.store import RegistryStore
from vckg.preprocessing.text import normalize_text
from vckg.relation_extraction.discovery_benchmark import EXP, REGISTRY, ROOT, RUN, jl, load_manifest
from vckg.storage.sqlite import Staging
from vckg.validation import hybrid_qa

GROUND = EXP / "grounding"
REP = ROOT / "reports/phase6b/grounding"
STAGING_REG = GROUND / "registry_p6b3_staging.sqlite"
BASE_RESULTS = EXP / "hybrid_qa/results.jsonl"


def blocked_53(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["hybrid"]["decision"] == "QUARANTINE" and r["hybrid"]["quarantine_class"] == "HARD_BLOCK"
            and set(r["hybrid"]["hard_failed"]) <= {"IDENTITY_NOT_GROUNDED"} and r["hybrid"]["semantic"] == "OK"]


def load_world():
    manifest = {r["article_id"]: r for r in load_manifest()}
    arts = {a.article_id: a for a in Staging(ROOT / "data/staging/staging.sqlite").get_articles()}
    texts = {aid: normalize_text(arts[aid].text) for aid in manifest}
    ments: dict[str, list[dict]] = defaultdict(list)
    for m in jl(RUN / "entities.jsonl"):
        if m["article_id"] in manifest:
            ments[m["article_id"]].append(m)
    return manifest, texts, ments


def endpoint_causes(fused_53: list[dict], decisions: dict[tuple, dict], store: RegistryStore) -> list[dict]:
    """Per blocked endpoint: cause category (dry-run decisions of the new rules, i.e. what the article evidence allows)."""
    rows = []
    for f in fused_53:
        c = f["candidates"][0]
        for role in ("subject", "object"):
            m = getattr(c, role)
            st = "UNRESOLVED" if not m.entity_id else (store.get_entity(m.entity_id)["resolution_status"] if store.get_entity(m.entity_id) else "UNRESOLVED")
            if st in ("VERIFIED", "ARTICLE_GROUNDED"):
                continue
            d = decisions.get((c.article_id, m.start, m.end))
            if m.label.value == "BOND_ISSUE":
                cat = "BOND_NOT_SPECIFIC"
            elif d is None:
                cat = "NOT_ANALYSED"
            elif d["action"] == "PROMOTE":
                cat = "PERSON_FULL_NAME_WITH_ROLE_OR_ORG" if m.label.value == "PERSON" else "ORG_FULL_LEGAL_NAME_NO_REGISTRY"
            elif d["action"] == "RESOLVE_TO":
                cat = "ORG_SHORT_NAME_WITH_FULL_NAME_IN_ARTICLE"
            else:
                cat = {"SHORT_PERSON_NAME": "PERSON_SHORT_OR_AMBIGUOUS", "NER_TRUNCATED": "NER_SPAN_TRUNCATED", "GENERIC_NAME": "GENERIC_OR_OUT_OF_DOMAIN",
                       "GENERIC_OR_UNPROVEN_SHORT_NAME": "GENERIC_OR_OUT_OF_DOMAIN", "NO_FULL_NAME_IN_ARTICLE": "UNLISTED_ORG_NO_IDENTITY_SOURCE",
                       "NO_LEGAL_FORM": "UNLISTED_ORG_NO_IDENTITY_SOURCE", "NO_PROPER_TOKEN": "GENERIC_OR_OUT_OF_DOMAIN"}.get(d["reason"], "OTHER_AMBIGUOUS:" + d["reason"])
            rows.append({"article_id": c.article_id, "predicate": c.predicate, "role": role, "mention": m.text, "label": m.label.value, "entity_id": m.entity_id or "",
                         "entity_status": st, "cause": cat, "rule_decision": d["action"] if d else "", "rule_reason": (d["reason"] or d["method"]) if d else "",
                         "methods": "+".join(f["methods"])})
    return rows


def collision_report(decisions: list[dict], store_base: RegistryStore, store_new: RegistryStore, rows_after: list[dict]) -> dict:
    """Identity collision / false-merge risk checks on the applied decisions."""
    risks = []
    ent = store_new.db.execute("SELECT entity_id, canonical_name, entity_type FROM entities WHERE merged_into IS NULL").fetchall()
    from vckg.entity_linking.article_grounding import core_tokens
    cores = {e["entity_id"]: core_tokens(e["canonical_name"]) for e in ent if e["entity_type"] != "PERSON"}
    for d in decisions:
        if d["action"] != "RESOLVE_TO":
            continue
        toks = core_tokens(d["text"])
        others = sorted(eid for eid, ct in cores.items() if eid != d["resolved_entity_id"] and len(ct) > len(toks) and (ct[:len(toks)] == toks or ct[-len(toks):] == toks))
        if others:
            risks.append({"article_id": d["article_id"], "mention": d["text"], "resolved_to": d["resolved_entity_id"], "other_registry_entities_containing_name": others[:6]})
    promoted_same_key = defaultdict(set)
    for d in decisions:
        if d["action"] == "PROMOTE" and d["label"] != "PERSON":
            promoted_same_key[d["resolved_entity_id"]].add(d["article_id"])
    person_cross = [d for d in decisions if d["action"] == "PROMOTE" and d["label"] == "PERSON" and not d["resolved_entity_id"].endswith(d["article_id"])]
    self_loops = [r for r in rows_after if r["subject_id"] and r["subject_id"] == r["object_id"]]
    return {"resolve_to_with_other_registry_entities_containing_the_short_name": risks, "n_risk": len(risks),
            "org_entities_promoted_and_shared_by_several_articles": {k: sorted(v) for k, v in promoted_same_key.items() if len(v) > 1},
            "person_promotions_not_article_scoped": len(person_cross), "self_loops_after_overlay": len(self_loops),
            "cross_article_person_merges": 0}


def run(fresh: bool = False) -> dict:
    GROUND.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    manifest, texts, ments = load_world()
    base_rows = [json.loads(x) for x in BASE_RESULTS.read_text(encoding="utf-8").splitlines() if x.strip()]
    b53 = blocked_53(base_rows)
    b53_keys = {json.dumps(r["key"]) for r in b53}
    # --- 1. dry-run analysis on an untouched copy of the baseline registry
    if fresh or not STAGING_REG.exists():
        shutil.copy(REGISTRY, STAGING_REG)
    dry_path = GROUND / "registry_dry.sqlite"
    shutil.copy(REGISTRY, dry_path)
    dry = RegistryStore(dry_path)
    dry_dec: dict[tuple, dict] = {}
    for aid in manifest:
        for d in ground_article(dry, aid, texts[aid], ments[aid], apply=False):
            dry_dec[(aid, d.start, d.end)] = d.as_dict()
    fused, _raw = hybrid_qa.build_fused(manifest)
    fused_53 = [f for f in fused if json.dumps(list(f["key"])) in b53_keys]
    causes = endpoint_causes(fused_53, dry_dec, dry)
    prio = ["NER_SPAN_TRUNCATED", "PERSON_SHORT_OR_AMBIGUOUS", "GENERIC_OR_OUT_OF_DOMAIN", "BOND_NOT_SPECIFIC", "UNLISTED_ORG_NO_IDENTITY_SOURCE"]
    by_c = defaultdict(list)
    for r in causes:
        by_c[(r["article_id"], r["predicate"], r.get("methods", ""))].append(r)
    cand_counts = Counter()
    for f in fused_53:
        c = f["candidates"][0]
        cs = [r["cause"] for r in causes if r["article_id"] == c.article_id and r["predicate"] == c.predicate and r["mention"] in (c.subject.text, c.object.text)]
        cs = sorted(set(cs), key=lambda x: (prio.index(x) if x in prio else 99))
        cand_counts[cs[0] if cs else "UNKNOWN"] += 1
    ana = {"candidates_blocked_only_by_identity": len(b53), "fused_matched": len(fused_53),
           "endpoint_causes": dict(Counter(r["cause"] for r in causes)), "candidate_primary_cause": dict(cand_counts),
           "note": "Dry-run of the grounding rules on the BASELINE registry; categories describe what the article evidence allows, nothing was changed yet."}
    (REP / "identity_cause_analysis.json").write_text(json.dumps(ana, ensure_ascii=False, indent=2), encoding="utf-8")
    with (REP / "identity_blocked_endpoints.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(causes[0].keys()))
        w.writeheader()
        w.writerows(causes)
    # --- 2. apply on the staging copy (idempotent: re-running changes nothing)
    store = RegistryStore(STAGING_REG)
    all_dec, promoted = [], 0
    for aid in manifest:
        ds = ground_article(store, aid, texts[aid], ments[aid], apply=True)
        all_dec += ds
    promoted = sum(1 for d in all_dec if d.action == "PROMOTE")
    prom = [d.as_dict() for d in all_dec]
    (GROUND / "promotions.jsonl").write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in prom), encoding="utf-8")
    overlay = overlay_from(all_dec)
    (GROUND / "overlay.json").write_text(json.dumps(overlay, ensure_ascii=False, indent=1), encoding="utf-8")
    store.db.commit()
    # --- 3. re-run the unchanged hybrid QA with grounded registry + overlay
    out_dir, rep_dir = GROUND / "hybrid_qa", REP / "hybrid_qa"
    summary = hybrid_qa.run(registry=STAGING_REG, out_dir=out_dir, rep_dir=rep_dir, overlay=overlay)
    hybrid_qa.OUT, hybrid_qa.REP = EXP / "hybrid_qa", ROOT / "reports/phase6b/hybrid_qa"  # restore globals
    new_rows = [json.loads(x) for x in (out_dir / "results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    cmp = compare(base_rows, new_rows, b53, prom, ana)
    cmp["collisions"] = collision_report(prom, dry, store, new_rows)
    cmp["summary_after"] = {k: summary[k] for k in ("A_rule", "B_llm", "C_union", "B_only")}
    (REP / "comparison.json").write_text(json.dumps(cmp, ensure_ascii=False, indent=2, default=list), encoding="utf-8")
    cmp["promotions_applied_this_run"] = promoted
    return cmp


def _sig(r: dict) -> tuple:
    return (r["article_id"], r["subject"], r["predicate"], r["object"], r["label_status"])


def compare(base: list[dict], new: list[dict], b53: list[dict], prom: list[dict], ana: dict) -> dict:
    nb = {_sig(r): r for r in new}
    {_sig(r) for r in b53}
    trans = Counter()
    pass_by_method = {"before": Counter(), "after": Counter()}
    for tag, rows in (("before", base), ("after", new)):
        for r in rows:
            if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT"):
                pass_by_method[tag]["BOTH" if r["discovery_method"] == "BOTH" else r["discovery_method"] + "_ONLY"] += 1
    b53_ids = {_sig(r) for r in b53}
    other_tr = Counter()
    for r in base:
        if _sig(r) in b53_ids:
            continue
        n = nb.get(_sig(r))
        other_tr[(r["hybrid"]["decision"], n["hybrid"]["decision"] if n else "MISSING")] += 1
    moved = []
    for r in b53:
        n = nb.get(_sig(r))
        after = (n["hybrid"]["decision"], n["hybrid"]["quarantine_class"]) if n else ("MISSING", "")
        trans[(r["hybrid"]["decision"], after[0], after[1])] += 1
        if n and n["hybrid"]["decision"] == "PASS":
            moved.append({"article_id": r["article_id"], "url": r["url"], "predicate": r["predicate"], "subject": r["subject"], "object": r["object"], "methods": r["methods"], "evidence": r["evidence"][:220]})
    action = Counter(d["action"] for d in prom)
    methods = Counter(d["method"] for d in prom if d["action"] != "KEEP")
    resolved_eps = {(d["article_id"], d["start"], d["end"]) for d in prom if d["action"] in ("PROMOTE", "RESOLVE_TO")}
    n_resolved = n_ambig = 0
    for r in b53:
        n = nb.get(_sig(r))
        if n and "IDENTITY_NOT_GROUNDED" not in n["hybrid"]["hard_failed"] and "IDENTITY_SHORT_PERSON_NAME" not in n["hybrid"]["hard_failed"]:
            n_resolved += 1
        else:
            n_ambig += 1
    keep_reasons = Counter(d["reason"] for d in prom if d["action"] == "KEEP")
    def dec(rows):
        return dict(Counter(r["hybrid"]["decision"] for r in rows))
    passed_after = [r for r in new if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT")]
    return {"blocked_53": len(b53), "resolved_identity_of_53": n_resolved, "still_identity_blocked_of_53": n_ambig,
            "of_53_transitions": {f"{k[0]} -> {k[1]} ({k[2]})": v for k, v in trans.items()}, "of_53_now_pass": len(moved), "newly_passing_examples": moved,
            "decisions_before_C": dec(base), "decisions_after_C": dec(new),
            "pass_by_method": {k: dict(v) for k, v in pass_by_method.items()},
            "non53_transitions": {f"{k[0]} -> {k[1]}": v for k, v in other_tr.items()},
            "grounding_actions": dict(action), "grounding_methods": dict(methods), "keep_reasons": dict(keep_reasons),
            "staging_after": {"validated": len(passed_after), "unique_entities": len({x for r in passed_after for x in (r["subject_id"], r["object_id"])}),
                              "relation_types": sorted({r["predicate"] for r in passed_after})},
            "staging_before": {"validated": sum(1 for r in base if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT")),
                               "unique_entities": len({x for r in base if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT") for x in (r["subject_id"], r["object_id"])}),
                               "relation_types": sorted({r["predicate"] for r in base if r["hybrid"]["decision"] in ("PASS", "AUTO_CORRECT")})},
            "unmatched_candidates_after": sum(1 for r in b53 if _sig(r) not in nb), "resolved_spans": len(resolved_eps),
            "note": "More PASS is not evidence of higher accuracy: no gold exists."}


def main(argv: list[str] | None = None) -> int:
    fresh = "--fresh" in (argv if argv is not None else sys.argv[1:])
    print(json.dumps(run(fresh), ensure_ascii=False, indent=2, default=list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
