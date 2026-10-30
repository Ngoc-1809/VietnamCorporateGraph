"""Phase 6A - automated edge quality control for OFFICIAL edges.

original edge -> per-evidence audit (deterministic checks + Qwen cross-check) -> safe correction (only lexically/structurally
provable) -> revalidation -> final decision PASS | AUTO_CORRECT | QUARANTINE | REJECT.

Safety rules
 * Qwen can only DOWNGRADE (PASS -> QUARANTINE). It never accepts an edge on its own, never causes REJECT, never creates a correction.
 * Anything that cannot be verified (evidence unreachable, mention not found, LLM required but unavailable) -> QUARANTINE (fail-safe).
 * Corrections are limited to: factual_status (lexical proof), direction (type proof), predicate (Pho Chu tich), duplicate evidence,
   duplicate BondIssue (same issuer + same code + arithmetic proof). No dates are inferred, persons are never merged by name.
 * The input is never modified; every result stores original edge, proposed correction, checks passed/failed, timestamp, model/prompt.
Entry point: python -m vckg.validation.auto_auditor --out reports/phase6/auto_qa [--no-llm] [--fresh]"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx

from vckg.entity_linking.normalize import normalize_name
from vckg.models import FactualStatus, Mention
from vckg.preprocessing.text import normalize_text, split_sentences
from vckg.relation_extraction.candidates import generate_candidates, load_config, load_relations
from vckg.relation_extraction.modality import detect_modality

ROOT = Path(__file__).resolve().parents[3]
AUDITOR_VERSION = "auto-auditor-v1"
LLM_PROMPT_VERSION = "audit-v1-2026-10-31"
ROLE_PREDS = {"CHAIR_OF", "CEO_OF", "BOARD_MEMBER_OF"}
OFFICIAL_STATUS = {"FACT", "HISTORICAL", "ENDED"}

_KIN = re.compile(r"\b(vợ|chồng|con gái|con trai|con|cha|bố|mẹ|anh trai|em trai|chị gái|em gái|chị dâu|anh rể|em dâu)\b", re.IGNORECASE)
_TENURE = re.compile(r"trong giai đoạn từ[^.;]{0,50}?\bđến\b", re.IGNORECASE)
_ENDED = re.compile(r"\bđã\s+(?:thôi giữ chức|từ nhiệm|miễn nhiệm|nghỉ hưu|rời)\b", re.IGNORECASE)
_FORMER = re.compile(r"\b(?:nguyên|cựu|từng là|từng giữ)\b", re.IGNORECASE)
_RESIGN_REQ = re.compile(r"(?:đơn\s+)?xin\s+từ nhiệm|đề nghị\s+từ nhiệm|dự kiến\s+từ nhiệm|có đơn\s+từ nhiệm", re.IGNORECASE)
_CRIMINAL = re.compile(r"\b(?:vụ án|bản án|bị cáo|bị can|thi hành án|bị bắt|bị khởi tố|bị truy tố|lừa đảo|bồi hoàn)\b", re.IGNORECASE)
_CONVICT = re.compile(r"\b(?:kết án|tuyên phạt|tuyên án|bị tuyên|phạt tù|mức án|án tù)\b", re.IGNORECASE)
_ALLEGED = re.compile(r"\b(?:bị cáo buộc|cáo buộc|nghi vấn|nghi ngờ)\b", re.IGNORECASE)
_CAPTION = re.compile(r"Ảnh\s*:|\(đứng giữa\)|\(bên (?:trái|phải)\)", re.IGNORECASE)
_PROS_VERB = re.compile(r"khởi tố|truy tố|bắt tạm giam|\bbắt\b", re.IGNORECASE)
_SANC_VERB = re.compile(r"xử phạt|\bphạt\b|đình chỉ|cảnh cáo", re.IGNORECASE)
_CODE = re.compile(r"[A-Z]{2,5}\d{2}[A-Z0-9.\-]{2,}|[A-Z0-9]{3,}[-.]\d{4}[A-Z0-9.\-]*")
_AMOUNT = re.compile(r"\d[\d.,]*(?:nghìntỷ|tỷđồng|tỷusd|triệuusd|triệuđồng)", re.IGNORECASE)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _nospace(s: str) -> str:
    return re.sub(r"\s+", "", s.lower())


# ---------------------------------------------------------------------------------------------- context
@dataclass
class Context:
    article_text: callable           # article_id -> normalized text | None
    mentions: callable               # article_id -> list[dict]
    canon: callable                  # entity_id -> canonical (merge-resolved) id
    info: dict                       # entity_id -> {name,type,status}
    aliases: callable                # entity_id -> set[alias_key]
    relations: dict
    status_policy: dict = field(default_factory=lambda: {"FACT": "official", "HISTORICAL": "official", "ENDED": "official"})
    _cache: dict = field(default_factory=dict)

    def generated(self, article_id: str) -> list:
        if article_id not in self._cache:
            text = self.article_text(article_id)
            ms = [Mention.model_validate({k: v for k, v in m.items()}) for m in self.mentions(article_id)]
            sents = split_sentences(text) if text else []
            self._cache[article_id] = generate_candidates(sents, ms, self.relations, article_id, text) if text else []
        return self._cache[article_id]


def build_context(run_dirs: list[Path], registries: list[Path], staging_db: Path, merges: list[dict] | None = None) -> Context:
    from vckg.graph.neo4j_sync import registry_info
    from vckg.storage.sqlite import Staging
    arts = {a.article_id: normalize_text(a.text) for a in Staging(staging_db).get_articles()}
    ments: dict[str, list[dict]] = defaultdict(list)
    for d in run_dirs:
        for line in (d / "entities.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                m = json.loads(line)
                ments[m["article_id"]].append(m)
    info: dict = {}
    parent: dict[str, str] = {}
    alias_rows: dict[str, set[str]] = defaultdict(set)
    for reg in registries:
        info.update(registry_info(reg))
        db = sqlite3.connect(str(reg))
        parent.update({a: b for a, b in db.execute("SELECT entity_id, merged_into FROM entities WHERE merged_into IS NOT NULL")})
        for eid, key in db.execute("SELECT entity_id, alias_key FROM aliases"):
            alias_rows[eid].add(key)
        db.close()
    for mg in merges or []:
        parent[mg["drop"]] = mg["keep"]

    def canon(x: str) -> str:
        seen = set()
        while x in parent and x not in seen:
            seen.add(x)
            x = parent[x]
        return x

    def aliases(eid: str) -> set[str]:
        c = canon(eid)
        out = set()
        for k, v in alias_rows.items():
            if canon(k) == c:
                out |= v
        return out
    cfg = str(ROOT / "config/relations.yaml")
    return Context(arts.get, lambda a: ments.get(a, []), canon, info, aliases, load_relations(cfg), load_config(cfg).get("status_policy", {}))


# ---------------------------------------------------------------------------------------------- LLM cross-check
SCHEMA = {"type": "object", "required": ["subject_holds_relation", "relation_tense", "belongs_to_other_person", "evidence_sufficient", "note"],
          "properties": {"subject_holds_relation": {"type": "boolean"},
                         "relation_tense": {"type": "string", "enum": ["CURRENT", "PAST", "ENDED", "PLANNED", "NEGATED", "UNKNOWN"]},
                         "belongs_to_other_person": {"type": "boolean"}, "evidence_sufficient": {"type": "boolean"},
                         "note": {"type": "string", "maxLength": 200}}}
SYSTEM = ("You audit ONE extracted relation against ONE Vietnamese news sentence. Use only the sentence. Answer the questions literally. "
          "subject_holds_relation: does the sentence state that exactly this SUBJECT has this relation to the OBJECT (not another person/company, "
          "not a relative)? relation_tense: CURRENT (holds now), PAST (held in the past, e.g. 'nguyên', 'trong giai đoạn từ..đến'), ENDED "
          "(explicitly ended), PLANNED, NEGATED, UNKNOWN. belongs_to_other_person: true if the role/ownership is stated for someone else "
          "(e.g. a relative) rather than the subject. evidence_sufficient: false if the sentence is only a caption/fragment or does not clearly state it. "
          "Never use outside knowledge.")


class AuditLLM:
    def __init__(self, model: str = "qwen3.5:9b", host: str = "http://127.0.0.1:11434", cache_path: Path | None = None, timeout: float = 120.0):
        from vckg.relation_extraction.qwen_verifier import LLMCache
        self.model, self.host, self.timeout = model, host.rstrip("/"), timeout
        self.cache = LLMCache(cache_path or ROOT / "data/staging/llm_cache.sqlite")
        self.calls = self.hits = self.failures = 0
        self.latency = 0.0

    def available(self) -> bool:
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=5)
            return r.status_code == 200 and any(m["name"] == self.model for m in r.json().get("models", []))
        except httpx.HTTPError:
            return False

    def check(self, sentence: str, subj: str, obj: str, pred: str, status: str) -> dict | None:
        key = hashlib.sha256(f"audit|{self.model}|{LLM_PROMPT_VERSION}|{sentence}|{subj}|{obj}|{pred}|{status}".encode()).hexdigest()
        hit = self.cache.get(key)
        if hit:
            self.hits += 1
            return json.loads(hit)
        user = (f"Sentence: {sentence}\nSUBJECT: {subj}\nOBJECT: {obj}\nRelation: {pred} (SUBJECT -> OBJECT); current label: {status}\n"
                "Return the JSON audit.")
        payload = {"model": self.model, "stream": False, "think": False, "format": SCHEMA, "options": {"temperature": 0, "seed": 7, "num_ctx": 4096},
                   "keep_alive": "10m", "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
        t0 = time.perf_counter()
        try:
            r = httpx.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            r.raise_for_status()
            content = r.json()["message"]["content"]
            out = json.loads(content)
            if not all(k in out for k in SCHEMA["required"]):
                raise ValueError("schema")
        except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError):
            self.failures += 1
            return None
        self.latency += time.perf_counter() - t0
        self.calls += 1
        self.cache.put(key, self.model, LLM_PROMPT_VERSION, content, 0.0, 0, 0)
        return out


# ---------------------------------------------------------------------------------------------- per-evidence audit
def _find(mentions: list[dict], ev: dict, ent: str, ctx: Context) -> list[dict]:
    c = ctx.canon(ent)
    return [m for m in mentions if m["start"] >= ev["evidence_start"] and m["end"] <= ev["evidence_end"] and m.get("entity_id") and ctx.canon(m["entity_id"]) == c]


def _types_ok(spec: dict, s_label: str, o_label: str) -> bool:
    return s_label in spec["subject"] and o_label in spec["object"]


def audit_evidence(edge: dict, ev: dict, ctx: Context, llm: AuditLLM | None, llm_required: bool) -> dict:
    """Returns {status: OK|WEAK|QUAR|REJECT, passed:[], failed:[], reasons:[], corrections:{}, notes:[], llm:{}|None}."""
    R = {"status": "OK", "passed": [], "failed": [], "reasons": [], "corrections": {}, "notes": [], "llm": None, "article_id": ev["article_id"]}
    pred, sid, oid = edge["predicate"], edge["subject_id"], edge["object_id"]
    spec = ctx.relations[pred]

    def quar(code, why):
        R["failed"].append(code)
        R["reasons"].append(f"{code}: {why}")
        if R["status"] == "OK":
            R["status"] = "QUAR"

    def reject(code, why):
        R["failed"].append(code)
        R["reasons"].append(f"{code}: {why}")
        R["status"] = "REJECT"

    # 1. evidence reachable and exact (fail-safe)
    text = ctx.article_text(ev["article_id"])
    if not text or not ev.get("source_url"):
        quar("EVIDENCE_UNREACHABLE", "article text or URL missing")
        return R
    if text[ev["evidence_start"]:ev["evidence_end"]] != ev["evidence_text"]:
        quar("EVIDENCE_MISMATCH", "stored evidence does not match article text at offsets")
        return R
    R["passed"].append("evidence_exact_match")
    etxt = ev["evidence_text"]
    # 2. caption / fragment
    if len(etxt.strip()) < 40 or etxt.lstrip().startswith("|") or _CAPTION.search(etxt):
        R["status"] = "WEAK"
        R["failed"].append("EVIDENCE_CAPTION_OR_SHORT")
        R["reasons"].append("EVIDENCE_CAPTION_OR_SHORT: caption/fragment is not accepted as sole support")
        return R
    R["passed"].append("evidence_is_full_sentence")
    ments = ctx.mentions(ev["article_id"])
    sm = _find(ments, ev, sid, ctx)
    om = _find(ments, ev, oid, ctx) if pred != "ISSUED_BOND" else []
    status = ev["factual_status"]
    # 3. mentions of both endpoints present in the evidence
    if not sm:
        quar("SUBJECT_MENTION_NOT_FOUND", "no mention linked to subject entity inside evidence span")
        return R
    if pred != "ISSUED_BOND" and not om:
        quar("OBJECT_MENTION_NOT_FOUND", "no mention linked to object entity inside evidence span")
        return R
    R["passed"].append("endpoint_mentions_found")
    if pred == "ISSUED_BOND":
        return _audit_bond(edge, ev, sm, ctx, R, quar, reject, llm, llm_required)
    pair = min(((a, b) for a in sm for b in om), key=lambda p: abs(p[0].get("start") - p[1].get("start")))
    s_m, o_m = pair
    # 4. types / direction
    if _types_ok(spec, s_m["label"], o_m["label"]):
        R["passed"].append("types_and_direction_valid")
    elif _types_ok(spec, o_m["label"], s_m["label"]) and not spec.get("symmetric"):
        R["corrections"]["direction"] = "SWAP"
        R["notes"].append("types valid only in reversed direction")
    else:
        reject("INVALID_ENTITY_TYPES", f"{s_m['label']}/{o_m['label']} fit neither direction of {pred}")
        return R
    # 5. segment between endpoints
    a, b = (s_m, o_m) if s_m["start"] <= o_m["start"] else (o_m, s_m)
    seg = text[a["end"]:b["start"]]
    others = [m for m in ments if m["label"] == "PERSON" and a["end"] <= m["start"] and m["end"] <= b["start"]
              and m.get("entity_id") and ctx.canon(m["entity_id"]) not in (ctx.canon(sid), ctx.canon(oid)) and m.get("alias_of") is None]
    if others and pred in ROLE_PREDS | {"OWNS_SHARES_IN"}:
        quar("OTHER_PERSON_BETWEEN", f"another person '{others[0]['text']}' stands between subject and object (relation may belong to them)")
    elif _KIN.search(seg) and pred in ROLE_PREDS | {"OWNS_SHARES_IN", "FOUNDED"}:
        quar("KINSHIP_BETWEEN_ENDPOINTS", "kinship term between subject and object (possible wrong person)")
    else:
        R["passed"].append("no_wrong_person_signal")
        if _KIN.search(text[max(0, s_m["start"] - 14):s_m["start"]]):
            R["notes"].append("subject introduced via kinship phrase; role cue follows subject directly")
    # 6. structural reproduction of the relation (no inference beyond the text)
    if "direction" not in R["corrections"]:
        gen = [c for c in ctx.generated(ev["article_id"]) if c.predicate == pred and c.evidence_start == ev["evidence_start"]
               and ctx.canon(c.subject.entity_id or "") == ctx.canon(sid) and ctx.canon(c.object.entity_id or "") == ctx.canon(oid)]
        if gen:
            R["passed"].append("pattern_reproduces_relation")
        else:
            quar("RELATION_NOT_REPRODUCED", "no structural pattern re-derives this relation from the sentence (possible inference)")
    # 7. predicate mapping
    if pred == "CHAIR_OF" and re.search(r"phó\s+chủ tịch", seg + text[max(0, a["start"] - 40):a["start"]], re.IGNORECASE) \
            and not re.search(r"(?<!phó )(?<!phó\s)chủ tịch", seg, re.IGNORECASE) and not re.search(r"(?<!phó )chủ tịch", text[max(0, a["start"] - 25):a["start"]], re.IGNORECASE):
        R["corrections"]["predicate"] = "BOARD_MEMBER_OF"
    # 8. temporal / modality
    lo, hi = min(s_m["start"], o_m["start"]) - ev["evidence_start"], max(s_m["end"], o_m["end"]) - ev["evidence_start"]
    mod, cues = detect_modality(etxt, lo, hi)
    new_status = status
    if mod == FactualStatus.DENIED:
        reject("NEGATED_RELATION", f"negation cue {cues}")
        return R
    if _RESIGN_REQ.search(etxt) and pred in ROLE_PREDS:
        quar("RESIGNATION_REQUEST_ONLY", "resignation requested/submitted, not stated as effective")
    elif _TENURE.search(etxt) and pred in ROLE_PREDS:
        new_status = "HISTORICAL"
    elif _ENDED.search(etxt) and pred in ROLE_PREDS:
        new_status = "ENDED"
    elif mod in (FactualStatus.HISTORICAL, FactualStatus.ENDED) and status == "FACT" or mod in (FactualStatus.PLANNED, FactualStatus.ALLEGED) and status == "FACT":
        new_status = mod.value
    if _FORMER.search(etxt[max(0, lo - 30):hi + 5]) and new_status == "FACT" and pred in ROLE_PREDS:
        new_status = "HISTORICAL"
    if new_status != status:
        R["corrections"]["factual_status"] = new_status
    elif "RESIGNATION_REQUEST_ONLY" not in R["failed"]:
        R["passed"].append("temporal_status_consistent")
    if pred in ROLE_PREDS and _CRIMINAL.search(etxt) and new_status == "FACT":
        quar("ROLE_IN_CRIMINAL_CONTEXT", "role is mentioned inside a criminal-case sentence; tenure/time not established")
    # 9. enforcement semantics
    if pred == "PROSECUTED_BY":
        if not _PROS_VERB.search(etxt):
            quar("PROSECUTION_VERB_MISSING", "no khởi tố/truy tố/bắt in evidence (investigation only = ALLEGED)")
        else:
            stage = "INDICTMENT" if re.search("truy tố", etxt, re.IGNORECASE) else "INITIATED_OR_ARRESTED"
            R["notes"].append(f"prosecution_stage={stage}; charged/prosecuted, not convicted")
            if re.search("truy tố", etxt, re.IGNORECASE) and not re.search(r"viện|ksnd|kiểm sát", ctx.info.get(oid, {}).get("name", "") + " " + o_m["text"], re.IGNORECASE):
                quar("INDICTMENT_AUTHORITY_MISMATCH", "'truy tố' with a non-prosecutor authority")
            if _CONVICT.search(etxt):
                R["notes"].append("conviction wording present; edge kept as prosecuted only")
            am = _ALLEGED.search(etxt[max(0, lo - 40):hi + 5])  # allegation must sit in the clause of the two endpoints
            if am and not _PROS_VERB.search(etxt[max(0, lo - 40):hi + 5]):
                quar("ALLEGATION_ONLY", "alleged wording around the endpoints without an explicit prosecution verb")
    if pred == "SANCTIONED_BY" and not _SANC_VERB.search(etxt):
        quar("SANCTION_VERB_MISSING", "no sanction verb in evidence")
    # 10. identity / alias checks
    for role, m, eid in (("subject", s_m, sid), ("object", o_m, oid)):
        st = ctx.info.get(eid, {}).get("status", "")
        if st not in ("VERIFIED", "ARTICLE_GROUNDED"):
            quar("IDENTITY_NOT_GROUNDED", f"{role} identity status '{st}'")
        t = m["text"]
        if t.isupper() and 2 <= len(t) <= 6 and " " not in t:
            keys = ctx.aliases(eid)
            if t.upper() not in {k.upper() for k in keys} and normalize_name(t) not in keys:
                quar("ACRONYM_NOT_IN_REGISTRY", f"{role} mention '{t}' has no alias/ticker record for its entity")
            else:
                R["passed"].append(f"{role}_acronym_alias_recorded")
    # 11. LLM cross-check (can only downgrade)
    if R["status"] == "OK":
        if llm is None:
            if llm_required:
                quar("LLM_UNAVAILABLE_FAILSAFE", "LLM cross-check required but unavailable; not auto-passing")
        else:
            out = llm.check(etxt, s_m["text"], o_m["text"], pred, new_status)
            R["llm"] = out
            if out is None:
                quar("LLM_FAILURE_FAILSAFE", "LLM returned no valid JSON; not auto-passing")
            elif out["belongs_to_other_person"] or not out["subject_holds_relation"]:
                quar("LLM_CONTRADICTION", f"LLM: holds={out['subject_holds_relation']} other_person={out['belongs_to_other_person']} - {out['note']}")
            elif not out["evidence_sufficient"]:
                quar("LLM_EVIDENCE_INSUFFICIENT", out["note"])
            elif out["relation_tense"] in ("PAST", "ENDED", "PLANNED", "NEGATED") and new_status == "FACT" and pred in ROLE_PREDS:
                quar("LLM_TEMPORAL_CONFLICT", f"LLM tense {out['relation_tense']} vs deterministic FACT (no lexical proof, not auto-corrected)")
            else:
                R["passed"].append("llm_crosscheck_consistent")
    return R


def _audit_bond(edge, ev, sm, ctx, R, quar, reject, llm, llm_required):
    etxt = ev["evidence_text"]
    name = ctx.info.get(edge["object_id"], {}).get("name", "")
    ns = _nospace(etxt)
    if not re.search(r"phát hành|chào bán", etxt, re.IGNORECASE) or "trái phiếu" not in etxt.lower():
        quar("BOND_CUE_MISSING", "no phát hành/trái phiếu wording")
        return R
    s = sm[0]
    if etxt.lower().find("phát hành") < s["end"] - ev["evidence_start"] and not re.search(r"do\s+.*phát hành", etxt, re.IGNORECASE):
        quar("BOND_ISSUER_ORDER", "issuer does not precede 'phát hành'")
    for tok in _AMOUNT.findall(_nospace(name)) + [c.lower() for c in _CODE.findall(name)]:
        if _nospace(tok) not in ns:
            quar("BOND_FACT_NOT_IN_EVIDENCE", f"'{tok}' of the BondIssue is not printed in the evidence")
    if R["status"] == "OK":
        R["passed"].append("bond_facts_in_evidence")
        mod, _cues = detect_modality(etxt)
        if mod != FactualStatus.FACT or ev["factual_status"] != "FACT":
            R["corrections"]["factual_status"] = mod.value if mod != FactualStatus.FACT else ev["factual_status"]
        if llm is None and llm_required:
            quar("LLM_UNAVAILABLE_FAILSAFE", "LLM cross-check required but unavailable")
        elif llm is not None:
            out = llm.check(etxt, s["text"], name, "ISSUED_BOND", ev["factual_status"])
            R["llm"] = out
            if out is None:
                quar("LLM_FAILURE_FAILSAFE", "LLM returned no valid JSON")
            elif not out["subject_holds_relation"] or not out["evidence_sufficient"]:
                quar("LLM_CONTRADICTION", out["note"])
            else:
                R["passed"].append("llm_crosscheck_consistent")
    return R


# ---------------------------------------------------------------------------------------------- per-edge decision + correction + revalidation
def _dedupe_evidence(evs: list[dict]) -> tuple[list[dict], int]:
    seen, out = set(), []
    for e in evs:
        k = (e["article_id"], e["evidence_start"], e["evidence_end"])
        k2 = (e["article_id"], _nospace(e["evidence_text"]))
        if k in seen or k2 in seen:
            continue
        seen.add(k), seen.add(k2)
        out.append(e)
    return out, len(evs) - len(out)


def revalidate(edge: dict, ctx: Context) -> list[str]:
    """Cheap re-check of the corrected edge: types, evidence access, status policy, identity. Returns failures."""
    f = []
    spec = ctx.relations.get(edge["predicate"])
    if spec is None:
        return ["UNKNOWN_PREDICATE"]
    for side, eid in (("subject", edge["subject_id"]), ("object", edge["object_id"])):
        if ctx.info.get(eid, {}).get("status", "") not in ("VERIFIED", "ARTICLE_GROUNDED"):
            f.append(f"{side.upper()}_IDENTITY_NOT_GROUNDED")
    for ev in edge["evidence"]:
        t = ctx.article_text(ev["article_id"])
        if not t or t[ev["evidence_start"]:ev["evidence_end"]] != ev["evidence_text"]:
            f.append("EVIDENCE_MISMATCH")
        if ctx.status_policy.get(ev["factual_status"]) != "official":
            f.append(f"STATUS_{ev['factual_status']}_NOT_OFFICIAL")
        if edge["predicate"] != "ISSUED_BOND":
            sm, om = _find(ctx.mentions(ev["article_id"]), ev, edge["subject_id"], ctx), _find(ctx.mentions(ev["article_id"]), ev, edge["object_id"], ctx)
            if not sm or not om or not any(_types_ok(spec, a["label"], b["label"]) for a in sm for b in om):
                f.append("TYPES_OR_MENTIONS_INVALID")
    return sorted(set(f))


def audit_edge(edge: dict, ctx: Context, llm: AuditLLM | None, llm_required: bool = True) -> dict:
    t0 = time.perf_counter()
    evs, removed = _dedupe_evidence(edge["evidence"])
    per = [audit_evidence(edge, ev, ctx, llm, llm_required) for ev in evs]
    res = {"edge_id": edge.get("edge_id", ""), "original_edge": edge, "audited_at": now(), "auditor_version": AUDITOR_VERSION,
           "model": llm.model if llm else None, "prompt_version": LLM_PROMPT_VERSION if llm else None,
           "normalizations": ([f"dedupe_evidence(removed={removed})"] if removed else []),
           "evidence_audits": [{k: v for k, v in r.items()} for r in per], "proposed_correction": None, "corrected_edge": None,
           "failed_checks": sorted({f for r in per for f in r["failed"]}), "passed_checks": sorted({p for r in per for p in r["passed"]}),
           "reasons": [x for r in per for x in r["reasons"]]}
    nonweak = [r for r in per if r["status"] != "WEAK"]
    if not nonweak:
        res["decision"], res["reasons"] = "QUARANTINE", res["reasons"] + ["NO_FULL_SENTENCE_EVIDENCE: only captions/fragments"]
    elif all(r["status"] == "REJECT" for r in nonweak):
        res["decision"] = "REJECT"
    elif any(r["status"] in ("QUAR", "REJECT") for r in nonweak):
        res["decision"] = "QUARANTINE"
    else:
        corr: dict = {}
        conflict = False
        for r in nonweak:
            for k, v in r["corrections"].items():
                if corr.setdefault(k, v) != v:
                    conflict = True
        if conflict:
            res["decision"], res["reasons"] = "QUARANTINE", res["reasons"] + ["CORRECTION_CONFLICT across evidence records"]
        elif corr:
            fixed = json.loads(json.dumps({**edge, "evidence": [e for e, r in zip(evs, per, strict=True) if r["status"] != "WEAK"]}))
            if corr.get("direction") == "SWAP":
                fixed["subject_id"], fixed["object_id"] = fixed["object_id"], fixed["subject_id"]
            if "predicate" in corr:
                fixed["predicate"] = corr["predicate"]
            if "factual_status" in corr:
                for e in fixed["evidence"]:
                    e["factual_status"] = corr["factual_status"]
            for e in fixed["evidence"]:
                e["validation_status"] = "QA:AUTO_CORRECT:" + ",".join(sorted(corr))
            res["proposed_correction"], res["corrected_edge"] = corr, fixed
            bad = revalidate(fixed, ctx)
            if bad:
                res["decision"], res["reasons"] = "QUARANTINE", res["reasons"] + [f"REVALIDATION_FAILED after correction {corr}: {bad}"]
            else:
                res["decision"] = "AUTO_CORRECT"
                res["reasons"].append(f"corrected {corr}; revalidation passed")
        else:
            fixed = json.loads(json.dumps({**edge, "evidence": [e for e, r in zip(evs, per, strict=True) if r["status"] != "WEAK"]}))
            for e in fixed["evidence"]:
                e["validation_status"] = "QA:PASS"
            bad = revalidate(fixed, ctx)
            res["decision"], res["corrected_edge"] = ("PASS", fixed) if not bad else ("QUARANTINE", None)
            if bad:
                res["reasons"].append(f"REVALIDATION_FAILED: {bad}")
    res["seconds"] = round(time.perf_counter() - t0, 3)
    return res


# ---------------------------------------------------------------------------------------------- duplicate BondIssue resolution
def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _bond_amounts(evs: list[dict]) -> dict:
    """Amounts printed in the evidence. If different evidence records disagree on a figure the figure is None (no proof)."""
    f = {"triệu": 1.0, "tỷ": 1000.0}

    def pick(rx, conv):
        vals = {conv(m) for e in evs for m in rx.finditer(e["evidence_text"])}
        return vals.pop() if len(vals) == 1 else None
    return {"count": pick(re.compile(r"(\d[\d.]*)\s+trái phiếu"), lambda m: _num(m.group(1))),
            "unit": pick(re.compile(r"mệnh giá\s+(\d[\d.,]*)\s*(triệu|tỷ)\s*đồng"), lambda m: _num(m.group(1)) * f[m.group(2)]),
            "total": pick(re.compile(r"tổng giá trị phát hành\s+(\d[\d.,]*)\s*(triệu|tỷ)\s*đồng"), lambda m: _num(m.group(1)) * f[m.group(2)])}


def resolve_bond_duplicates(results: list[dict], ctx: Context) -> list[dict]:
    """Same issuer + same printed code. Merge only with arithmetic proof (count x par value == total). Otherwise both -> QUARANTINE."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in results:
        e = r["original_edge"]
        if e["predicate"] == "ISSUED_BOND":
            code = _CODE.findall(ctx.info.get(e["object_id"], {}).get("name", ""))
            if code:
                groups[(ctx.canon(e["subject_id"]), code[0])].append(r)
    for (issuer, code), rs in groups.items():
        if len(rs) < 2:
            continue
        ok = [r for r in rs if r["decision"] in ("PASS", "AUTO_CORRECT")]
        union_ev = [e for r in rs for e in r["original_edge"]["evidence"]]
        am = _bond_amounts(union_ev)
        proven = (am["count"] and am["unit"] and am["total"] and abs(am["count"] * am["unit"] - am["total"]) < 1e-6)
        names = [ctx.info.get(r["original_edge"]["object_id"], {}).get("name", "") for r in rs]
        if proven and len(ok) == len(rs):
            keep = next((r for r, n in zip(rs, names, strict=True) if "tỷ" in n), rs[0])
            kid = keep["original_edge"]["object_id"]
            merged_ev, _ = _dedupe_evidence([e for r in rs for e in (r["corrected_edge"] or r["original_edge"])["evidence"]])
            merged = {**keep["original_edge"], "object_id": kid, "evidence": merged_ev}
            for e in merged["evidence"]:
                e["validation_status"] = "QA:AUTO_CORRECT:merge_duplicate_bond"
            proof = (f"issuer={issuer}; code={code}; {am['count']:.0f} bonds x par {am['unit']:.0f} million VND = {am['total']:.0f} million VND (= stated total)")
            for r in rs:
                r["decision"] = "AUTO_CORRECT"
                r["proposed_correction"] = {"merge_duplicate_bond": {"into_object_id": kid, "proof": proof,
                                                                       "merged_object_ids": [x["original_edge"]["object_id"] for x in rs]}}
                r["corrected_edge"] = merged
                r["reasons"].append("duplicate BondIssue merged: " + proof)
        else:
            why = "arithmetic proof of one issuance missing" if not proven else "member edge not clean"
            for r in rs:
                if r["decision"] in ("PASS", "AUTO_CORRECT"):
                    r["decision"], r["corrected_edge"] = "QUARANTINE", None
                r["reasons"].append(f"BOND_CONFLICT: same issuer+code {code} on {len(rs)} BondIssue nodes, {why}")
    return results


