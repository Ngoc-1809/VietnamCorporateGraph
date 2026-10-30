"""Manual-evaluation tooling: export a stratified sample of REAL sentences with model predictions, GOLD columns empty.

Nothing here writes model output into gold columns. Gold stays blank until a human fills it in."""
from __future__ import annotations

import csv
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from vckg.entity_linking.normalize import fold
from vckg.preprocessing.text import normalize_text, split_sentences

COLUMNS = [
    "sample_id", "stratum", "source", "source_url", "article_id", "sentence", "sentence_start", "sentence_end",
    "entity_spans", "predicted_subject", "predicted_object", "predicted_relation", "predicted_status",
    "predicted_outcome", "predicted_reasons", "rule_status", "llm_valid", "llm_status",
    "gold_entity_spans", "gold_subject", "gold_object", "gold_relation", "gold_status", "reviewer_comment",
]
_SIGNAL = re.compile(
    r"bổ nhiệm|miễn nhiệm|thôi giữ chức|từ nhiệm|chủ tịch|tổng giám đốc|thành viên hđqt|cổ đông lớn|sở hữu|nắm giữ|mua lại|thâu tóm|"
    r"sáp nhập|công ty con|công ty mẹ|cấp tín dụng|hợp đồng tín dụng|cho vay|trái phiếu|xử phạt|bị phạt|khởi tố|hợp tác|liên doanh", re.IGNORECASE)
_MODALITY = re.compile(r"không phải|không có|phủ nhận|chưa|dự kiến|có thể|đang đàm phán|đang xem xét|nguyên |cựu |từng|bị cáo buộc|"
                       r"đang bị điều tra|thôi giữ|từ nhiệm|miễn nhiệm|vô tội", re.IGNORECASE)


def stratum_of(sentence: str, mentions: list[dict], cands: list[dict]) -> str:
    inscope = [m for m in mentions if not str(m.get("linking_method", "")).startswith("out_of_scope")]
    if cands:
        if any(c["outcome"] in ("official", "candidate_edge") for c in cands):
            if any(c["rule_status"] != "FACT" or (c["llm_status"] and c["llm_status"] != c["rule_status"]) for c in cands):
                return "negation_or_status_disagreement"
            return "relation_accepted_or_candidate"
        if any(c["llm_valid"] == "False" for c in cands):
            return "llm_rule_disagreement"
        return "relation_rejected"
    if len(inscope) >= 2:
        if _MODALITY.search(sentence) and _SIGNAL.search(sentence):
            return "modality_no_candidate"
        if any(m["link_status"] in ("ambiguous", "unresolved") and m["label"] == "PERSON" for m in inscope):
            return "entity_ambiguity"
        if _SIGNAL.search(sentence):
            return "signal_no_candidate"
        return "no_relation_control"
    return ""


def rows_for_article(article, mentions: list[dict], outcomes: list[dict]) -> list[dict]:
    """article: Article-like (article_id, url, source, text). mentions/outcomes: dict rows from a pipeline run."""
    text = normalize_text(article.text)
    sents = split_sentences(text)
    ms_by, oc_by = defaultdict(list), defaultdict(list)
    for m in mentions:
        if m.get("article_id") == article.article_id and m.get("sentence_index") is not None:
            ms_by[m["sentence_index"]].append(m)
    for o in outcomes:
        if o.get("article_id") == article.article_id:
            for s in sents:  # outcomes carry the evidence sentence; map back to its index
                if o["evidence"] == s.text:
                    oc_by[s.index].append(o)
                    break
    rows = []
    for s in sents:
        ms, ocs = ms_by.get(s.index, []), oc_by.get(s.index, [])
        stratum = stratum_of(s.text, ms, ocs)
        if not stratum:
            continue
        spans = json.dumps([{"text": m["text"], "start": m["start"], "end": m["end"], "label": m["label"],
                             "entity_id": m.get("entity_id"), "link_status": m["link_status"]} for m in ms], ensure_ascii=False)
        base = {"stratum": stratum, "source": article.source, "source_url": article.url, "article_id": article.article_id,
                "sentence": s.text, "sentence_start": s.start, "sentence_end": s.end, "entity_spans": spans}
        if ocs:
            for o in ocs:
                rows.append({**base, "predicted_subject": o["subject_text"], "predicted_object": o["object_text"],
                             "predicted_relation": o["predicate"], "predicted_status": o["rule_status"],
                             "predicted_outcome": o["outcome"], "predicted_reasons": o["reasons"], "rule_status": o["rule_status"],
                             "llm_valid": o["llm_valid"], "llm_status": o["llm_status"]})
        else:
            rows.append({**base, "predicted_subject": "", "predicted_object": "", "predicted_relation": "", "predicted_status": "",
                         "predicted_outcome": "", "predicted_reasons": "", "rule_status": "", "llm_valid": "", "llm_status": ""})
    return rows


