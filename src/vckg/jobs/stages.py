"""Phase 6C - per-article pipeline stages, composed from the EXISTING modules (nothing re-implemented):
  load -> GLiNER NER (versioned cache) -> registry dictionary/merge/resolve (pipeline.process_article, no Qwen verifier)
       -> span recovery + article grounding (6B.4/6B.3 rules, staging registry) -> rule candidates (+bonds)
       -> Qwen discovery windows (6B.1, versioned cache, call cap) -> artifacts (JSON-serialisable).
Fusion + hybrid QA + staging graph run later over ALL finished articles (worker.finalize), so nothing here decides PASS/QUARANTINE.
Nothing in this module can create an official edge."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from vckg.entity_linking.article_grounding import _truncated, ground_article, overlay_from
from vckg.entity_linking.resolver import EntityResolver
from vckg.entity_linking.store import RegistryStore
from vckg.models import Article, Mention
from vckg.ner.span_recovery import RECOVERY_VERSION, recover_article
from vckg.pipeline import Counters, process_article
from vckg.preprocessing.text import normalize_text, split_sentences
from vckg.relation_extraction.discovery_benchmark import discover_article, head_mentions
from vckg.validation.evidence import EdgeStore
from vckg.validation.span_qa import corrected_mentions

NER_CACHE_VERSION = "ner-cache-v1"
PIPELINE_VERSION = "pipeline-6c-v1"


class NonRetryable(RuntimeError):
    """Error that a retry cannot fix (missing article, ...)."""


class LLMCallFailed(RuntimeError):
    """A live Qwen window failed (timeout / bad JSON / service down). The article is NOT marked done: results would silently lack LLM candidates."""


class CachedNER:
    """Wraps a real NER backend (lazy: the model is loaded only on a cache miss). Key = (cache version, model id, threshold, exact text)."""

    def __init__(self, path: str | Path, factory, model_id: str = "fastino/gliner2.5-multi-v1", threshold: float = 0.5):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), timeout=30)
        self.db.execute("CREATE TABLE IF NOT EXISTS ner_cache(key TEXT PRIMARY KEY, model TEXT, version TEXT, mentions TEXT, created_at TEXT)")
        self.factory, self.model_id, self.threshold = factory, model_id, threshold
        self._ner = None
        self.hits = 0
        self.live = 0

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{NER_CACHE_VERSION}|{self.model_id}|{self.threshold}|sentence|{text}".encode()).hexdigest()

    def extract_sentences(self, text: str, sentences) -> list[Mention]:
        k = self._key(text)
        row = self.db.execute("SELECT mentions FROM ner_cache WHERE key=?", (k,)).fetchone()
        if row:
            self.hits += 1
            return [Mention.model_validate(x) for x in json.loads(row[0])]
        if self._ner is None:
            self._ner = self.factory()
        out = self._ner.extract_sentences(text, sentences)
        self.live += 1
        self.db.execute("INSERT OR REPLACE INTO ner_cache VALUES(?,?,?,?,datetime('now'))",
                        (k, self.model_id, NER_CACHE_VERSION, json.dumps([m.model_dump(mode="json") for m in out], ensure_ascii=False)))
        self.db.commit()
        return out

    def close(self) -> None:
        self.db.close()


@dataclass
class Runtime:
    """Everything a stage needs. Backends are injected (real GLiNER/Qwen in production, doubles only in unit tests)."""
    store: RegistryStore
    resolver: EntityResolver
    relations: dict
    ner: object
    llm: object | None  # DiscoveryLLM-like (discover/stats/model) or None => rule-only (declared in the job config, never silent)
    staging_db: Path
    counters: Counters = field(default_factory=Counters)


def load_article(staging_db: Path, article_id: str) -> Article:
    db = sqlite3.connect(f"file:{Path(staging_db).as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        r = db.execute("SELECT * FROM articles WHERE article_id=?", (article_id,)).fetchone()
    finally:
        db.close()
    if r is None:
        raise NonRetryable(f"ARTICLE_NOT_FOUND: {article_id}")
    return Article(**{k: r[k] for k in ("article_id", "url", "source", "title", "text", "published_at", "fetched_at", "content_hash")})


def recover_and_ground(store: RegistryStore, article_id: str, text: str, ments: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    """Same logic as validation.span_qa.run for ONE article: span recovery on the baseline mentions, then article grounding on the corrected
    mentions (staging registry). -> (overlay entries, fix rows, grounding decisions). Overlay keys are the ORIGINAL mention spans."""
    fixes = recover_article(article_id, text, ments, _truncated)
    new_ments, new_by_orig = corrected_mentions(text, ments, fixes, store, article_id)
    complete = {f.original for f in fixes if f.kind == "CONFIRMED_COMPLETE"}
    decisions = ground_article(store, article_id, text, new_ments, apply=True, confirmed_complete=complete)
    store.db.commit()
    resolve = overlay_from(decisions)
    overlay: dict = dict(resolve)
    for orig, nm in new_by_orig.items():
        tgt = resolve.get(f"{article_id}|{nm['start']}|{nm['end']}") or nm["entity_id"]
        overlay[f"{article_id}|{orig[0]}|{orig[1]}"] = {"start": nm["start"], "end": nm["end"], "text": nm["text"], "label": nm["label"], "entity_id": tgt}
    return overlay, [f.as_dict() for f in fixes], [d.as_dict() for d in decisions]


def process_one(rt: Runtime, article: Article, progress=lambda stage: None, stop=lambda: False) -> dict:
    """Run all stages for one article and return its artifacts. Raises on failure (the worker isolates and retries)."""
    t0 = time.perf_counter()
    text = normalize_text(article.text)
    ner0 = (getattr(rt.ner, "hits", 0), getattr(rt.ner, "live", 0))
    progress("ner+resolve")
    res = process_article(article, rt.relations, rt.resolver, EdgeStore(), rt.ner, None, rt.counters)  # verifier=None: rule candidates only
    rt.store.db.commit()
    ments = [{"article_id": article.article_id, **m.model_dump(mode="json")} for m in res.mentions]
    progress("span_recovery+grounding")
    overlay, fixes, decisions = recover_and_ground(rt.store, article.article_id, text, ments)
    rule = [c.model_dump(mode="json") for c in res.candidates]
    chunks: list[dict] = []
    calls = hits = fails = 0
    stopped_budget = False
    if rt.llm is not None:
        progress("qwen_discovery")
        st = rt.llm.stats
        c0, h0, f0 = st.calls, st.cache_hits, st.failures
        sents = split_sentences(text)
        chunks, stopped_budget = discover_article(rt.llm, article.article_id, article.title, text, sents, head_mentions([dict(m) for m in ments]), rt.relations)
        calls, hits, fails = st.calls - c0, st.cache_hits - h0, st.failures - f0
        if stopped_budget:
            from vckg.relation_extraction.llm_discovery import BudgetExceeded
            raise BudgetExceeded("live Qwen call cap reached")
        if any(not c["ok"] for c in chunks):
            raise LLMCallFailed(f"{sum(not c['ok'] for c in chunks)} Qwen window(s) failed")
    return {"mentions": ments, "rule": rule, "chunks": chunks, "overlay": overlay, "fixes": fixes, "decisions": decisions,
            "stats": {"mentions": len(ments), "rule_candidates": len(rule), "llm_accepted": sum(len(c["accepted"]) for c in chunks), "qwen_live": calls,
                      "qwen_cached": hits, "qwen_failed": fails, "ner_cached": getattr(rt.ner, "hits", 0) - ner0[0], "ner_live": getattr(rt.ner, "live", 0) - ner0[1],
                      "windows": len(chunks), "recovery_versions": RECOVERY_VERSION, "seconds": round(time.perf_counter() - t0, 2)}}
