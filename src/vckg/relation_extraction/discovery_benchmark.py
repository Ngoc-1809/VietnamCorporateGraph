"""Phase 6B.1 experiment CLI.  select -> run (resumable, budgeted) -> report.   Outputs: data/experiments/phase6b, reports/phase6b.
Never touches Neo4j, registry, official edges or the auditor logic (the auditor is only CALLED, deterministic mode, no Qwen)."""
from __future__ import annotations

import csv
import json
import random
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from vckg.fn_analysis import FAMILIES
from vckg.models import RelationCandidate
from vckg.preprocessing.text import normalize_text, split_sentences
from vckg.reasons import pre_llm_reasons
from vckg.relation_extraction.candidate_fusion import fuse
from vckg.relation_extraction.candidates import load_relations
from vckg.relation_extraction.llm_discovery import (
    DISCOVERY_PROMPT_VERSION,
    BudgetExceeded,
    DiscoveryLLM,
    select_windows,
    validate_relation,
    window_sentences,
)
from vckg.storage.sqlite import Staging

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "data/experiments/phase6b"
REP = ROOT / "reports/phase6b"
RUN = ROOT / "data/outputs/phase5/new144"
REGISTRY = ROOT / "data/registry/registry_p5_new.sqlite"
SEED = 20261031
CUE = re.compile("|".join(f"(?:{v})" for v in FAMILIES.values() if v), re.IGNORECASE)
PRED_FAMILY = {"CHAIR_OF": "ROLE", "CEO_OF": "ROLE", "BOARD_MEMBER_OF": "ROLE", "FOUNDED": "ROLE", "OWNS_SHARES_IN": "OWN", "SUBSIDIARY_OF": "SUBSID",
               "ACQUIRED": "ACQUIRE", "LENDS_TO": "LEND", "JOINT_VENTURE_WITH": "PARTNER", "PARTNERS_WITH": "PARTNER", "SANCTIONED_BY": "SANCTION",
               "PROSECUTED_BY": "PROSECUTE", "ISSUED_BOND": "BOND"}


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