def sample_rows(rows: list[dict], n: int = 120, seed: int = 13) -> list[dict]:
    """Stratified, source-balanced sample. Deterministic for a given seed. Sentences with several predictions stay together."""
    rng = random.Random(seed)
    by_sent: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_sent[(r["article_id"], r["sentence_start"])].append(r)
    strata: dict[str, dict[str, list[tuple]]] = defaultdict(lambda: defaultdict(list))
    for key, rs in by_sent.items():
        strata[rs[0]["stratum"]][rs[0]["source"]].append(key)
    for st in strata.values():
        for lst in st.values():
            lst.sort()
            rng.shuffle(lst)
    chosen: list[tuple] = []
    queues = {st: [k for rr in zip_longest_sources(src) for k in rr] for st, src in strata.items()}
    names = sorted(queues)
    while len(chosen) < min(n, len(by_sent)) and any(queues.values()):
        for st in names:  # round-robin over strata, then sources within each stratum
            if queues[st] and len(chosen) < n:
                chosen.append(queues[st].pop(0))
    out = []
    for i, key in enumerate(sorted(chosen), 1):
        for r in by_sent[key]:
            out.append({**r, "sample_id": f"S{i:04d}"})
    return out


def zip_longest_sources(src: dict[str, list[tuple]]) -> list[list[tuple]]:
    srcs = [src[k] for k in sorted(src)]
    width = max(len(s) for s in srcs)
    return [[s[i] for s in srcs if i < len(s)] for i in range(width)]


def write_csv(path: str | Path, rows: list[dict]) -> int:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})  # gold_* and reviewer_comment are never filled
    return len(rows)


def export_from_runs(run_dirs: list[Path], articles: list, out_csv: str | Path, n: int = 120, seed: int = 13) -> dict:
    by_id = {a.article_id: a for a in articles}
    rows: list[dict] = []
    for d in run_dirs:
        mentions = [json.loads(x) for x in (d / "entities.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        outcomes = list(csv.DictReader((d / "candidate_outcomes.csv").open(encoding="utf-8-sig"))) if (d / "candidate_outcomes.csv").exists() else []
        for aid in {m["article_id"] for m in mentions}:
            if aid in by_id:
                rows += rows_for_article(by_id[aid], mentions, outcomes)
    seen, uniq = set(), []
    for r in rows:  # same article may appear in several runs
        k = (r["article_id"], r["sentence_start"], r["predicted_subject"], r["predicted_object"], r["predicted_relation"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    sample = sample_rows(uniq, n, seed)
    write_csv(out_csv, sample)
    from collections import Counter
    return {"rows": len(sample), "sentences": len({r["sample_id"] for r in sample}),
            "by_stratum": dict(Counter(r["stratum"] for r in {r["sample_id"]: r for r in sample}.values())),
            "by_source": dict(Counter(r["source"] for r in {r["sample_id"]: r for r in sample}.values())),
            "gold_columns_filled": 0, "available_sentences": len({(r["article_id"], r["sentence_start"]) for r in uniq})}


__all__ = ["COLUMNS", "export_from_runs", "fold", "rows_for_article", "sample_rows", "stratum_of", "write_csv"]
