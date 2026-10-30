"""Qwen3.5 relation verifier (Ollama /api/chat, JSON-schema constrained output) with a persistent cache.

The LLM is a *verifier of rule-generated candidates*: it can reject, or confirm and give status/dates, but it can
neither add relations that the sentence does not state nor override deterministic findings (see EdgeStore).
Its self-reported confidence is deliberately not part of the contract."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from pydantic import ValidationError

from vckg.models import RelationCandidate, Verdict

PROMPT_VERSION = "v4-2026-10-30"

SYSTEM = (
    "You verify ONE candidate relation between two entities in ONE Vietnamese financial-news sentence. "
    "Use ONLY that sentence. Never infer, never use outside knowledge. "
    "valid means: the sentence explicitly addresses this relation between exactly these two entity strings, EVEN IF it says the "
    "relation has ended (resigned), is planned, is alleged, or is denied - report that in factual_status and keep valid=true. "
    "A deputy chair (Phó Chủ tịch) of the board is a board member; a resignation from a board seat is an ENDED board membership. "
    "If the sentence does not explicitly state the relation between exactly these two entity strings, return "
    "valid=false, relation_type=NO_RELATION, rejection_reason=NO_RELATION. Mere co-mention is NO_RELATION. "
    "A person who 'once worked at' / 'was previously at' a company is NOT its chair or CEO unless the sentence says so. "
    "If an entity string is only a part of a longer legal name in the sentence (a different company such as a "
    "country subsidiary), return valid=false, rejection_reason=SPAN_ERROR. "
    "subject_mention and object_mention must each be copied EXACTLY from the two entity strings given. They must follow "
    "the predicate direction rule. direction=AS_LISTED when Entity 1 is the subject, REVERSED when Entity 2 is the subject. "
    "evidence_text must be a verbatim substring of the sentence that states the relation. "
    "factual_status: FACT (stated as true/happened), PLANNED (future, proposed, negotiating, not completed), "
    "DENIED (the sentence negates or denies the relation), ALLEGED (accused, suspected, under investigation), "
    "HISTORICAL (past relation not described as ended by an event), ENDED (explicitly ended: resigned, dismissed, terminated), UNKNOWN. "
    "valid_from / valid_to only when a date is explicit in the sentence, else null. reason: at most one short sentence."
)

DIRECTION = {
    "CHAIR_OF": "subject = the person who is chair, object = the organization",
    "CEO_OF": "subject = the person who is CEO/general director, object = the organization",
    "BOARD_MEMBER_OF": "subject = the person on the board, object = the organization",
    "FOUNDED": "subject = founder, object = organization founded",
    "OWNS_SHARES_IN": "subject = shareholder, object = company whose shares are held",
    "SUBSIDIARY_OF": "subject = the subsidiary, object = the parent",
    "ACQUIRED": "subject = acquirer, object = target",
    "LENDS_TO": "subject = lender (bank), object = borrower",
    "ISSUED_BOND": "subject = issuer",
    "JOINT_VENTURE_WITH": "symmetric",
    "PARTNERS_WITH": "symmetric",
    "SANCTIONED_BY": "subject = the sanctioned party, object = the sanctioning authority",
    "PROSECUTED_BY": "subject = the accused (prosecution/charging, not conviction), object = the authority",
}
REJECTIONS = ["NONE", "NO_RELATION", "WRONG_DIRECTION", "NEGATED", "NOT_FACTUAL", "WRONG_ENTITY", "SPAN_ERROR", "OTHER"]
STATUSES = ["FACT", "PLANNED", "DENIED", "ALLEGED", "HISTORICAL", "ENDED", "UNKNOWN"]


def verdict_schema(predicates: list[str]) -> dict:
    sch = Verdict.model_json_schema()
    props = sch["properties"]
    props["relation_type"] = {"type": "string", "enum": [*predicates, "NO_RELATION"]}
    props["direction"] = {"type": "string", "enum": ["AS_LISTED", "REVERSED"]}
    props["rejection_reason"] = {"type": "string", "enum": REJECTIONS}
    props["factual_status"] = {"type": "string", "enum": STATUSES}
    sch.pop("$defs", None)
    return sch


def build_prompt(c: RelationCandidate) -> str:
    return (
        f"Sentence: {c.evidence_text}\n"
        f"Entity 1: {c.subject.text} (type {c.subject.label.value})\n"
        f"Entity 2: {c.object.text} (type {c.object.label.value})\n"
        f"Predicate: {c.predicate}. Direction rule: {DIRECTION.get(c.predicate, '')}.\n"
        f"The rule-based extractor proposes: subject = Entity 1, object = Entity 2 (matched cue: \"{c.cue}\").\n"
        f"Return the JSON verdict; relation_type must be \"{c.predicate}\" or NO_RELATION."
    )


class OllamaUnavailable(RuntimeError):
    pass


@dataclass
class LLMStats:
    calls: int = 0
    cache_hits: int = 0
    parse_failures: int = 0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    eval_tokens: int = 0
    per_call_ms: list[float] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"llm_calls": self.calls, "cache_hits": self.cache_hits, "parse_failures": self.parse_failures,
                "total_llm_latency_s": round(self.latency_ms / 1000, 2),
                "mean_latency_ms": round(self.latency_ms / self.calls, 1) if self.calls else None,
                "prompt_tokens": self.prompt_tokens, "completion_tokens": self.eval_tokens}


class LLMCache:
    def __init__(self, path: str | Path = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.execute("CREATE TABLE IF NOT EXISTS llm_cache(key TEXT PRIMARY KEY, model TEXT, prompt_version TEXT, "
                        "response TEXT, latency_ms REAL, prompt_tokens INTEGER, eval_tokens INTEGER, created_at TEXT)")

    def get(self, key: str) -> str | None:
        r = self.db.execute("SELECT response FROM llm_cache WHERE key=?", (key,)).fetchone()
        return r[0] if r else None

    def put(self, key: str, model: str, version: str, response: str, ms: float, pt: int, et: int) -> None:
        self.db.execute("INSERT OR REPLACE INTO llm_cache VALUES(?,?,?,?,?,?,?,datetime('now'))", (key, model, version, response, ms, pt, et))
        self.db.commit()


class QwenVerifier:
    def __init__(self, model: str = "qwen3.5:9b", host: str = "http://127.0.0.1:11434", timeout: float = 180.0,
                 num_ctx: int = 4096, keep_alive: str = "10m", predicates: list[str] | None = None,
                 cache: LLMCache | None = None):
        self.model, self.host, self.timeout = model, host.rstrip("/"), timeout
        self.options = {"temperature": 0, "num_ctx": num_ctx, "seed": 7}
        self.keep_alive = keep_alive
        self.prompt_version = PROMPT_VERSION
        self.schema = verdict_schema(predicates or list(DIRECTION))
        self.cache = cache
        self.stats = LLMStats()

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=5)
            return r.status_code == 200 and any(m["name"] == self.model for m in r.json().get("models", []))
        except httpx.HTTPError:
            return False

    def cache_key(self, c: RelationCandidate) -> str:
        raw = f"{self.model}|{self.prompt_version}|{c.evidence_text}|{c.subject.text}|{c.subject.label.value}|{c.object.text}|{c.object.label.value}|{c.predicate}|{c.cue}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _parse(self, content: str) -> Verdict | None:
        try:
            return Verdict.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError):
            return None

    def verify(self, c: RelationCandidate, definition: str = "", retries: int = 1) -> Verdict | None:
        key = self.cache_key(c)
        if self.cache:
            hit = self.cache.get(key)
            if hit is not None:
                v = self._parse(hit)
                if v is not None:
                    self.stats.cache_hits += 1
                    return v
        payload = {"model": self.model, "stream": False, "think": False, "format": self.schema, "options": self.options,
                   "keep_alive": self.keep_alive,
                   "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": build_prompt(c)}]}
        for _ in range(retries + 1):
            t0 = time.perf_counter()
            try:
                r = httpx.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
                r.raise_for_status()
            except httpx.HTTPError as e:
                raise OllamaUnavailable(str(e)) from e
            ms = (time.perf_counter() - t0) * 1000
            body = r.json()
            pt, et = int(body.get("prompt_eval_count", 0)), int(body.get("eval_count", 0))
            self.stats.calls += 1
            self.stats.latency_ms += ms
            self.stats.per_call_ms.append(ms)
            self.stats.prompt_tokens += pt
            self.stats.eval_tokens += et
            content = body["message"]["content"]
            v = self._parse(content)
            if v is not None:
                if self.cache:
                    self.cache.put(key, self.model, self.prompt_version, content, ms, pt, et)
                return v
            self.stats.parse_failures += 1
        return None