# ---------------------------------------------------------------------------------------------- runner (checkpoint / resume / outputs)
def fingerprint(edge: dict, llm_on: bool) -> str:
    return hashlib.sha1((json.dumps(edge, sort_keys=True, ensure_ascii=False) + AUDITOR_VERSION + LLM_PROMPT_VERSION + str(llm_on)).encode()).hexdigest()


def run(edges: list[dict], ctx: Context, out: Path, llm: AuditLLM | None, llm_required: bool = True, fresh: bool = False,
        log=print) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    ck = out / "checkpoint.jsonl"
    if fresh and ck.exists():
        ck.rename(out / f"checkpoint.{int(time.time())}.bak.jsonl")  # never destroy previous audit history
    done: dict[str, dict] = {}
    if ck.exists():
        for line in ck.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                done[d["fingerprint"]] = d["result"]
    t0 = time.perf_counter()
    results, skipped = [], 0
    with ck.open("a", encoding="utf-8") as f:
        for i, e in enumerate(edges, 1):
            fp = fingerprint(e, llm is not None)
            if fp in done:
                results.append(done[fp])
                skipped += 1
                continue
            r = audit_edge(e, ctx, llm, llm_required)
            f.write(json.dumps({"fingerprint": fp, "result": r}, ensure_ascii=False) + "\n")
            f.flush()
            results.append(r)
            log(f"[{i}/{len(edges)}] {r['decision']:<10} {e['predicate']} {e['subject_id'][:30]} -> {e['object_id'][:30]}")
    results = resolve_bond_duplicates(json.loads(json.dumps(results)), ctx)
    return write_outputs(results, edges, ctx, out, llm, time.perf_counter() - t0, skipped)


