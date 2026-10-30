"""Core Pydantic schemas shared by every pipeline stage.

Score policy (Phase 4): a score field is None when the backend did not produce a real score.
ner_score comes from GLiNER; linking_score only from fuzzy matching (rapidfuzz ratio); relation_score is
None unless a calibrated/real score exists. LLM self-reported confidence is NOT stored as a score."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    BANK = "BANK"
    REGULATOR = "REGULATOR"
    GOVERNMENT_AGENCY = "GOVERNMENT_AGENCY"


ORG_LIKE = {EntityType.ORGANIZATION, EntityType.BANK, EntityType.REGULATOR, EntityType.GOVERNMENT_AGENCY}


class FactualStatus(str, Enum):
    """CONFIRMED == FACT and NEGATED == DENIED (aliases kept so stored data stays valid)."""

    FACT = "FACT"
    CONFIRMED = "FACT"  # noqa: PIE796 - intentional alias
    PLANNED = "PLANNED"
    ALLEGED = "ALLEGED"
    DENIED = "DENIED"
    NEGATED = "DENIED"  # noqa: PIE796 - intentional alias
    HISTORICAL = "HISTORICAL"
    ENDED = "ENDED"  # relation held and has explicitly ended (resigned, dismissed, terminated)
    UNKNOWN = "UNKNOWN"


class ReviewStatus(str, Enum):
    AUTO_ACCEPTED = "AUTO_ACCEPTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"


class ResolutionStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"
    AMBIGUOUS = "AMBIGUOUS"
    REJECTED = "REJECTED"


class Sentence(BaseModel):
    index: int
    text: str
    start: int
    end: int


class Article(BaseModel):
    article_id: str
    url: str
    source: str
    title: str = ""
    text: str
    published_at: str | None = None
    fetched_at: str | None = None
    content_hash: str = ""


class Mention(BaseModel):
    """A mention with character offsets into the (NFC-normalized) article text. Separate from entities."""

    text: str
    start: int
    end: int
    label: EntityType
    ner_score: float | None = None  # GLiNER score; None for dictionary/rule mentions (no score exists)
    method: str = "gliner2.5"
    article_id: str = ""
    sentence_index: int | None = None
    entity_id: str | None = None  # None == unresolved
    link_status: str = "unresolved"  # resolved | provisional | ambiguous | unresolved
    linking_method: str = ""
    link_score: float | None = None  # only for fuzzy matches (rapidfuzz ratio); None otherwise
    candidate_entity_ids: list[str] = Field(default_factory=list)
    alias_of: int | None = None  # start offset of the mention this one is a parenthetical alias of

    @model_validator(mode="before")
    @classmethod
    def _legacy(cls, d):
        if isinstance(d, dict) and "confidence" in d:  # Phase-3 JSONL compatibility
            d = dict(d)
            conf = d.pop("confidence")
            if d.get("method", "gliner2.5") == "gliner2.5" and "ner_score" not in d:
                d["ner_score"] = conf
            if d.get("link_score") == 0.0 and not d.get("entity_id"):
                d["link_score"] = None
        return d

    @model_validator(mode="after")
    def _check_span(self) -> Mention:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("invalid span")
        return self

    @property
    def mention_id(self) -> str:
        import hashlib
        return hashlib.sha1(f"{self.article_id}|{self.start}|{self.end}|{self.text}".encode()).hexdigest()[:16]

    def check_against(self, doc_text: str) -> bool:
        return doc_text[self.start : self.end] == self.text


class RegistryEntry(BaseModel):
    entity_id: str
    canonical_name: str
    type: EntityType
    aliases: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    provenance: str = "registry"  # registry data is NEVER a graph edge source


class RelationCandidate(BaseModel):
    candidate_id: str
    article_id: str = ""
    subject: Mention
    object: Mention
    predicate: str
    sentence_index: int
    evidence_text: str
    evidence_start: int
    evidence_end: int
    cue: str = ""
    pattern_id: str = ""
    direction_source: str = "unknown"  # pattern (structure-derived) | types | unknown
    direction_ambiguous: bool = False  # kept for compatibility: True when direction_source == unknown
    factual_status: FactualStatus = FactualStatus.UNKNOWN
    modality_cues: list[str] = Field(default_factory=list)
    subject_entity_status: str | None = None  # ResolutionStatus value from the registry, None if unlinked
    object_entity_status: str | None = None
    method: str = "pattern"


class Verdict(BaseModel):
    """Strict JSON contract for the LLM. No defaults on required fields; no self-reported confidence
    (an LLM's stated confidence is not a probability and is deliberately not part of the contract)."""

    valid: bool
    relation_type: str  # predicate name, or NO_RELATION
    subject_mention: str  # exact text of the SUBJECT mention (one of the two given strings)
    object_mention: str  # exact text of the OBJECT mention
    direction: str  # AS_LISTED | REVERSED (relative to Entity 1 -> Entity 2)
    evidence_text: str  # verbatim substring of the sentence
    factual_status: FactualStatus
    rejection_reason: str  # NONE | NO_RELATION | WRONG_DIRECTION | NEGATED | NOT_FACTUAL | WRONG_ENTITY | SPAN_ERROR | OTHER
    valid_from: str | None = None
    valid_to: str | None = None
    reason: str = Field(default="", max_length=300)

    @model_validator(mode="before")
    @classmethod
    def _legacy(cls, d):
        if isinstance(d, dict) and "subject_text" in d:  # Phase-3 verdict files
            d = dict(d)
            d.setdefault("relation_type", d.pop("predicate", None) or "OTHER")
            d.setdefault("subject_mention", d.pop("subject_text"))
            d.setdefault("object_mention", d.pop("object_text"))
            d.setdefault("evidence_text", d.pop("evidence_quote", ""))
            d.pop("confidence", None)
            d.setdefault("direction", "AS_LISTED")
            d.setdefault("rejection_reason", "NONE" if d.get("valid") else "OTHER")
        return d

    # compatibility accessors
    @property
    def predicate(self) -> str:
        return self.relation_type

    @property
    def subject_text(self) -> str:
        return self.subject_mention

    @property
    def object_text(self) -> str:
        return self.object_mention

    @property
    def evidence_quote(self) -> str:
        return self.evidence_text


class EvidenceRecord(BaseModel):
    article_id: str
    source_url: str
    evidence_text: str
    evidence_start: int
    evidence_end: int
    published_at: str | None = None
    extraction_method: str
    relation_score: float | None = None  # None unless a real/calibrated score exists
    score_available: bool = False
    subject_ner_score: float | None = None
    object_ner_score: float | None = None
    subject_linking_score: float | None = None
    object_linking_score: float | None = None
    validation_status: str = ""
    review_status: ReviewStatus
    factual_status: FactualStatus
    valid_from: str | None = None
    valid_to: str | None = None
    model: str = ""
    prompt_version: str = ""


class Edge(BaseModel):
    """One logical edge; many evidence records may support it."""

    subject_id: str
    predicate: str
    object_id: str
    evidence: list[EvidenceRecord] = Field(default_factory=list)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.subject_id, self.predicate, self.object_id)

