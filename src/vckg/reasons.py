"""Unified rejection / review reason codes + independent per-candidate diagnosis.

`diagnose_candidate` evaluates every check independently (never stops at the first failure), so a candidate
rejected for several reasons keeps all of them. Used by the live pipeline/validator and by offline diagnostics.

BLOCKING reasons => no edge. REVIEW reasons => candidate edge kept in staging (never official)."""
from __future__ import annotations

from enum import Enum

from vckg.models import EntityType, FactualStatus, RelationCandidate, Verdict


class ReasonCode(str, Enum):
    SUBJECT_UNRESOLVED = "SUBJECT_UNRESOLVED"
    OBJECT_UNRESOLVED = "OBJECT_UNRESOLVED"
    NO_EXPLICIT_RELATION = "NO_EXPLICIT_RELATION"
    NEGATED_RELATION = "NEGATED_RELATION"
    NON_FACTUAL_RELATION = "NON_FACTUAL_RELATION"
    INVALID_DIRECTION = "INVALID_DIRECTION"
    INVALID_ENTITY_TYPES = "INVALID_ENTITY_TYPES"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    LLM_REJECTED = "LLM_REJECTED"
    PARSE_FAILURE = "PARSE_FAILURE"
    DUPLICATE = "DUPLICATE"
    OTHER = "OTHER"
    # extras (documented in reports/phase4_diagnostics.md)
    VERIFIER_ENTITY_MISMATCH = "VERIFIER_ENTITY_MISMATCH"  # LLM named an entity that is not one of the candidate's
    NOT_VERIFIED = "NOT_VERIFIED"  # verifier not run (unavailable)
    ENDPOINT_NOT_VERIFIED = "ENDPOINT_NOT_VERIFIED"  # endpoint exists but identity status below policy for official
    SPAN_ERROR = "SPAN_ERROR"  # LLM reports the mention is only part of a different, longer name


REVIEW_ONLY = {ReasonCode.NON_FACTUAL_RELATION, ReasonCode.NOT_VERIFIED, ReasonCode.ENDPOINT_NOT_VERIFIED}
IDENTITY_REASONS = {ReasonCode.SUBJECT_UNRESOLVED, ReasonCode.OBJECT_UNRESOLVED}
LLM_REASON_MAP = {"NO_RELATION": ReasonCode.NO_EXPLICIT_RELATION, "WRONG_DIRECTION": ReasonCode.INVALID_DIRECTION,
                  "NEGATED": ReasonCode.NEGATED_RELATION, "NOT_FACTUAL": ReasonCode.NON_FACTUAL_RELATION,
                  "WRONG_ENTITY": ReasonCode.VERIFIER_ENTITY_MISMATCH, "SPAN_ERROR": ReasonCode.SPAN_ERROR,
                  "OTHER": ReasonCode.LLM_REJECTED}
NON_FACT_STATUSES = {FactualStatus.PLANNED, FactualStatus.ALLEGED}

DEFAULT_ENDPOINT_POLICY = {"ORG": ["VERIFIED"], "PERSON": ["VERIFIED", "PROVISIONAL"], "AUTHORITY": ["VERIFIED", "PROVISIONAL"]}


def endpoint_group(t: EntityType) -> str:
    if t == EntityType.PERSON:
        return "PERSON"
    if t in (EntityType.REGULATOR, EntityType.GOVERNMENT_AGENCY):
        return "AUTHORITY"
    return "ORG"


def quote_supported(quote: str, sentence: str) -> bool:
    """True if the LLM quote is an exact substring of the sentence or an ordered word-subsequence of it
    (it may drop asides such as "(HOSE: PPC)" but cannot contain words the sentence does not have)."""
    if not quote or quote in sentence:
        return True
    strip = lambda w: w.strip(".,;:()[]\"“”\x27")
    it = iter([strip(w) for w in sentence.split()])
    return all(any(strip(w) == s for s in it) for w in quote.split())