def _entities(edges: list[dict]) -> set[str]:
    return {e["subject_id"] for e in edges} | {e["object_id"] for e in edges}


def write_outputs(results: list[dict], edges: list[dict], ctx: Context, out: Path, llm: AuditLLM | None, secs: float, skipped: int) -> dict:
    import csv
    dec = Counter(r["decision"] for r in results)
    (out / "audit_results.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results), encoding="utf-8")
    validated: dict[tuple, dict] = {}
    for r in results:
        if r["decision"] in ("PASS", "AUTO_CORRECT") and r["corrected_edge"]:
            e = r["corrected_edge"]
            k = (e["subject_id"], e["predicate"], e["object_id"])
            if k in validated:
                have = {(x["article_id"], x["evidence_start"], x["evidence_end"]) for x in validated[k]["evidence"]}
                validated[k]["evidence"] += [x for x in e["evidence"] if (x["article_id"], x["evidence_start"], x["evidence_end"]) not in have]
            else:
                validated[k] = json.loads(json.dumps(e))
    for name, sel in (("validated_edges", list(validated.values())),
                      ("quarantine", [r["original_edge"] | {"qa_reasons": r["reasons"]} for r in results if r["decision"] == "QUARANTINE"]),
                      ("rejected", [r["original_edge"] | {"qa_reasons": r["reasons"]} for r in results if r["decision"] == "REJECT"])):
        (out / f"{name}.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in sel), encoding="utf-8")
    with (out / "audit_results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["edge_id", "decision", "subject", "predicate", "object", "original_status", "final_status", "correction", "failed_checks", "reasons", "llm_called", "source_urls", "evidence"])
        for r in results:
            e = r["original_edge"]
            ce = r["corrected_edge"] or e
            w.writerow([r["edge_id"], r["decision"], ctx.info.get(e["subject_id"], {}).get("name", e["subject_id"]), e["predicate"],
                        ctx.info.get(e["object_id"], {}).get("name", e["object_id"]), e["evidence"][0]["factual_status"],
                        ce["evidence"][0]["factual_status"] if ce["evidence"] else "", json.dumps(r["proposed_correction"], ensure_ascii=False) if r["proposed_correction"] else "",
                        "|".join(r["failed_checks"]), " || ".join(r["reasons"])[:600], any(a["llm"] for a in r["evidence_audits"]),
                        " | ".join(sorted({x["source_url"] for x in e["evidence"]})), " || ".join(x["evidence_text"] for x in e["evidence"])[:500]])
    v = list(validated.values())
    summary = {
        "decisions": dict(dec), "input_edges": len(edges), "input_unique_entities": len(_entities(edges)),
        "input_relation_types": len({e["predicate"] for e in edges}),
        "validated_edges": len(v), "validated_unique_entities": len(_entities(v)), "validated_relation_types": sorted({e["predicate"] for e in v}),
        "duplicate_bond_events_resolved": len({json.dumps(r["proposed_correction"]["merge_duplicate_bond"]["merged_object_ids"]) for r in results
                                                if r["proposed_correction"] and "merge_duplicate_bond" in r["proposed_correction"]}),
        "corrections_by_type": dict(Counter(k for r in results if r["proposed_correction"] for k in r["proposed_correction"])),
        "failed_checks": dict(Counter(c for r in results for c in r["failed_checks"])),
        "llm": {"model": llm.model, "prompt_version": LLM_PROMPT_VERSION, "live_calls": llm.calls, "cache_hits": llm.hits, "failures": llm.failures,
                "llm_seconds": round(llm.latency, 1)} if llm else None,
        "resumed_from_checkpoint": skipped, "wall_seconds": round(secs, 1), "auditor_version": AUDITOR_VERSION, "finished_at": now(),
        "note": "No gold labels: these are rule-based QA outcomes, not Precision/Recall."}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="auto_auditor")
    p5 = ROOT / "data/outputs/phase5"
    ap.add_argument("--runs", nargs="+", default=[str(p5 / "dev44"), str(p5 / "holdout19"), str(p5 / "new144")])
    ap.add_argument("--registry", nargs="+", default=[str(ROOT / f"data/registry/registry_p5_{n}.sqlite") for n in ("dev", "holdout", "new")])
    ap.add_argument("--staging", default=str(ROOT / "data/staging/staging.sqlite"))
    ap.add_argument("--out", default=str(ROOT / "reports/phase6/auto_qa"))
    ap.add_argument("--no-llm", action="store_true", help="skip Qwen; PASS is then impossible (fail-safe) unless --llm-optional")
    ap.add_argument("--llm-optional", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="ignore checkpoint (old one is kept as .bak)")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(argv)
    from vckg.graph.neo4j_sync import collect, edge_id
    runs, regs = [Path(x) for x in a.runs], [Path(x) for x in a.registry]
    off, _cand, _info, _arts = collect(runs, regs)
    for e in off:
        e["edge_id"] = edge_id(e)
    if a.limit:
        off = off[: a.limit]
    ctx = build_context(runs, regs, Path(a.staging), getattr(collect, "last_merges", []))
    llm = None
    if not a.no_llm:
        llm = AuditLLM()
        if not llm.available():
            print("UNAVAILABLE: Ollama/qwen3.5:9b not reachable -> fail-safe, nothing can PASS")
            llm = None
    summary = run(off, ctx, Path(a.out), llm, llm_required=not a.llm_optional, fresh=a.fresh)
    try:  # read-only comparison with the production graph
        from vckg.graph.neo4j_sync import connect
        with connect().session() as s:
            ids = {r["i"] for r in s.run("MATCH (:Entity)-[r]->(:Entity) WHERE r.edge_id IS NOT NULL RETURN r.edge_id AS i")}
        summary["neo4j_readonly_check"] = {"neo4j_official_edges": len(ids), "audited_edges": len(off), "same_edge_ids": ids == {e["edge_id"] for e in off}}
        (Path(a.out) / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        summary["neo4j_readonly_check"] = f"unavailable: {e}"
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
