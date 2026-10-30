"""Phase 5 / Task C1: false-negative taxonomy for sentences that carry a relation cue but produced no candidate.

HEURISTIC classification (rule-based triage, not ground truth). Counts are cue coverage, NOT recall.
Usage: python -m vckg.fn_analysis <run_dir> [<run_dir> ...] -> reports/phase5_false_negatives.{md,csv}"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from vckg.models import FactualStatus
from vckg.preprocessing.text import normalize_text, split_sentences
from vckg.relation_extraction.modality import detect_modality
from vckg.storage.sqlite import Staging

ROOT = Path(__file__).resolve().parents[2]

FAMILIES = {
    "ROLE": r"chủ tịch|tổng giám đốc|giám đốc điều hành|\bceo\b|thành viên (?:độc lập )?(?:hđqt|hđtv|hội đồng)|phó chủ tịch|bổ nhiệm|miễn nhiệm|từ nhiệm|thôi giữ chức|sáng lập",
    "OWN": r"sở hữu|nắm giữ|cổ đông lớn|thoái vốn|\bnắm\s+\d",
    "SUBSID": r"công ty con|công ty mẹ|trực thuộc|công ty thành viên|công ty liên kết",
    "ACQUIRE": r"mua lại|thâu tóm|sáp nhập|nhận chuyển nhượng|chuyển nhượng",
    "LEND": r"cho vay|cấp tín dụng|hợp đồng tín dụng|tài trợ vốn|khoản vay",
    "BOND": r"phát hành[^.]{0,30}trái phiếu|trái phiếu[^.]{0,30}phát hành",
    "PARTNER": r"hợp tác chiến lược|ký(?: kết)? (?:thỏa thuận|biên bản ghi nhớ)? ?hợp tác|bắt tay|liên doanh",
    "SANCTION": r"xử phạt|bị phạt|phạt hành chính",
    "PROSECUTE": r"khởi tố|truy tố|bắt tạm giam|bị bắt",
}
_GENERIC_LEND = re.compile(r"lãi suất cho vay|cho vay ký quỹ|margin|dư nợ cho vay|hoạt động cho vay|cho vay tiêu dùng|cho vay bất động sản", re.IGNORECASE)
_CAP_SEQ = re.compile(r"(?:[A-ZĐ][\wÀ-ỹ&.\-]*\s+){1,5}[A-ZĐ][\wÀ-ỹ&.\-]*|[A-Z]{2,6}")
CATEGORIES = [
    "NO_ENTITY_PAIR", "NER_MISSED_ENDPOINT", "WRONG_SPAN_OR_TYPE", "GENERATOR_MISS", "MULTI_ENTITY_SENTENCE",
    "ELIDED_SUBJECT_OR_CROSS_SENTENCE", "MODALITY_NOT_FACT", "NOT_A_RELATION_GENERIC_CUE",
]


def classify(sent_text: str, family: str, mentions: list[dict], prev_mentions: list[dict]) -> str:
    ins = [m for m in mentions if not str(m.get("linking_method", "")).startswith("out_of_scope")]
    heads = [m for m in ins if m.get("alias_of") is None]
    if family == "LEND" and _GENERIC_LEND.search(sent_text):
        return "NOT_A_RELATION_GENERIC_CUE"
    status, _ = detect_modality(sent_text)
    if len(heads) < 2:
        covered = [(m["start"], m["end"]) for m in heads]
        uncovered = [c.group(0) for c in _CAP_SEQ.finditer(sent_text) if c.start() > 0 and len(c.group(0)) > 3]
        if len(heads) == 1 and prev_mentions:
            return "ELIDED_SUBJECT_OR_CROSS_SENTENCE"
        if len(heads) == 1 and re.match(r"^\W*(?:sở hữu|nắm|giữ|đảm nhiệm|là|được|đã|hiện)", sent_text, re.IGNORECASE):
            return "ELIDED_SUBJECT_OR_CROSS_SENTENCE"
        return "NER_MISSED_ENDPOINT" if (uncovered and len(uncovered) > len(covered)) else "NO_ENTITY_PAIR"
    if status not in (FactualStatus.FACT,):
        return "MODALITY_NOT_FACT"
    if len(heads) >= 5:
        return "MULTI_ENTITY_SENTENCE"
    bad = [m for m in heads if len(m["text"]) < 4 or m["text"].islower()]
    if bad:
        return "WRONG_SPAN_OR_TYPE"
    return "GENERATOR_MISS" if len(heads) <= 4 else "MULTI_ENTITY_SENTENCE"


def analyse(run_dirs: list[Path], staging_db: Path | None = None) -> list[dict]:
    st = Staging(staging_db or ROOT / "data/staging/staging.sqlite")
    arts = {a.article_id: a for a in st.get_articles()}
    rows: list[dict] = []
    for d in run_dirs:
        ments = [json.loads(x) for x in (d / "entities.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        cands = [json.loads(x) for x in (d / "candidates.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        cand_sent = {(c["article_id"], c["sentence_index"]) for c in cands}
        by = defaultdict(list)
        for m in ments:
            by[(m["article_id"], m.get("sentence_index"))].append(m)
        for aid in sorted({m["article_id"] for m in ments}):
            a = arts.get(aid)
            if not a:
                continue
            for s in split_sentences(normalize_text(a.text)):
                for fam, rx in FAMILIES.items():
                    if re.search(rx, s.text, re.IGNORECASE):
                        if len([m for m in by.get((aid, s.index), []) if m.get("alias_of") is None]) < 1:
                            continue
                        has = (aid, s.index) in cand_sent
                        cat = "HAS_CANDIDATE" if has else classify(s.text, fam, by.get((aid, s.index), []), by.get((aid, s.index - 1), []))
                        rows.append({"run": d.name, "article_id": aid, "source": a.source, "url": a.url, "family": fam,
                                     "category": cat, "n_mentions": len(by.get((aid, s.index), [])), "sentence": s.text})
    return rows


def write_reports(rows: list[dict], out_md: Path, out_csv: Path) -> dict:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    tot = Counter(r["family"] for r in rows)
    has = Counter(r["family"] for r in rows if r["category"] == "HAS_CANDIDATE")
    cats = Counter(r["category"] for r in rows if r["category"] != "HAS_CANDIDATE")
    lines = ["# Phase 5 - False-negative taxonomy (heuristic triage)", "",
             "Cue sentences with >=1 in-scope mention. **Cue coverage, not recall.** Categories are rule-based triage, not gold.", "",
             "| family | cue sentences | with candidate | coverage |", "|---|---|---|---|"]
    for k in FAMILIES:
        if tot[k]:
            lines.append(f"| {k} | {tot[k]} | {has[k]} | {has[k] / tot[k]:.0%} |")
    lines += ["", "| missing-candidate category | sentences |", "|---|---|"] + [f"| {c} | {cats.get(c, 0)} |" for c in CATEGORIES]
    for c in ("GENERATOR_MISS", "MULTI_ENTITY_SENTENCE", "ELIDED_SUBJECT_OR_CROSS_SENTENCE", "NER_MISSED_ENDPOINT", "WRONG_SPAN_OR_TYPE"):
        ex = [r for r in rows if r["category"] == c][:6]
        if ex:
            lines += ["", f"### {c} (examples)"] + [f"- [{r['family']}] {r['sentence'][:220]}" for r in ex]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return {"total": dict(tot), "with_candidate": dict(has), "missing": dict(cats)}


if __name__ == "__main__":
    dirs = [Path(a) for a in sys.argv[1:]]
    rows = analyse(dirs)
    print(json.dumps(write_reports(rows, ROOT / "reports/phase5_false_negatives.md", ROOT / "reports/phase5_false_negatives.csv"), ensure_ascii=False, indent=1))
