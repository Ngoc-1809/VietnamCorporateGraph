"""Per-article pipeline: normalize -> NER + registry dictionary -> span repair -> entity resolution -> structure-aware
candidates -> pre-LLM filter -> verifier -> validation -> edges. NER and verifier are injected (real or test doubles).
Counters record the funnel at every step."""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol

from vckg.entity_linking.resolver import EntityResolver
from vckg.models import Article, Mention, RelationCandidate, Verdict
from vckg.ner.merge import merge_mentions
from vckg.ner.scope import classify_scope
from vckg.preprocessing.text import normalize_text, split_sentences
from vckg.reasons import ReasonCode, pre_llm_reasons
from vckg.relation_extraction.candidates import count_pairs, generate_candidates
from vckg.validation.evidence import EdgeStore


class NER(Protocol):
    def extract(self, text: str) -> list[Mention]: ...


class Verifier(Protocol):
    model: str
    prompt_version: str

    def verify(self, c: RelationCandidate, definition: str = "") -> Verdict | None: ...


@dataclass
class Counters:
    articles: int = 0
    mentions_total: int = 0
    mentions_person_org_bank: int = 0
    mentions_in_scope: int = 0
    out_of_scope: int = 0
    linked_verified: int = 0
    linked_provisional: int = 0
    ambiguous: int = 0
    unresolved: int = 0
    candidate_pairs: int = 0
    candidates: int = 0
    llm_eligible: int = 0
    llm_skipped: int = 0
    llm_valid: int = 0
    llm_invalid: int = 0
    llm_parse_failure: int = 0
    validator_official: int = 0
    validator_candidate_edge: int = 0
    validator_rejected: int = 0
    reasons: Counter = field(default_factory=Counter)
    skip_reasons: Counter = field(default_factory=Counter)
    seconds_per_article: list[float] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if not isinstance(v, (Counter, list))}
        d["rejection_reasons"] = dict(self.reasons)
        d["llm_skipped_reasons"] = dict(self.skip_reasons)
        s = self.seconds_per_article
        d["mean_seconds_per_article"] = round(sum(s) / len(s), 2) if s else None
        return d


@dataclass
class ArticleResult:
    article: Article
    mentions: list[Mention] = field(default_factory=list)
    candidates: list[RelationCandidate] = field(default_factory=list)
    verdicts: dict[str, Verdict | None] = field(default_factory=dict)
    skipped: dict[str, list[ReasonCode]] = field(default_factory=dict)


def process_article(article: Article, relations: dict, resolver: EntityResolver, store: EdgeStore,
                    ner: NER | None = None, verifier: Verifier | None = None, counters: Counters | None = None,
                    registry_dictionary: bool = True, sentence_ner: bool = True) -> ArticleResult:
    t0 = time.perf_counter()
    cn = counters or Counters()
    text = normalize_text(article.text)
    article = article.model_copy(update={"text": text})  # offsets always refer to normalized text
    sentences = split_sentences(text)
    if ner is None:
        ner_mentions = []
    elif sentence_ner and hasattr(ner, "extract_sentences"):
        ner_mentions = ner.extract_sentences(text, sentences)
    else:
        ner_mentions = ner.extract(text)
    dic = resolver.scan_dictionary(text) if registry_dictionary else []
    mentions = merge_mentions(ner_mentions, dic, text, sentences)
    mentions = resolver.resolve_article(article.article_id, text, sentences, mentions)

    cn.articles += 1
    cn.mentions_total += len(mentions)
    for m in mentions:
        in_scope, _ = classify_scope(m)
        cn.mentions_in_scope += in_scope
        cn.out_of_scope += not in_scope
        cn.mentions_person_org_bank += m.label.value in ("PERSON", "ORGANIZATION", "BANK")
        if m.entity_id and m.link_status == "resolved":
            cn.linked_verified += 1
        elif m.entity_id:
            cn.linked_provisional += 1
        elif m.link_status == "ambiguous":
            cn.ambiguous += 1
        elif in_scope:
            cn.unresolved += 1

    status_of = {m.entity_id: resolver.store.get_entity(m.entity_id)["resolution_status"] for m in mentions if m.entity_id}
    cands = generate_candidates(sentences, mentions, relations, article.article_id)
    for c in cands:
        c.subject_entity_status = status_of.get(c.subject.entity_id)
        c.object_entity_status = status_of.get(c.object.entity_id)
    cn.candidate_pairs += count_pairs(sentences, mentions, relations)
    cn.candidates += len(cands)
    res = ArticleResult(article=article, mentions=mentions, candidates=cands)

    seen_pairs: set[tuple] = set()
    for c in cands:
        spec = relations[c.predicate]
        pre = pre_llm_reasons(text, c, spec)
        pair = (c.predicate, c.subject.entity_id, c.object.entity_id, c.sentence_index)
        if not pre and pair in seen_pairs:
            pre = [ReasonCode.DUPLICATE]
        seen_pairs.add(pair)
        if pre:
            res.skipped[c.candidate_id] = pre
            cn.llm_skipped += 1
            cn.skip_reasons[pre[0].value] += 1
            store.reject(c, pre)
            cn.validator_rejected += 1
            cn.reasons.update(r.value for r in pre)
            continue
        verdict = None
        if verifier is not None:
            cn.llm_eligible += 1
            verdict = verifier.verify(c, spec.get("definition", ""))
            res.verdicts[c.candidate_id] = verdict
            if verdict is None:
                cn.llm_parse_failure += 1
            elif verdict.valid:
                cn.llm_valid += 1
            else:
                cn.llm_invalid += 1
        method = f"pattern+{verifier.model}" if verifier else "pattern"
        store.add(article, c, verdict, method, symmetric=bool(spec.get("symmetric")), relations_spec=spec,
                  verifier_ran=verifier is not None, model=getattr(verifier, "model", ""),
                  prompt_version=getattr(verifier, "prompt_version", ""))
        oc = store.outcomes[c.candidate_id]
        if oc.outcome == "official":
            cn.validator_official += 1
        elif oc.outcome == "candidate_edge":
            cn.validator_candidate_edge += 1
        else:
            cn.validator_rejected += 1
        cn.reasons.update(r.value for r in oc.reasons)
    cn.seconds_per_article.append(time.perf_counter() - t0)
    return res

