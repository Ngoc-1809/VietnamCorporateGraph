"""Evidence validation + edge assembly with edge deduplication and explicit status policy.

Outcomes per candidate: official | candidate_edge (kept for review, never official) | rejected (no edge).
 - evidence must be a verbatim slice of the article at the stated offsets, article needs url+id;
 - NEGATED (DENIED) never creates an edge; PLANNED/ALLEGED/UNKNOWN -> candidate edge only;
 - the LLM can only make a verdict STRICTER: deterministic findings (negation, structure-derived direction,
   endpoint identity, evidence) are never overridden by 'valid=true';
 - an official edge needs: verifier valid + no blocking reason + official-by-policy status + endpoints meeting the
   endpoint policy (organizations VERIFIED; persons may be article identity clusters);
 - the same (subject, predicate, object) is one Edge with several EvidenceRecords (deduped per article+span).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from vckg.models import (
    Article,
    Edge,
    EvidenceRecord,
    FactualStatus,
    RelationCandidate,
    ReviewStatus,
    Verdict,
)
from vckg.reasons import (
    DEFAULT_ENDPOINT_POLICY,
    ReasonCode,
    diagnose_candidate,
    is_blocking,
    pre_llm_reasons,
    quote_supported,
)

DEFAULT_STATUS_POLICY = {"FACT": "official", "HISTORICAL": "official", "ENDED": "official", "PLANNED": "candidate",
                         "ALLEGED": "candidate", "UNKNOWN": "candidate", "DENIED": "never_edge"}
_RANK = [FactualStatus.DENIED, FactualStatus.ALLEGED, FactualStatus.PLANNED, FactualStatus.ENDED,
         FactualStatus.HISTORICAL, FactualStatus.UNKNOWN, FactualStatus.FACT]


class EvidenceError(ValueError):
    pass


def validate_evidence(article: Article, c: RelationCandidate, verdict: Verdict | None = None) -> None:
    """Raises EvidenceError (kept for direct use/tests; the store uses the non-raising reason codes)."""
    if not article.url or not article.article_id:
        raise EvidenceError("missing provenance (url/article_id)")
    if ReasonCode.MISSING_EVIDENCE in pre_llm_reasons(article.text, c, None):
        raise EvidenceError("evidence/mention offsets do not match article text")
    if verdict and verdict.evidence_text and not quote_supported(verdict.evidence_text, c.evidence_text):
        raise EvidenceError("LLM evidence_text is not verbatim in the sentence")


def stricter(a: FactualStatus, b: FactualStatus) -> FactualStatus:
    """Lower rank wins (DENIED strictest, FACT loosest). An LLM can only tighten a rule-derived status."""
    return min(a, b, key=_RANK.index)


@dataclass
class Outcome:
    candidate_id: str
    outcome: str  # official | candidate_edge | rejected
    reasons: list[ReasonCode] = field(default_factory=list)
    edge_key: tuple[str, str, str] | None = None


class EdgeStore:
    def __init__(self, status_policy: dict | None = None, endpoint_policy: dict | None = None) -> None:
        self.edges: dict[tuple[str, str, str], Edge] = {}
        self.outcomes: dict[str, Outcome] = {}
        self.status_policy = status_policy or DEFAULT_STATUS_POLICY
        self.endpoint_policy = endpoint_policy or DEFAULT_ENDPOINT_POLICY

    @property
    def dropped(self) -> list[tuple[str, str]]:
        """(candidate_id, primary reason code) for rejected candidates - compatibility view."""
        return [(o.candidate_id, o.reasons[0].value if o.reasons else "OTHER")
                for o in self.outcomes.values() if o.outcome == "rejected"]

    def reject(self, c: RelationCandidate, reasons: list[ReasonCode]) -> None:
        self.outcomes[c.candidate_id] = Outcome(c.candidate_id, "rejected", reasons or [ReasonCode.OTHER])

    def add(self, article: Article, c: RelationCandidate, verdict: Verdict | None, method: str,
            symmetric: bool = False, relations_spec: dict | None = None, *, verifier_ran: bool | None = None,
            model: str = "", prompt_version: str = "") -> Edge | None:
        if not article.url or not article.article_id:
            self.reject(c, [ReasonCode.MISSING_EVIDENCE])
            return None
        ran = (verdict is not None) if verifier_ran is None else verifier_ran
        reasons = diagnose_candidate(article.text, c, verdict, relations_spec, verifier_ran=ran, policy=self.endpoint_policy)
        if symmetric:  # direction is meaningless for symmetric predicates
            reasons = [r for r in reasons if r != ReasonCode.INVALID_DIRECTION]
        if is_blocking(reasons):
            self.reject(c, reasons)
            return None
        # ---- direction + status resolution (deterministic findings first)
        subj, obj = c.subject.entity_id, c.object.entity_id
        status, valid_from, valid_to = c.factual_status, None, None
        note = ""
        if verdict is not None:
            if verdict.subject_mention != c.subject.text and not symmetric:
                subj, obj = obj, subj  # allowed only for typed/unknown direction (diagnose blocked 'pattern' flips)
            valid_from, valid_to = verdict.valid_from, verdict.valid_to
            if verdict.valid and verdict.rejection_reason != "NONE":
                note = "llm_inconsistent_rejection_reason=" + verdict.rejection_reason  # valid=true yet a rejection reason was given
            llm_status = verdict.factual_status
            if llm_status in (FactualStatus.HISTORICAL, FactualStatus.ENDED) and c.factual_status not in (
                    FactualStatus.HISTORICAL, FactualStatus.ENDED):
                # Qwen over-uses HISTORICAL for present-tense statements in past-event articles; a past/ended
                # reading needs a lexical cue found by the rule layer, otherwise the LLM status is ignored.
                note = (note + ";" if note else "") + f"llm_status={llm_status.value}_ignored_no_cue"
                llm_status = c.factual_status
            status = stricter(c.factual_status, llm_status)
            if c.factual_status == FactualStatus.FACT and llm_status == FactualStatus.UNKNOWN:
                status = FactualStatus.UNKNOWN
        policy = self.status_policy.get(status.value, "candidate")
        if policy == "never_edge":
            self.reject(c, [*reasons, ReasonCode.NEGATED_RELATION])
            return None
        if symmetric and subj > obj:
            subj, obj = obj, subj
        if subj == obj:
            self.reject(c, [ReasonCode.OTHER])
            return None
        official = (policy == "official" and verdict is not None and verdict.valid and not reasons)
        review = ReviewStatus.AUTO_ACCEPTED if official else ReviewStatus.NEEDS_REVIEW
        rec = EvidenceRecord(
            article_id=article.article_id, source_url=article.url, evidence_text=c.evidence_text,
            evidence_start=c.evidence_start, evidence_end=c.evidence_end, published_at=article.published_at,
            extraction_method=method, relation_score=None, score_available=False,
            subject_ner_score=c.subject.ner_score, object_ner_score=c.object.ner_score,
            subject_linking_score=c.subject.link_score, object_linking_score=c.object.link_score,
            validation_status=(("ACCEPTED" if official else "CANDIDATE:" + ",".join(r.value for r in reasons or [ReasonCode.OTHER]))
                               + (f";{note}" if note else "")),
            review_status=review, factual_status=status, valid_from=valid_from, valid_to=valid_to,
            model=model, prompt_version=prompt_version)
        key = (subj, c.predicate, obj)
        edge = self.edges.setdefault(key, Edge(subject_id=subj, predicate=c.predicate, object_id=obj))
        if any((e.article_id, e.evidence_start, e.evidence_end) == (rec.article_id, rec.evidence_start, rec.evidence_end)
               for e in edge.evidence):
            self.outcomes[c.candidate_id] = Outcome(c.candidate_id, "rejected", [ReasonCode.DUPLICATE], key)
            return edge
        edge.evidence.append(rec)
        self.outcomes[c.candidate_id] = Outcome(c.candidate_id, "official" if official else "candidate_edge", reasons, key)
        return edge

    def remap(self, canonical) -> None:
        """Re-key edges after registry merges (canonical: entity_id -> surviving id). Evidence is unioned, not lost."""
        new: dict[tuple[str, str, str], Edge] = {}
        for (s, p, o), e in self.edges.items():
            k = (canonical(s), p, canonical(o))
            tgt = new.setdefault(k, Edge(subject_id=k[0], predicate=p, object_id=k[2]))
            have = {(x.article_id, x.evidence_start, x.evidence_end) for x in tgt.evidence}
            tgt.evidence += [x for x in e.evidence if (x.article_id, x.evidence_start, x.evidence_end) not in have]
        self.edges = new

    def official_edges(self) -> list[Edge]:
        out = []
        for e in self.edges.values():
            ev = [r for r in e.evidence if self.status_policy.get(r.factual_status.value) == "official"
                  and r.review_status in (ReviewStatus.AUTO_ACCEPTED, ReviewStatus.HUMAN_VERIFIED)]
            if ev:
                out.append(e.model_copy(update={"evidence": ev}))
        return out

    def candidate_edges(self) -> list[Edge]:
        off = {e.key for e in self.official_edges()}
        return [e for e in self.edges.values() if e.key not in off]