# ------------------------------------------------------------------------------------------------ select
def select_articles() -> list[dict]:
    man = jl(ROOT / "data/outputs/phase5/experiment_manifest.jsonl")
    rng = random.Random(SEED)
    pick = {}
    for subset, n in (("targeted", 40), ("control", 20)):
        pool = sorted((r for r in man if r["subset"] == subset), key=lambda r: r["article_id"])
        pick[subset] = rng.sample(pool, n)
    rows = []
    for subset in ("targeted", "control"):
        for i, r in enumerate(pick[subset]):
            rows.append({"article_id": r["article_id"], "url": r["url"], "content_hash": r.get("content_hash", ""), "source": r["source"], "subset": subset,
                         "topic": r.get("topic"), "selection_score": r.get("selection_score"), "smoke": i < (4 if subset == "targeted" else 2), "seed": SEED})
    EXP.mkdir(parents=True, exist_ok=True)
    (EXP / "manifest.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return rows


def load_manifest() -> list[dict]:
    p = EXP / "manifest.jsonl"
    return jl(p) if p.exists() else select_articles()


# ------------------------------------------------------------------------------------------------ run
def head_mentions(rows: list[dict]) -> list[dict]:
    ms = [m for m in rows if m.get("alias_of") is None and not str(m.get("linking_method", "")).startswith("out_of_scope")]
    ms.sort(key=lambda m: (m["start"], m["end"]))
    for i, m in enumerate(ms):
        m["mid"] = f"M{i}"
    return ms


def run(out: Path, smoke: bool, max_calls: int = 180) -> int:
    from vckg.relation_extraction.qwen_verifier import LLMCache
    out.mkdir(parents=True, exist_ok=True)
    manifest = [r for r in load_manifest() if r["smoke"] or not smoke]
    arts = {a.article_id: a for a in Staging(ROOT / "data/staging/staging.sqlite").get_articles()}
    by_art: dict[str, list[dict]] = defaultdict(list)
    for m in jl(RUN / "entities.jsonl"):
        by_art[m["article_id"]].append(m)
    relations = load_relations(str(ROOT / "config/relations.yaml"))
    llm = DiscoveryLLM(LLMCache(EXP / "llm_cache.sqlite"), max_live_calls=max_calls)
    if not llm.available():
        print("UNAVAILABLE: Ollama/qwen3.5:9b not reachable")
        return 2
    ck = out / "chunks.jsonl"
    done = {(r["article_id"], r["window"]["start"], r["window"]["end"], r["prompt_version"]) for r in jl(ck)}
    prog = {"state": "RUNNING", "articles_total": len(manifest), "articles_done": 0, "windows_done": len(done), "live_calls": 0, "started": time.strftime("%H:%M:%S")}
    (out / "progress.json").write_text(json.dumps(prog), encoding="utf-8")
    code = 0
    with ck.open("a", encoding="utf-8") as f:
        for n, row in enumerate(manifest, 1):
            aid = row["article_id"]
            a = arts[aid]
            text = normalize_text(a.text)
            sents = split_sentences(text)
            ms = head_mentions(by_art[aid])
            wins = window_sentences(sents, ms, CUE)
            chosen, left = select_windows(wins)
            for w in chosen:
                k = (aid, w["start"], w["end"], DISCOVERY_PROMPT_VERSION)
                if k in done:
                    continue
                inside = [m for m in ms if m["start"] >= w["start"] and m["end"] <= w["end"]]
                try:
                    res = llm.discover(a.title, text[w["start"]:w["end"]], inside)
                except BudgetExceeded as e:
                    print("STOP:", e)
                    prog.update(state="STOPPED_BUDGET")
                    code = 3
                    break
                rec = {"article_id": aid, "window": w, "eligible_windows_unexamined": left, "prompt_version": DISCOVERY_PROMPT_VERSION, "model": llm.model,
                       "ok": res is not None, "cached": bool(res and res["cached"]), "usage": res["usage"] if res else {}, "raw": [], "accepted": [],
                       "unresolved": [], "rejected": []}
                if res:
                    mids = {m["mid"]: m for m in inside}
                    seen = set()
                    for rel in res["parsed"]["relations"]:
                        raw_key = json.dumps(rel, sort_keys=True, ensure_ascii=False)
                        if raw_key in seen:
                            rec["rejected"].append({"reason": "DUPLICATE_IN_CHUNK", "rel": rel})
                            continue
                        seen.add(raw_key)
                        rec["raw"].append(rel)
                        cand, why = validate_relation(rel, text, w, sents, mids, relations, aid)
                        if cand is None:
                            rec["rejected"].append({"reason": why, "rel": rel})
                        elif cand["unresolved"]:
                            rec["unresolved"].append(cand)
                        else:
                            c = cand["candidate"]
                            rec["accepted"].append({"cand": c.model_dump(mode="json"), "llm_quote": cand["llm_quote"], "model_status": cand["model_status"],
                                                    "rule_status": cand["rule_status"], "reason": cand["reason"]})
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
            if code:
                break
            prog.update(articles_done=n, windows_done=prog["windows_done"], live_calls=llm.stats.calls, cache_hits=llm.stats.cache_hits, failures=llm.stats.failures,
                        updated=time.strftime("%H:%M:%S"))
            (out / "progress.json").write_text(json.dumps(prog), encoding="utf-8")
    if not code:
        prog.update(state="COMPLETED", finished=time.strftime("%H:%M:%S"))
    prog.update(live_calls=llm.stats.calls, cache_hits=llm.stats.cache_hits, failures=llm.stats.failures)
    (out / "progress.json").write_text(json.dumps(prog), encoding="utf-8")
    print(json.dumps(prog))
    return code


# ------------------------------------------------------------------------------------------------ report
def _canon_fn():
    db = sqlite3.connect(str(REGISTRY))
    parent = {a: b for a, b in db.execute("SELECT entity_id, merged_into FROM entities WHERE merged_into IS NOT NULL")}
    db.close()

    def canon(x):
        seen = set()
        while x in parent and x not in seen:
            seen.add(x)
            x = parent[x]
        return x
    return canon


def report(out: Path, tag: str) -> dict:
    from vckg.validation.auto_auditor import audit_edge, build_context
    manifest = {r["article_id"]: r for r in load_manifest() if r["smoke"] or tag != "smoke"}
    chunks = jl(out / "chunks.jsonl")
    chunks = [c for c in chunks if c["article_id"] in manifest and c["prompt_version"] == DISCOVERY_PROMPT_VERSION]
    canon = _canon_fn()
    arts = {a.article_id: a for a in Staging(ROOT / "data/staging/staging.sqlite").get_articles()}
    texts = {aid: normalize_text(arts[aid].text) for aid in manifest}
    relations = load_relations(str(ROOT / "config/relations.yaml"))
    windows = defaultdict(list)
    for c in chunks:
        windows[c["article_id"]].append((c["window"]["start"], c["window"]["end"]))
    items = []
    for r in jl(RUN / "candidates.jsonl"):
        if r["article_id"] in manifest:
            c = RelationCandidate.model_validate(r)
            items.append({"cand": c, "method": "RULE", "meta": {}, "in_window": any(s <= c.evidence_start and c.evidence_end <= e for s, e in windows[c.article_id])})
    n_rule_raw = len(items)
    rejects, unresolved = Counter(), []
    n_llm_raw = 0
    for c in chunks:
        for a in c["accepted"]:
            n_llm_raw += 1
            items.append({"cand": RelationCandidate.model_validate(a["cand"]), "method": "LLM", "in_window": True,
                          "meta": {"llm_quote": a["llm_quote"], "model_status": a["model_status"], "rule_status": a["rule_status"], "reason": a["reason"],
                                   "prompt_version": c["prompt_version"], "model": c["model"]}})
        for r in c["rejected"]:
            rejects[r["reason"]] += 1
        unresolved += c["unresolved"]
    for it in items:
        it.setdefault("in_window", True)
    fused = fuse(items, canon)
    # deterministic validation + auditor (deterministic mode: no Qwen -> no extra inference, no same-model circularity)
    ctx = build_context([RUN], [REGISTRY], ROOT / "data/staging/staging.sqlite")
    t0 = time.perf_counter()
    for f in fused:
        c = f["candidates"][0]
        reasons = pre_llm_reasons(texts[c.article_id], c, relations[c.predicate])
        f["det_reasons"] = [x.value for x in reasons]
        f["valid_evidence"] = "MISSING_EVIDENCE" not in f["det_reasons"]
        f["det_pass"] = not reasons and f["factual_status"] != "DENIED"
        f["in_window_rule"] = any(it["in_window"] for it in items if it["method"] == "RULE" and it["cand"].candidate_id in {x.candidate_id for x in f["candidates"]})
        f["auditor"] = None
        if f["det_pass"]:
            evs = [{"article_id": e["article_id"], "source_url": arts[e["article_id"]].url, "evidence_text": e["evidence_text"], "evidence_start": e["evidence_start"],
                    "evidence_end": e["evidence_end"], "factual_status": f["factual_status"], "published_at": None, "extraction_method": e["method"],
                    "review_status": "NEEDS_REVIEW", "valid_from": None, "valid_to": None} for e in f["evidence"]]
            edge = {"subject_id": c.subject.entity_id, "predicate": c.predicate, "object_id": c.object.entity_id, "evidence": evs, "edge_id": "x"}
            r = audit_edge(edge, ctx, None, llm_required=False)
            f["auditor"] = {"decision": r["decision"], "failed": r["failed_checks"], "reasons": r["reasons"][:3]}
        f["cue_present"] = bool(re.search(FAMILIES[PRED_FAMILY[f["predicate"]]], f["evidence"][0]["evidence_text"], re.IGNORECASE))
    audit_secs = time.perf_counter() - t0
    for f in fused:
        f["methods"] = sorted(f["methods"])

    def sets(sel):
        return [f for f in fused if sel(f)]
    A, B, C = sets(lambda f: "RULE" in f["methods"]), sets(lambda f: "LLM" in f["methods"]), fused
    Aw = sets(lambda f: "RULE" in f["methods"] and f["in_window_rule"])
    a_spo = {f["key"][:3] for f in A}
    b_spo = {f["key"][:3] for f in B}
    only_B = sets(lambda f: f["methods"] == ["LLM"] and f["key"][:3] not in a_spo)
    status_disagree = sets(lambda f: f["methods"] == ["LLM"] and f["key"][:3] in a_spo)
    only_A_w = sets(lambda f: "RULE" in f["methods"] and f["in_window_rule"] and f["key"][:3] not in b_spo)

    def stat(S):
        aud = Counter(f["auditor"]["decision"] for f in S if f["auditor"])
        pat_only = sum(1 for f in S if f["auditor"] and f["auditor"]["decision"] == "QUARANTINE" and set(f["auditor"]["failed"]) <= {"RELATION_NOT_REPRODUCED"})
        arts_ = defaultdict(set)
        for f in S:
            for a in f["articles"]:
                arts_[a].add(f["key"])

        def y(sel):
            ids = [a for a, m in manifest.items() if sel(m)]
            return {"articles": len(ids), "candidates": sum(len(arts_.get(a, ())) for a in ids), "per_article": round(sum(len(arts_.get(a, ())) for a in ids) / max(len(ids), 1), 3)}
        return {"unique": len(S), "valid_evidence": sum(f["valid_evidence"] for f in S), "det_pass": sum(f["det_pass"] for f in S),
                "auditor": dict(aud), "auditor_quarantine_only_because_pattern_not_reproduced": pat_only, "relation_types": sorted({f["predicate"] for f in S}),
                "by_predicate": dict(Counter(f["predicate"] for f in S)), "by_status": dict(Counter(f["factual_status"] for f in S)),
                "yield_targeted": y(lambda m: m["subset"] == "targeted"), "yield_control": y(lambda m: m["subset"] == "control"),
                "yield_by_source": {s: y(lambda m, s=s: m["source"] == s) for s in sorted({m["source"] for m in manifest.values()})},
                "with_status_conflict": sum(f["status_conflict"] for f in S)}
    live = [c for c in chunks if not c["cached"] and c["ok"]]
    usage = {"windows_examined": len(chunks), "live_calls_recorded": len(live), "cached_windows": sum(c["cached"] for c in chunks), "failed_calls": sum(not c["ok"] for c in chunks),
             "prompt_tokens": sum(c["usage"].get("prompt_tokens", 0) for c in live), "completion_tokens": sum(c["usage"].get("eval_tokens", 0) for c in live),
             "qwen_seconds": round(sum(c["usage"].get("seconds", 0) for c in live), 1), "audit_seconds_deterministic": round(audit_secs, 1),
             "eligible_windows_unexamined": sum(c["eligible_windows_unexamined"] for c in {c["article_id"]: c for c in chunks}.values())}
    res = {"tag": tag, "articles": len(manifest), "targeted": sum(m["subset"] == "targeted" for m in manifest.values()),
           "control": sum(m["subset"] == "control" for m in manifest.values()), "prompt_version": DISCOVERY_PROMPT_VERSION,
           "raw": {"rule_candidates": n_rule_raw, "llm_valid_relations": n_llm_raw, "llm_rejected": dict(rejects), "llm_unresolved_endpoint": len(unresolved)},
           "A_rule_all": stat(A), "A_rule_in_examined_windows": stat(Aw), "B_llm": stat(B), "C_union": stat(C),
           "overlap_all_vs_B": {"both_same_status": sum(f["methods"] == ["BOTH"] for f in fused), "both_triples_ignoring_status": len(a_spo & b_spo),
                                "same_triple_different_status": len(status_disagree), "only_B": len(only_B), "only_A_in_windows_missed_by_B": len(only_A_w),
                                "only_A_outside_windows": len({f["key"][:3] for f in fused if "RULE" in f["methods"] and not f["in_window_rule"]} - b_spo)},
           "duplicate_rate": {"B_raw_over_unique": round(n_llm_raw / max(len(B), 1), 3), "C_raw_over_unique": round((n_rule_raw + n_llm_raw) / max(len(C), 1), 3)},
           "only_B": {**{k: v for k, v in stat(only_B).items() if k in ("unique", "valid_evidence", "det_pass", "auditor", "auditor_quarantine_only_because_pattern_not_reproduced", "relation_types", "by_predicate", "by_status")},
                      "new_relation_types_vs_A": sorted({f["predicate"] for f in only_B} - {f["predicate"] for f in A}),
                      "no_lexical_cue_for_predicate": sum(not f["cue_present"] for f in only_B),
                      "llm_status_stricter_than_model": sum(1 for f in only_B for m in f["llm_meta"] if m["model_status"] != f["factual_status"])},
           "usage": usage}
    REP.mkdir(parents=True, exist_ok=True)
    (REP / f"benchmark_{tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=list), encoding="utf-8")
    cols = ["article_id", "source", "subset", "url", "subject", "subject_entity", "predicate", "object", "object_entity", "factual_status", "model_status", "rule_status",
            "evidence", "llm_quote", "llm_reason", "deterministic_valid", "det_reasons", "auditor_decision", "auditor_failed_checks", "lexical_cue_for_predicate",
            "human_label (CORRECT/WRONG/UNSURE)", "human_note"]
    with (REP / f"b_only_candidates_{tag}.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for f in sorted(only_B, key=lambda f: (f["articles"] and min(f["articles"]), f["predicate"])):
            c, m = f["candidates"][0], f["llm_meta"][0]
            a = min(f["articles"])
            w.writerow({"article_id": a, "source": manifest[a]["source"], "subset": manifest[a]["subset"], "url": manifest[a]["url"], "subject": c.subject.text,
                        "subject_entity": c.subject.entity_id, "predicate": c.predicate, "object": c.object.text, "object_entity": c.object.entity_id,
                        "factual_status": f["factual_status"], "model_status": m["model_status"], "rule_status": m["rule_status"], "evidence": c.evidence_text,
                        "llm_quote": m["llm_quote"], "llm_reason": m["reason"], "deterministic_valid": f["det_pass"], "det_reasons": "|".join(f["det_reasons"]),
                        "auditor_decision": (f["auditor"] or {}).get("decision", "NOT_AUDITED"), "auditor_failed_checks": "|".join((f["auditor"] or {}).get("failed", [])),
                        "lexical_cue_for_predicate": f["cue_present"], "human_label (CORRECT/WRONG/UNSURE)": "", "human_note": ""})
    (REP / f"llm_unresolved_endpoint_{tag}.jsonl").write_text("\n".join(json.dumps(u, ensure_ascii=False, default=str) for u in unresolved), encoding="utf-8")
    (REP / f"llm_rejected_{tag}.jsonl").write_text("\n".join(json.dumps({"article_id": c["article_id"], **r}, ensure_ascii=False) for c in chunks for r in c["rejected"]), encoding="utf-8")
    return res


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="discovery_benchmark")
    ap.add_argument("cmd", choices=["select", "run", "report", "all"])
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--max-calls", type=int, default=180)
    a = ap.parse_args(argv)
    tag = "smoke" if a.smoke else "batch60"
    out = EXP / tag
    if a.cmd == "select":
        rows = select_articles()
        print(len(rows), "articles ->", EXP / "manifest.jsonl")
        return 0
    code = 0
    if a.cmd in ("run", "all"):
        code = run(out, a.smoke, a.max_calls)
    if a.cmd in ("report", "all") and code in (0, 3):
        print(json.dumps(report(out, tag), ensure_ascii=False, indent=2, default=list))
    return code


if __name__ == "__main__":
    sys.exit(main())

