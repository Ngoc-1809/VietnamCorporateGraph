"""Phase 5 final benchmark tables from real run outputs. Groups: baseline (Phase 4 snapshot), phase5 dev44 / holdout19 (same 63
articles), new targeted, new control (split of run new144 via the discovery manifest). Edge counts are per group by evidence article."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from vckg.fn_analysis import analyse
from vckg.metrics import compute_kpis, unique_edges

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/outputs"


def _jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def subset_stats(run: Path, article_ids: set[str], meta: dict[str, dict]) -> dict:
    """Metrics for the articles of one subset inside a run directory."""
    rows = [r for r in csv.DictReader((run / "candidate_outcomes.csv").open(encoding="utf-8-sig")) if r["article_id"] in article_ids]
    ments = [m for m in _jl(run / "entities.jsonl") if m["article_id"] in article_ids]
    def sub_edges(fname):
        out = []
        for e in _jl(run / fname):
            ev = [r for r in e["evidence"] if r["article_id"] in article_ids]
            if ev:
                out.append({**e, "evidence": ev})
        return list(unique_edges(out).values())
    off, cand = sub_edges("relations_official.jsonl"), sub_edges("relations_candidate.jsonl")
    off_keys = {(e["subject_id"], e["predicate"], e["object_id"]) for e in off}
    cand = [e for e in cand if (e["subject_id"], e["predicate"], e["object_id"]) not in off_keys]
    nodes = {e["subject_id"] for e in off} | {e["object_id"] for e in off}
    per_art = defaultdict(lambda: {"official": 0, "cand": 0, "rows": 0})
    for e in off:
        for a in {r["article_id"] for r in e["evidence"]}:
            per_art[a]["official"] += 1
    for e in cand:
        for a in {r["article_id"] for r in e["evidence"]}:
            per_art[a]["cand"] += 1
    for r in rows:
        per_art[r["article_id"]]["rows"] += 1
    fn = [r for r in analyse([run]) if r["article_id"] in article_ids]
    cue_art = {r["article_id"] for r in fn}
    no_rel = [a for a in article_ids if per_art[a]["official"] == 0 and per_art[a]["cand"] == 0]
    why = Counter()
    for a in no_rel:
        arr = [r for r in rows if r["article_id"] == a]
        if arr:
            why["candidates_generated_but_all_rejected:" + Counter(x for r in arr for x in r["reasons"].split("|") if x).most_common(1)[0][0]] += 1
        elif a in cue_art:
            why["cue_sentence_present_but_no_candidate (pattern/NER miss)"] += 1
        else:
            why["no_relation_cue_in_article"] += 1
    llm = [r for r in rows if r["llm_valid"] != ""]
    return {
        "articles": len(article_ids), "mentions": len(ments), "entities_grounded_or_provisional_touched": len({m["entity_id"] for m in ments if m["entity_id"] and m["link_status"] in ("grounded", "provisional")}),
        "candidates_generated": len(rows), "official_unique_edges": len(off), "candidate_unique_edges": len(cand),
        "graph_entity_nodes": len(nodes), "official_edges_per_article": round(len(off) / len(article_ids), 3) if article_ids else None,
        "candidates_per_article": round(len(rows) / len(article_ids), 3) if article_ids else None,
        "articles_with_official": sum(1 for a in article_ids if per_art[a]["official"]), "articles_without_any_edge": len(no_rel),
        "why_no_edge": dict(why), "relation_types_official": sorted({e["predicate"] for e in off}),
        "official_by_predicate": dict(Counter(e["predicate"] for e in off)), "candidate_by_predicate": dict(Counter(e["predicate"] for e in cand)),
        "llm_verified_candidates": len(llm), "llm_valid": sum(1 for r in llm if r["llm_valid"] == "True"),
        "llm_rejected": sum(1 for r in llm if r["llm_valid"] == "False"),
        "duplicate_evidence_merged": sum(len(e["evidence"]) - 1 for e in off),
        "rejection_reasons": dict(Counter(x for r in rows if r["outcome"] == "rejected" for x in r["reasons"].split("|") if x)),
    }


def build() -> dict:
    p5 = OUT / "phase5"
    man = [json.loads(x) for x in (p5 / "experiment_manifest.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    ids = defaultdict(set)
    for r in man:
        ids[r["subset"]].add(r["article_id"])
    res: dict = {"baseline_phase4": json.loads((ROOT / "reports/phase5_baseline_kpis.json").read_text(encoding="utf-8"))}
    res["phase5_groups"] = {
        "dev44": compute_kpis(p5 / "dev44", ROOT / "data/registry/registry_p5_dev.sqlite"),
        "holdout19": compute_kpis(p5 / "holdout19", ROOT / "data/registry/registry_p5_holdout.sqlite"),
        "new144_all": compute_kpis(p5 / "new144", ROOT / "data/registry/registry_p5_new.sqlite")}
    res["new_subsets"] = {k: subset_stats(p5 / "new144", ids[k], {}) for k in ("targeted", "control")}
    by_topic, by_source = {}, {}
    t = [r for r in man if r["subset"] == "targeted"]
    for key, name in (("topic", "by_topic"), ("source", "by_source")):
        for val in sorted({r[key] for r in t}):
            by_topic_ids = {r["article_id"] for r in t if r[key] == val}
            s = subset_stats(p5 / "new144", by_topic_ids, {})
            (by_topic if key == "topic" else by_source)[val] = {k: s[k] for k in ("articles", "official_unique_edges", "candidate_unique_edges", "official_edges_per_article", "candidates_per_article", "relation_types_official")}
    res["targeted_by_topic"], res["targeted_by_source"] = by_topic, by_source
    res["control_by_source"] = {}
    for val in sorted({r["source"] for r in man if r["subset"] == "control"}):
        s = subset_stats(p5 / "new144", {r["article_id"] for r in man if r["subset"] == "control" and r["source"] == val}, {})
        res["control_by_source"][val] = {k: s[k] for k in ("articles", "official_unique_edges", "candidate_unique_edges", "official_edges_per_article")}
    return res


def to_markdown(r: dict) -> str:
    L = ["# Phase 5 - Benchmark tự sinh từ dữ liệu chạy thật", "", "Không có ground truth: không có Precision/Recall. Số liệu là đếm cạnh theo nhóm bài.", ""]
    keys = ["articles_processed", "official_unique_edges", "candidate_unique_edges", "graph_entity_nodes", "official_relation_types", "articles_with_official_edges",
            "official_edges_per_article", "candidates_per_article", "article_grounded_entities", "provisional_entities", "llm_calls_per_article"]
    L += ["## Nhóm 63 bài gốc: baseline Phase 4 vs Phase 5 (cùng bài)", "", "| chỉ số | dev44 P4 | dev44 P5 | holdout19 P4 | holdout19 P5 |", "|---|---|---|---|---|"]
    b, g = r["baseline_phase4"], r["phase5_groups"]
    for k in keys:
        L.append(f"| {k} | {b['final_dev'].get(k)} | {g['dev44'].get(k)} | {b['final_holdout'].get(k)} | {g['holdout19'].get(k)} |")
    L += ["", "dev44 đã được dùng để sửa mẫu/prompt (không độc lập). holdout19 chỉ được chạy lại, không dùng để chỉnh.", "",
          "## Bài mới: targeted vs control", "", "| chỉ số | targeted | control |", "|---|---|---|"]
    t, c = r["new_subsets"]["targeted"], r["new_subsets"]["control"]
    for k in ("articles", "mentions", "entities_grounded_or_provisional_touched", "candidates_generated", "official_unique_edges", "candidate_unique_edges", "graph_entity_nodes",
              "official_edges_per_article", "candidates_per_article", "articles_with_official", "articles_without_any_edge", "llm_verified_candidates", "llm_valid", "llm_rejected",
              "duplicate_evidence_merged"):
        L.append(f"| {k} | {t[k]} | {c[k]} |")
    L += ["", f"Loại quan hệ official - targeted: {t['relation_types_official']}; control: {c['relation_types_official']}", "",
          f"official theo predicate - targeted: {t['official_by_predicate']}; control: {c['official_by_predicate']}",
          f"candidate theo predicate - targeted: {t['candidate_by_predicate']}; control: {c['candidate_by_predicate']}", "",
          "### Vì sao bài không có cạnh", "", f"- targeted: {t['why_no_edge']}", f"- control: {c['why_no_edge']}", "",
          "### Lý do loại candidate", "", f"- targeted: {t['rejection_reasons']}", f"- control: {c['rejection_reasons']}", "", "## Targeted theo chủ đề", "",
          "| chủ đề | bài | official | candidate | official/bài | loại official |", "|---|---|---|---|---|---|"]
    for k, v in r["targeted_by_topic"].items():
        L.append(f"| {k} | {v['articles']} | {v['official_unique_edges']} | {v['candidate_unique_edges']} | {v['official_edges_per_article']} | {v['relation_types_official']} |")
    L += ["", "## Targeted theo nguồn", "", "| nguồn | bài | official | candidate | official/bài |", "|---|---|---|---|---|"]
    for k, v in r["targeted_by_source"].items():
        L.append(f"| {k} | {v['articles']} | {v['official_unique_edges']} | {v['candidate_unique_edges']} | {v['official_edges_per_article']} |")
    L += ["", "## Control theo nguồn", "", "| nguồn | bài | official | candidate | official/bài |", "|---|---|---|---|---|"]
    for k, v in r["control_by_source"].items():
        L.append(f"| {k} | {v['articles']} | {v['official_unique_edges']} | {v['candidate_unique_edges']} | {v['official_edges_per_article']} |")
    return "\n".join(L)


if __name__ == "__main__":
    res = build()
    (ROOT / "reports/phase5_benchmark.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "reports/phase5_benchmark.md").write_text(to_markdown(res), encoding="utf-8")
    print(to_markdown(res))
