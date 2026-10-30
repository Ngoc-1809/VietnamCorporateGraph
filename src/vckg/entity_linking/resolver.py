"""Article-first entity resolution on top of RegistryStore.

Pipeline per mention: scope filter -> parenthetical alias grouping -> exact canonical -> alias -> ticker (only with
context) -> fuzzy (candidate list; auto-link only with context support) -> contextual disambiguation ->
otherwise create a PROVISIONAL entity (organizations) or an article-scoped identity cluster (persons).

Hard rules:
 * persons are never keyed by name alone across the corpus: provisional id = person:{name}@art:{article_id};
   clusters merge only through `consolidate_persons` (shared organization context) and are logged;
 * a bare upper-case token is not a ticker: tickers link only with a textual cue or entity-name context;
 * fuzzy matches never merge entities - at most they list `candidate_entity_ids` for review."""
from __future__ import annotations

import re

from vckg.entity_linking.normalize import fold, normalize_name, slugify, strip_accents
from vckg.entity_linking.store import Candidate, RegistryStore
from vckg.models import ORG_LIKE, EntityType, Mention, ResolutionStatus, Sentence
from vckg.ner.scope import classify_scope
from vckg.preprocessing.text import sentence_index_for

_TICKER_CUE = re.compile(
    r"(?:cổ phiếu|cp|mã(?: chứng khoán| ck| cổ phiếu)?|ticker|hose|hsx|hnx|upcom)\s*[:\-]?\s*\(?$", re.IGNORECASE)
_PREFIX_LEFT = re.compile(r"(?:(?:ngan hang|tmcp|cong ty|co phan|ctcp|tap doan|tong cong ty|tnhh|thuong mai)\s+)+$")
_STOP_SINGLE = {"viet", "nam", "phat", "thanh", "dong", "tin", "hoa", "viet nam", "quoc", "gia", "dau", "tu", "xay", "dung",
                "thuong", "mai", "co", "phan", "tai", "chinh", "ngan", "hang"}
MAX_NGRAM = 8
ACRONYM_MIN_SCORE = 0.8
ACRONYM_STOP = {"GDP", "CPI", "USD", "VND", "EUR", "FDI", "IPO", "ETF", "TPCP", "UBND", "HĐQT", "CEO", "CFO", "NHNN", "ĐHĐCĐ", "BCTC",
                "VAT", "EPS", "ROE", "ROA", "WTO", "IMF", "FED", "FTA", "ASEAN", "OPEC", "NATO", "KCN", "KLGD", "ESG", "CTCK",
                "BHXH", "HNX", "HOSE", "UPCOM", "OTC", "AI", "IT", "PMI", "PPI", "OPEC+", "G7", "G20", "EU", "UN", "FOMC"}


def is_ticker_like(s: str) -> bool:
    return s.isupper() and 2 <= len(s) <= 5 and " " not in s and any(c.isalpha() for c in s)