def is_blocking(reasons: list[ReasonCode]) -> bool:
    return any(r not in REVIEW_ONLY for r in reasons)


def pre_llm_reasons(article_text: str, c: RelationCandidate, spec: dict | None) -> list[ReasonCode]:
    """Checks that make an LLM call pointless. Everything here is blocking anyway, so no recall is lost."""
    r: list[ReasonCode] = []
    if not c.subject.entity_id:
        r.append(ReasonCode.SUBJECT_UNRESOLVED)
    if not c.object.entity_id:
        r.append(ReasonCode.OBJECT_UNRESOLVED)
    if spec and (c.subject.label.value not in spec["subject"] or c.object.label.value not in spec["object"]):
        r.append(ReasonCode.INVALID_ENTITY_TYPES)
    if (article_text[c.evidence_start:c.evidence_end] != c.evidence_text
            or article_text[c.subject.start:c.subject.end] != c.subject.text
            or article_text[c.object.start:c.object.end] != c.object.text):
        r.append(ReasonCode.MISSING_EVIDENCE)
    if c.factual_status == FactualStatus.DENIED:
        r.append(ReasonCode.NEGATED_RELATION)  # rule-certain negation: edge can never be created
    return r


def diagnose_candidate(article_text: str, c: RelationCandidate, verdict: Verdict | None, spec: dict | None, *,
                       verifier_ran: bool = True, policy: dict | None = None) -> list[ReasonCode]:
    r = pre_llm_reasons(article_text, c, spec)
    if c.factual_status in NON_FACT_STATUSES:
        r.append(ReasonCode.NON_FACTUAL_RELATION)
    policy = policy or DEFAULT_ENDPOINT_POLICY
    for m, st in ((c.subject, c.subject_entity_status), (c.object, c.object_entity_status)):
        if m.entity_id and st and st not in policy.get(endpoint_group(m.label), ["VERIFIED"]):
            r.append(ReasonCode.ENDPOINT_NOT_VERIFIED)
            break
    if not verifier_ran:
        r.append(ReasonCode.NOT_VERIFIED)
    elif verdict is None:
        r.append(ReasonCode.PARSE_FAILURE)
    else:
        texts = {c.subject.text, c.object.text}
        if verdict.subject_mention not in texts or verdict.object_mention not in texts or verdict.subject_mention == verdict.object_mention:
            r.append(ReasonCode.VERIFIER_ENTITY_MISMATCH)
        else:
            flipped = verdict.subject_mention != c.subject.text
            if (flipped != (verdict.direction == "REVERSED")):
                r.append(ReasonCode.OTHER)  # direction field contradicts the named subject
            if flipped and c.direction_source == "pattern":
                r.append(ReasonCode.INVALID_DIRECTION)  # structure-derived direction beats the LLM
            elif flipped and spec:
                sm, om = c.object, c.subject
                if sm.label.value not in spec["subject"] or om.label.value not in spec["object"]:
                    r.append(ReasonCode.INVALID_DIRECTION)
        if verdict.relation_type not in (c.predicate, "NO_RELATION"):
            r.append(ReasonCode.OTHER)
        if not verdict.valid or verdict.relation_type == "NO_RELATION":
            r.append(LLM_REASON_MAP.get(verdict.rejection_reason, ReasonCode.LLM_REJECTED))
            if verdict.rejection_reason != "NONE":
                r.append(ReasonCode.LLM_REJECTED)
        if verdict.evidence_text and not quote_supported(verdict.evidence_text, c.evidence_text):
            r.append(ReasonCode.MISSING_EVIDENCE)
        if verdict.valid:
            if verdict.factual_status == FactualStatus.DENIED:
                r.append(ReasonCode.NEGATED_RELATION)
            elif verdict.factual_status in NON_FACT_STATUSES:
                r.append(ReasonCode.NON_FACTUAL_RELATION)
    seen: set[ReasonCode] = set()
    return [x for x in r if not (x in seen or seen.add(x))]


