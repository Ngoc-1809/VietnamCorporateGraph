"""Entity linking: exact alias -> ticker -> conservative fuzzy -> context disambiguation.

Policy: never merge on name similarity alone. Anything not clearly supported stays 'unresolved'
(or 'ambiguous' when several registry entries tie)."""
from __future__ import annotations

from rapidfuzz import fuzz, process

from vckg.entity_linking.normalize import clean_surface, normalize_name
from vckg.entity_linking.registry import Registry
from vckg.models import EntityType, Mention

FUZZY_ORG_MIN = 93.0
FUZZY_PERSON_MIN = 100.0  # persons: exact normalized full name only
FUZZY_GAP = 4.0


class EntityLinker:
    def __init__(self, registry: Registry):
        self.reg = registry
        self._keys = list(registry.alias_index.keys())

    # ---- context ----
    def _context_score(self, eid: str, context: str) -> int:
        ctx = context.lower()
        entry = self.reg.entries[eid]
        score = sum(1 for h in getattr(entry, "context_hints", []) if h in ctx)
        # another registry entity that mentions this one's canonical name in context is weak support
        if entry.canonical_name.lower() in ctx:
            score += 2
        return score

    def _choose(self, cands: set[str], context: str) -> tuple[str | None, str]:
        if len(cands) == 1:
            return next(iter(cands)), "resolved"
        scored = sorted(((self._context_score(c, context), c) for c in cands), reverse=True)
        if scored[0][0] > scored[1][0]:
            return scored[0][1], "resolved"
        return None, "ambiguous"

    def link(self, mention: Mention, context: str = "") -> Mention:
        m = mention.model_copy()
        if m.entity_id and m.link_status == "resolved":
            return m
        is_p = m.label == EntityType.PERSON
        key = normalize_name(m.text, is_person=is_p)
        if not key:
            return m

        cands = {c for c in self.reg.alias_index.get(key, set()) if self.reg.compatible(m.label, self.reg.entries[c].type)}
        if not cands and m.text.isupper() and 2 <= len(m.text) <= 6:
            cands = {c for c in self.reg.ticker_index.get(clean_surface(m.text).upper(), set())
                     if self.reg.compatible(m.label, self.reg.entries[c].type)}
        if cands:
            eid, status = self._choose(cands, context)
            m.entity_id, m.link_status, m.link_score = eid, status, 100.0 if eid else 0.0
            return m

        # conservative fuzzy
        threshold = FUZZY_PERSON_MIN if is_p else FUZZY_ORG_MIN
        if threshold < 100 and len(key) >= 5:
            res = process.extract(key, self._keys, scorer=fuzz.token_sort_ratio, limit=3)
            good = []
            for k, score, _ in res:
                ids = {c for c in self.reg.alias_index[k] if self.reg.compatible(m.label, self.reg.entries[c].type)}
                if score >= threshold and ids:
                    good.append((score, k, ids))
            if good:
                top = good[0]
                if len(good) > 1 and top[0] - good[1][0] < FUZZY_GAP and good[1][2] != top[2]:
                    m.link_status = "ambiguous"
                    return m
                eid, status = self._choose(top[2], context)
                if eid:
                    m.entity_id, m.link_status, m.link_score = eid, status, float(top[0])
                else:
                    m.link_status = status
        return m