class EntityResolver:
    def __init__(self, store: RegistryStore, *, fuzzy_min: float = 93.0, min_ner_score: float = 0.5):
        self.store, self.fuzzy_min, self.min_ner_score = store, fuzzy_min, min_ner_score
        self._dict_version = -1
        self._keys: dict[str, int] = {}

    # ------------------------------------------------------------------ dictionary scan over the registry
    def _refresh_keys(self) -> None:
        if self._dict_version == self.store.version:
            return
        keys: dict[str, int] = {}
        for r in self.store.db.execute(
            "SELECT DISTINCT a.alias_key FROM aliases a JOIN entities e ON e.entity_id=a.entity_id "
            "WHERE a.kind!='ticker' AND e.entity_type!='PERSON' AND e.merged_into IS NULL"):
            k = r[0]
            n = len(k.split())
            if n == 1 and (len(k) < 5 or k in _STOP_SINGLE):
                continue
            if n <= MAX_NGRAM:
                keys[k] = n
        self._keys, self._dict_version = keys, self.store.version

    def scan_dictionary(self, text: str) -> list[Mention]:
        """Registry-driven mentions (orgs). Proper-noun guard: span must start upper-case in the source text."""
        self._refresh_keys()
        folded = strip_accents(text).lower()
        if len(folded) != len(text):  # offsets would drift; skip rather than guess
            return []
        toks = [(m.group(), m.start(), m.end()) for m in re.finditer(r"\w+", folded)]
        taken: list[tuple[int, int]] = []
        out: list[Mention] = []
        i = 0
        while i < len(toks):
            hit = None
            for n in range(min(MAX_NGRAM, len(toks) - i), 0, -1):
                seg = toks[i:i + n]
                if any(folded[seg[j][2]:seg[j + 1][1]].strip(" \t-") for j in range(n - 1)):
                    continue
                phrase = " ".join(t[0] for t in seg)
                if phrase in self._keys:
                    hit = (n, seg[0][1], seg[-1][2], phrase)
                    break
            if not hit:
                i += 1
                continue
            n, s, e, phrase = hit
            if not text[s].isupper():
                i += 1
                continue
            m = _PREFIX_LEFT.search(folded[max(0, s - 40):s])
            if m:
                s = max(0, s - 40) + m.start()
            if any(s < te and ts < e for ts, te in taken):
                i += n
                continue
            cands = self.store.find_candidates(text[s:e], EntityType.ORGANIZATION, fuzzy_min=101)
            if cands:
                row = self.store.get_entity(cands[0].entity_id)
                out.append(Mention(text=text[s:e], start=s, end=e, label=EntityType(row["entity_type"]), method="dictionary"))
                taken.append((s, e))
            i += n
        # tickers: only with a textual cue; never from bare upper-case words
        for m in re.finditer(r"(?<![\w])[A-Z][A-Z0-9]{1,4}(?![\w])", text):
            s, e = m.span()
            if any(s < te and ts < e for ts, te in taken) or not self._ticker_cue(text, s, e):
                continue
            c = self.store.find_candidates(m.group(), EntityType.ORGANIZATION, allow_ticker=True, fuzzy_min=101)
            c = [x for x in c if x.method == "ticker"]
            if len(c) == 1:
                row = self.store.get_entity(c[0].entity_id)
                out.append(Mention(text=m.group(), start=s, end=e, label=EntityType(row["entity_type"]), method="dictionary_ticker"))
                taken.append((s, e))
        return sorted(out, key=lambda x: x.start)

    @staticmethod
    def _ticker_cue(text: str, s: int, e: int) -> bool:
        return bool(_TICKER_CUE.search(text[max(0, s - 24):s]))

    # ------------------------------------------------------------------ resolution
    def resolve_article(self, article_id: str, text: str, sentences: list[Sentence], mentions: list[Mention]) -> list[Mention]:
        folded_article = fold(text)
        ms = [m.model_copy(update={"article_id": article_id, "sentence_index": sentence_index_for(sentences, m.start)})
              for m in sorted(mentions, key=lambda x: (x.start, -(x.end - x.start)))]
        self._mark_parenthetical_aliases(text, ms)
        out: list[Mention] = []
        by_start: dict[int, Mention] = {}
        heads = [m for m in ms if m.alias_of is None]
        single = {id(m) for m in heads if m.label == EntityType.PERSON and len(normalize_name(m.text, is_person=True).split()) == 1}
        for m in [x for x in heads if id(x) not in single]:
            r = self._resolve_one(m, text, folded_article)
            by_start[m.start] = r
            out.append(r)
        names = self._article_person_tokens(out)
        for m in [x for x in heads if id(x) in single]:
            r = self._resolve_one(m, text, folded_article, names)
            by_start[m.start] = r
            out.append(r)
        for m in ms:
            if m.alias_of is not None:
                head = by_start.get(m.alias_of)
                if head is not None and head.entity_id and self._compatible(head.label, m.label):
                    m = m.model_copy(update={"entity_id": head.entity_id, "link_status": head.link_status,
                                             "linking_method": "parenthetical_alias", "candidate_entity_ids": [head.entity_id]})
                    self.store.add_alias(head.entity_id, m.text, "parenthetical", source_type="article")
                else:
                    m = m.model_copy(update={"linking_method": "parenthetical_alias_unlinked"})
                out.append(m)
        out.sort(key=lambda x: (x.start, x.end))
        self._add_person_context(article_id, out)
        for m in out:
            self.store.record_mention(m)
        return out

    @staticmethod
    def _compatible(a: EntityType, b: EntityType) -> bool:
        return (a == EntityType.PERSON) == (b == EntityType.PERSON)

    @staticmethod
    def _mark_parenthetical_aliases(text: str, ms: list[Mention]) -> None:
        ordered = sorted(range(len(ms)), key=lambda i: ms[i].start)
        for pos, i in enumerate(ordered):
            b = ms[i]
            if pos == 0 or not (b.end < len(text) and text[b.end] == ")"):
                continue
            a = ms[ordered[pos - 1]]
            if a.alias_of is None and text[a.end:b.start].strip() == "(" and (a.label == EntityType.PERSON) == (b.label == EntityType.PERSON):
                ms[i] = b.model_copy(update={"alias_of": a.start})

    def _link(self, m: Mention, entity_id: str, method: str, score: float | None, cands: list[str]) -> Mention:
        row = self.store.get_entity(entity_id)
        status = "resolved" if row["resolution_status"] == ResolutionStatus.VERIFIED.value else "provisional"
        upd = {"entity_id": row["entity_id"], "link_status": status, "linking_method": method,
               "link_score": score, "candidate_entity_ids": cands}
        etype = EntityType(row["entity_type"])
        if m.label != etype and m.label in ORG_LIKE and etype in ORG_LIKE:
            upd["label"] = etype  # org subtype (e.g. BANK) refined from the registry, not from the NER guess
        return m.model_copy(update=upd)

    @staticmethod
    def _article_person_tokens(resolved: list[Mention]) -> dict[str, set[str]]:
        """Given-name token -> person entity ids of the full-name persons resolved in THIS article."""
        idx: dict[str, set[str]] = {}
        for p in resolved:
            if p.label == EntityType.PERSON and p.entity_id:
                toks = normalize_name(p.text, is_person=True).split()
                if len(toks) >= 2:
                    idx.setdefault(toks[-1], set()).add(p.entity_id)
        return idx

    def _resolve_one(self, m: Mention, text: str, folded_article: str, names: dict[str, set[str]] | None = None) -> Mention:
        in_scope, why = classify_scope(m)
        if not in_scope:
            return m.model_copy(update={"link_status": "unresolved", "linking_method": f"out_of_scope:{why}"})
        if m.label == EntityType.PERSON:
            return self._resolve_person(m, why, text, folded_article, names)
        return self._resolve_org(m, text, folded_article)

    # ---- organizations
    def _context_support(self, entity_id: str, folded_article: str) -> int:
        n = 0
        for r in self.store.db.execute("SELECT alias_key,kind FROM aliases WHERE entity_id=?", (entity_id,)):
            if r["kind"] != "ticker" and len(r["alias_key"].split()) >= 2 and r["alias_key"] in folded_article:
                n += 1
        return n

    def _resolve_org(self, m: Mention, text: str, folded_article: str) -> Mention:
        ticker_like = is_ticker_like(m.text)
        cue = ticker_like and self._ticker_cue(text, m.start, m.end)
        cands = self.store.find_candidates(m.text, m.label, fuzzy_min=self.fuzzy_min, allow_ticker=ticker_like)
        acronym = ticker_like and not cue
        if acronym:
            # bare upper-case token: a registry hit is trusted only if the entity's full name is also in the article.
            # A token the registry does not know at all may be a real (unlisted) company acronym such as "VBOX":
            # it can become a PROVISIONAL entity, but never receives a ticker.
            ctx = [c for c in cands if self._context_support(c.entity_id, folded_article) > 0]
            if ctx:
                cands = ctx
            elif cands:
                return m.model_copy(update={"link_status": "unresolved", "linking_method": "ticker_without_context"})
        ids = [c.entity_id for c in cands]
        sure = [c for c in cands if c.method != "fuzzy"]
        if len(sure) == 1:
            return self._link(m, sure[0].entity_id, sure[0].method, None, ids)
        if len(sure) > 1:
            scored = sorted(((self._context_support(c.entity_id, folded_article), c) for c in sure), key=lambda t: -t[0])
            if scored[0][0] > scored[1][0]:
                return self._link(m, scored[0][1].entity_id, "context_disambiguation", None, ids)
            return m.model_copy(update={"link_status": "ambiguous", "linking_method": "alias_collision", "candidate_entity_ids": ids})
        fuzz_c: list[Candidate] = [c for c in cands if c.method == "fuzzy"]
        if fuzz_c:
            best = fuzz_c[0]
            top = {c.entity_id for c in fuzz_c if c.score == best.score}
            if len(top) == 1 and self._context_support(best.entity_id, folded_article) > 0:
                return self._link(m, best.entity_id, "fuzzy+context", best.score, ids)
            # similar-but-distinct: new provisional entity, similar ones only listed for human review
        return self._create_provisional_org(m, ids, acronym)

    def _create_provisional_org(self, m: Mention, cand_ids: list[str], acronym: bool = False) -> Mention:
        key = normalize_name(m.text)
        if acronym and (m.text in ACRONYM_STOP or len(m.text) < 3 or m.ner_score is None or m.ner_score < ACRONYM_MIN_SCORE):
            return m.model_copy(update={"link_status": "unresolved", "linking_method": "acronym_unverified"})
        if m.ner_score is not None and m.ner_score < self.min_ner_score:
            return m.model_copy(update={"link_status": "unresolved", "linking_method": "low_ner_score"})
        if len(key) < 3 or len(key.split()) > 12:
            return m.model_copy(update={"link_status": "unresolved", "linking_method": "bad_span"})
        eid, _ = self.store.add_entity(m.text, m.label, status=ResolutionStatus.PROVISIONAL, source_type="article")
        return self._link(m, eid, "new_provisional", None, cand_ids)

    # ---- persons
    def _resolve_person(self, m: Mention, why: str, text: str, folded_article: str,
                        names: dict[str, set[str]] | None = None) -> Mention:
        key = normalize_name(m.text, is_person=True)
        toks = key.split()
        if len(toks) < 2:
            hit = (names or {}).get(key, set())
            if len(hit) == 1:  # unique given-name match among the full names of this same article only
                return self._link(m, next(iter(hit)), "article_short_name", None, sorted(hit))
            return m.model_copy(update={"link_status": "unresolved", "linking_method": "person_single_token"})
        if m.ner_score is not None and m.ner_score < self.min_ner_score:
            return m.model_copy(update={"link_status": "unresolved", "linking_method": "low_ner_score"})
        cands = [c for c in self.store.find_candidates(m.text, EntityType.PERSON) if "@art:" not in c.entity_id]
        ids = [c.entity_id for c in cands]
        if len(cands) == 1 and len(toks) >= 3:  # curated full-name entry; 2-token names are too collision-prone
            return self._link(m, cands[0].entity_id, cands[0].method, None, ids)
        eid = f"person:{slugify(key)}@art:{m.article_id}"
        eid, _ = self.store.add_entity(m.text, EntityType.PERSON, entity_id=eid, status=ResolutionStatus.PROVISIONAL,
                                       source_type="article")
        out = self._link(m, eid, "article_identity_cluster", None, ids)
        return out

    def _add_person_context(self, article_id: str, ms: list[Mention]) -> None:
        orgs = [m for m in ms if m.entity_id and m.label != EntityType.PERSON and m.alias_of is None]
        for p in (m for m in ms if m.entity_id and m.label == EntityType.PERSON and m.alias_of is None):
            near = [o for o in orgs if o.sentence_index == p.sentence_index and abs(o.start - p.end) <= 150]
            if near:
                o = min(near, key=lambda x: abs(x.start - p.end))
                self.store.add_person_context(p.entity_id, o.entity_id, article_id)

    # ---- cross-article person consolidation (explicit, logged, idempotent)
    def consolidate_persons(self) -> int:
        rows = self.store.db.execute(
            "SELECT entity_id,name_key FROM entities WHERE entity_type='PERSON' AND merged_into IS NULL AND entity_id LIKE '%@art:%'"
        ).fetchall()
        by_key: dict[str, list[str]] = {}
        for r in rows:
            by_key.setdefault(r["name_key"], []).append(r["entity_id"])
        merged = 0
        for key, ids in by_key.items():
            ids = sorted(ids)
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    ca, cb = self.store.canonical_id(a), self.store.canonical_id(b)
                    if ca == cb:
                        continue
                    oa = {r[0] for r in self.store.db.execute("SELECT org_entity_id FROM person_context WHERE entity_id=?", (ca,))}
                    ob = {r[0] for r in self.store.db.execute("SELECT org_entity_id FROM person_context WHERE entity_id=?", (cb,))}
                    shared = {self.store.canonical_id(x) for x in oa} & {self.store.canonical_id(x) for x in ob}
                    if shared and self.store.merge_entities(min(ca, cb), max(ca, cb), f"same name_key '{key}' + shared org {sorted(shared)}"):
                        merged += 1
        return merged



