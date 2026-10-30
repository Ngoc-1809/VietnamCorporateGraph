"""Phase 6B.1 - LLM-assisted relation DISCOVERY (experiment; does not replace the rule-based generator).

Qwen receives a passage (several consecutive sentences), the article title, the in-scope entity mentions with ids, the allowed
predicates (ISSUED_BOND excluded: it needs a BondIssue node) and factual-status rules, and lists every relation the text states.
Every returned relation is validated deterministically before it becomes a candidate:
  mention ids must exist and be type-compatible, the quote must be a verbatim substring of the passage, both endpoints must lie in the
  evidence slice (<=2 sentences), negation drops it, the rule modality layer can only make the status stricter.
LLM-discovered candidates are candidates ONLY (direction_source='llm'); nothing here creates an official edge.
Spans: the model quotes text, offsets are derived by exact search (models are unreliable at offsets)."""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field

import httpx

from vckg.models import FactualStatus, Mention, RelationCandidate, Sentence
from vckg.reasons import quote_supported
from vckg.relation_extraction.modality import detect_modality
from vckg.relation_extraction.qwen_verifier import DIRECTION
from vckg.validation.evidence import stricter

DISCOVERY_PROMPT_VERSION = "disc-v1-2026-10-31"
PREDICATES = [p for p in DIRECTION if p != "ISSUED_BOND"]
STATUSES = ["FACT", "PLANNED", "ALLEGED", "HISTORICAL", "ENDED", "UNKNOWN"]
MAX_PASSAGE_CHARS = 1400
MAX_WINDOWS_PER_ARTICLE = 3
SCHEMA = {
    "type": "object", "required": ["relations"],
    "properties": {"relations": {"type": "array", "items": {
        "type": "object",
        "required": ["subject_mention_id", "subject_text", "object_mention_id", "object_text", "predicate", "evidence_text", "factual_status", "discovery_reason"],
        "properties": {
            "subject_mention_id": {"type": "string"}, "subject_text": {"type": "string"},
            "object_mention_id": {"type": "string"}, "object_text": {"type": "string"},
            "predicate": {"type": "string", "enum": PREDICATES},
            "evidence_text": {"type": "string"},
            "factual_status": {"type": "string", "enum": STATUSES},
            "discovery_reason": {"type": "string", "maxLength": 200}}}}}}

SYSTEM = (
    "You extract relations between entities from ONE passage of a Vietnamese financial news article. Use ONLY the passage. "
    "List every relation the passage explicitly states between two of the listed mentions; return an empty list if there is none. "
    "Never use outside knowledge. Never infer a relation because two entities merely appear together. Do not invent entities. "
    "Each relation: subject_mention_id and object_mention_id MUST be ids from the mention list (use \"NONE\" for an endpoint only if the passage clearly "
    "names it but it is not listed, then give its exact text in subject_text/object_text; otherwise leave the text fields empty). "
    "predicate must follow its direction rule. evidence_text MUST be copied verbatim from the passage (one sentence or a contiguous part of it). "
    "factual_status: FACT (stated as true/completed), PLANNED (future, proposed, negotiating, not completed), ALLEGED (accused, suspected, under "
    "investigation), HISTORICAL (past role/relation; 'nguyên', 'cựu', 'từng', tenure range ending in the past), ENDED (explicitly ended: resigned, dismissed), "
    "UNKNOWN. Do NOT list negated or denied relations. A planned deal is PLANNED, not FACT. 'Khởi tố' means charged/prosecuted, never convicted. "
    "A relative's role is not the subject's role. discovery_reason: one short sentence.")


def _dir_text() -> str:
    return "\n".join(f"- {p}: {DIRECTION[p]}" for p in PREDICATES)


# ------------------------------------------------------------------------------------------------ passages
def window_sentences(sentences: list[Sentence], mentions: list[dict], cue_rx: re.Pattern, max_chars: int = MAX_PASSAGE_CHARS) -> list[dict]:
    """Greedy windows of consecutive sentences (<= max_chars). Keeps windows with >=2 in-scope head mentions, ranked by cue sentences."""
    by_s: dict[int, list[dict]] = {}
    for m in mentions:
        if m["sentence_index"] is not None:
            by_s.setdefault(m["sentence_index"], []).append(m)
    wins, cur = [], []
    for s in sentences:
        if cur and s.end - cur[0].start > max_chars:
            wins.append(cur)
            cur = []
        cur.append(s)
    if cur:
        wins.append(cur)
    out = []
    for i, w in enumerate(wins):
        ms = [m for s in w for m in by_s.get(s.index, [])]
        ents = {m["entity_id"] or m["text"] for m in ms}
        if len(ms) < 2 or len(ents) < 2:
            continue
        cues = sum(1 for s in w if cue_rx.search(s.text))
        out.append({"index": i, "start": w[0].start, "end": w[-1].end, "sentences": [s.index for s in w], "cue_sentences": cues,
                    "n_mentions": len(ms), "score": cues * 100 + min(len(ents), 40)})
    return out


