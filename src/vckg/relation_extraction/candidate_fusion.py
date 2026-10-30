"""Phase 6B.1 - fusion of rule-based and LLM-discovered candidates (experiment only; nothing becomes official here).

Key = (canonical subject, predicate, canonical object, factual status); entities without an id are keyed by surface text + article.
discovery_method = RULE | LLM | BOTH. Evidence is merged by (article, span). The same (s,p,o) with different statuses is kept as
separate entries and flagged `status_conflict`. Agreement between RULE and LLM is not an independent verification of quality."""
from __future__ import annotations

from collections import defaultdict

from vckg.models import RelationCandidate


def ent_key(m, article_id: str, canon) -> str:
    return canon(m.entity_id) if m.entity_id else f"text:{article_id}:{m.text.lower()}"


def cand_key(c: RelationCandidate, canon, with_status: bool = True) -> tuple:
    k = (ent_key(c.subject, c.article_id, canon), c.predicate, ent_key(c.object, c.article_id, canon))
    return (*k, c.factual_status.value) if with_status else k


def fuse(items: list[dict], canon=lambda x: x) -> list[dict]:
    """items: {'cand': RelationCandidate, 'method': 'RULE'|'LLM', 'meta': dict}. Symmetric predicates are not reordered here."""
    fused: dict[tuple, dict] = {}
    for it in items:
        c: RelationCandidate = it["cand"]
        k = cand_key(c, canon)
        f = fused.setdefault(k, {"key": k, "subject_id": k[0], "predicate": c.predicate, "object_id": k[2], "factual_status": c.factual_status.value,
                                 "methods": set(), "articles": set(), "evidence": [], "candidates": [], "llm_meta": [], "raw_count": 0})
        f["methods"].add(it["method"])
        f["articles"].add(c.article_id)
        f["raw_count"] += 1
        f["candidates"].append(c)
        if it["method"] == "LLM":
            f["llm_meta"].append(it["meta"])
        span = (c.article_id, c.evidence_start, c.evidence_end)
        if span not in {(e["article_id"], e["evidence_start"], e["evidence_end"]) for e in f["evidence"]}:
            f["evidence"].append({"article_id": c.article_id, "evidence_text": c.evidence_text, "evidence_start": c.evidence_start,
                                  "evidence_end": c.evidence_end, "method": it["method"]})
    by_spo = defaultdict(set)
    for k in fused:
        by_spo[k[:3]].add(k[3])
    out = []
    for f in fused.values():
        ms = f["methods"]
        f["discovery_method"] = "BOTH" if len(ms) == 2 else next(iter(ms))
        f["status_conflict"] = len(by_spo[f["key"][:3]]) > 1
        f["duplicate_raw"] = f["raw_count"] - 1
        out.append(f)
    return out


def venn(rule: list[dict], llm: list[dict]) -> dict:
    """Both lists are fused outputs; compares on (s,p,o) ignoring status."""
    a = {f["key"][:3] for f in rule}
    b = {f["key"][:3] for f in llm}
    return {"A": len(a), "B": len(b), "both": len(a & b), "only_B": len(b - a), "only_A": len(a - b), "union": len(a | b)}