def select_windows(wins: list[dict], k: int = MAX_WINDOWS_PER_ARTICLE) -> tuple[list[dict], int]:
    """Top-k by score, returned in document order. Also returns the number of eligible windows left unexamined."""
    chosen = sorted(sorted(wins, key=lambda w: (-w["score"], w["start"]))[:k], key=lambda w: w["start"])
    return chosen, len(wins) - len(chosen)


def build_user_prompt(title: str, passage: str, mentions: list[dict]) -> str:
    ml = "\n".join(f'{m["mid"]} | "{m["text"]}" | {m["label"]}' for m in mentions)
    return (f"Article title: {title}\n\nPassage:\n{passage}\n\nMentions (id | text | type):\n{ml}\n\nAllowed predicates and direction (subject -> object):\n{_dir_text()}\n\n"
            "Return JSON {\"relations\": [...]}; an empty list is a valid answer.")


# ------------------------------------------------------------------------------------------------ LLM client
class BudgetExceeded(RuntimeError):
    pass


@dataclass
class DiscoveryStats:
    calls: int = 0
    cache_hits: int = 0
    failures: int = 0
    prompt_tokens: int = 0
    eval_tokens: int = 0
    latency: float = 0.0
    per_call: list[float] = field(default_factory=list)


class DiscoveryLLM:
    def __init__(self, cache, model: str = "qwen3.5:9b", host: str = "http://127.0.0.1:11434", max_live_calls: int = 180, timeout: float = 240.0):
        self.cache, self.model, self.host, self.timeout, self.max_live = cache, model, host.rstrip("/"), timeout, max_live_calls
        self.stats = DiscoveryStats()
        self.prompt_version = DISCOVERY_PROMPT_VERSION

    def available(self) -> bool:
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=5)
            return r.status_code == 200 and any(m["name"] == self.model for m in r.json().get("models", []))
        except httpx.HTTPError:
            return False

    def discover(self, title: str, passage: str, mentions: list[dict]) -> dict | None:
        user = build_user_prompt(title, passage, mentions)
        key = hashlib.sha256(f"disc|{self.model}|{self.prompt_version}|{user}".encode()).hexdigest()
        hit = self.cache.get(key)
        if hit:
            self.stats.cache_hits += 1
            return {"parsed": json.loads(hit), "cached": True, "usage": {}}
        if self.stats.calls >= self.max_live:
            raise BudgetExceeded(f"live Qwen calls reached the cap ({self.max_live})")
        payload = {"model": self.model, "stream": False, "think": False, "format": SCHEMA, "keep_alive": "10m",
                   "options": {"temperature": 0, "seed": 7, "num_ctx": 8192},
                   "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
        t0 = time.perf_counter()
        try:
            r = httpx.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            r.raise_for_status()
            body = r.json()
            content = body["message"]["content"]
            parsed = json.loads(content)
            if not isinstance(parsed.get("relations"), list):
                raise TypeError("schema")
        except (httpx.HTTPError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            self.stats.failures += 1
            self.stats.calls += 1  # a failed live attempt still consumed an inference
            return None
        dt = time.perf_counter() - t0
        pt, et = int(body.get("prompt_eval_count", 0)), int(body.get("eval_count", 0))
        s = self.stats
        s.calls += 1
        s.latency += dt
        s.prompt_tokens += pt
        s.eval_tokens += et
        s.per_call.append(dt)
        self.cache.put(key, self.model, self.prompt_version, content, dt * 1000, pt, et)
        return {"parsed": parsed, "cached": False, "usage": {"prompt_tokens": pt, "eval_tokens": et, "seconds": round(dt, 2)}}


# ------------------------------------------------------------------------------------------------ validation
def _sentence_of(sentences: list[Sentence], pos: int) -> Sentence:
    for s in sentences:
        if s.start <= pos < s.end:
            return s
    return sentences[-1]


def _nearest_occurrence(m: dict, mentions: dict[str, dict], q0: int, q1: int) -> dict:
    """The model may cite an earlier occurrence of the same entity; use the occurrence of that SAME entity closest to the quote."""
    same = [x for x in mentions.values() if (m.get("entity_id") and x.get("entity_id") == m["entity_id"]) or (not m.get("entity_id") and x["text"] == m["text"])]
    return min(same or [m], key=lambda x: 0 if (x["start"] < q1 and q0 < x["end"]) else min(abs(x["start"] - q1), abs(q0 - x["end"])))


def validate_relation(rel: dict, text: str, win: dict, sentences: list[Sentence], mentions: dict[str, dict], relations: dict,
                      article_id: str) -> tuple[dict | None, str]:
    """-> (candidate dict | None, reject_reason or 'OK'). Candidate dict holds a RelationCandidate plus discovery metadata."""
    pred = rel.get("predicate")
    if pred not in relations or pred == "ISSUED_BOND":
        return None, "BAD_PREDICATE"
    spec = relations[pred]
    quote = (rel.get("evidence_text") or "").strip()
    seg = text[win["start"]:win["end"]]
    if not quote:
        return None, "EVIDENCE_NOT_VERBATIM"
    if quote in seg:
        q0 = win["start"] + seg.index(quote)
        q1 = q0 + len(quote)
    else:  # tolerate dropped asides / trailing ellipsis: ordered word-subsequence of ONE sentence (same rule as the LLM-quote rule elsewhere)
        core = quote.strip(" .…")
        host = next((s for s in sentences if win["start"] <= s.start and s.end <= win["end"] and quote_supported(core, s.text) and len(core.split()) >= 4), None)
        if host is None:
            return None, "EVIDENCE_NOT_VERBATIM"
        q0, q1 = host.start, host.end
    sid, oid = rel.get("subject_mention_id"), rel.get("object_mention_id")
    unresolved = []
    ends = {}
    for role, mid, mt in (("subject", sid, rel.get("subject_text", "")), ("object", oid, rel.get("object_text", ""))):
        if mid in mentions:
            ends[role] = _nearest_occurrence(mentions[mid], mentions, q0, q1)
        elif mid == "NONE" and mt and mt in seg and (True):
            i = win["start"] + seg.index(mt)
            ends[role] = {"mid": "NONE", "text": mt, "start": i, "end": i + len(mt), "label": None, "entity_id": None, "unresolved": True}
            unresolved.append(role)
        else:
            return None, "UNKNOWN_MENTION_ID"
    s_m, o_m = ends["subject"], ends["object"]
    if s_m["start"] == o_m["start"] or (s_m.get("entity_id") and s_m["entity_id"] == o_m.get("entity_id")):
        return None, "SELF_LOOP"
    if not unresolved:
        ok = s_m["label"] in spec["subject"] and o_m["label"] in spec["object"]
        if not ok and spec.get("symmetric"):
            ok = o_m["label"] in spec["subject"] and s_m["label"] in spec["object"]
        if not ok:
            return None, "TYPE_MISMATCH"
    lo = min(q0, s_m["start"], o_m["start"])
    hi = max(q1, s_m["end"], o_m["end"])
    first, last = _sentence_of(sentences, lo), _sentence_of(sentences, hi - 1)
    if last.index - first.index > 1 or last.end - first.start > 700:
        return None, "ENDPOINT_FAR_FROM_QUOTE"
    ev_start, ev_end = first.start, last.end
    if not (ev_start <= s_m["start"] and s_m["end"] <= ev_end and ev_start <= o_m["start"] and o_m["end"] <= ev_end):
        return None, "ENDPOINT_NOT_IN_EVIDENCE"
    ev_text = text[ev_start:ev_end]
    model_status = FactualStatus(rel["factual_status"]) if rel.get("factual_status") in STATUSES else FactualStatus.UNKNOWN
    rule_status, cues = detect_modality(ev_text, lo - ev_start, hi - ev_start)
    if rule_status == FactualStatus.DENIED:
        return None, "NEGATED"
    status = stricter(model_status, rule_status)
    if unresolved:
        return {"unresolved": True, "article_id": article_id, "predicate": pred, "subject": s_m, "object": o_m, "evidence_text": ev_text,
                "evidence_start": ev_start, "evidence_end": ev_end, "llm_quote": quote, "factual_status": status.value,
                "model_status": model_status.value, "rule_status": rule_status.value, "reason": rel.get("discovery_reason", "")}, "OK"

    def mk(m):
        return Mention.model_validate({"text": m["text"], "start": m["start"], "end": m["end"], "label": m["label"], "article_id": article_id,
                                       "entity_id": m["entity_id"], "link_status": m["link_status"], "linking_method": m["linking_method"],
                                       "ner_score": m.get("ner_score"), "method": m.get("method", "gliner2.5"), "sentence_index": m.get("sentence_index")})
    cid = hashlib.sha1(f"{article_id}|{pred}|{s_m['start']}|{o_m['start']}|LLM".encode()).hexdigest()[:16]
    cand = RelationCandidate(candidate_id=cid, article_id=article_id, subject=mk(s_m), object=mk(o_m), predicate=pred, sentence_index=first.index,
                             evidence_text=ev_text, evidence_start=ev_start, evidence_end=ev_end, cue=quote, pattern_id="LLM.discovery",
                             direction_source="llm", factual_status=status, modality_cues=cues, method="llm")
    return {"unresolved": False, "candidate": cand, "llm_quote": quote, "model_status": model_status.value, "rule_status": rule_status.value,
            "reason": rel.get("discovery_reason", "")}, "OK"

