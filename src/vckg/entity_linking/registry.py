"""Entity Registry: names/aliases/tickers only. Registry facts never become graph edges."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field

from vckg.entity_linking.normalize import normalize_name
from vckg.models import ORG_LIKE, EntityType, RegistryEntry


class RegistryRecord(RegistryEntry):
    context_hints: list[str] = Field(default_factory=list)  # lowercase words that support this sense


class _File(BaseModel):
    provenance_note: str = ""
    entries: list[RegistryRecord]


class Registry:
    def __init__(self, entries: list[RegistryRecord]):
        self.entries = {e.entity_id: e for e in entries}
        if len(self.entries) != len(entries):
            raise ValueError("duplicate entity_id in registry")
        self.alias_index: dict[str, set[str]] = defaultdict(set)
        self.ticker_index: dict[str, set[str]] = defaultdict(set)
        for e in entries:
            is_p = e.type == EntityType.PERSON
            for name in [e.canonical_name, *e.aliases]:
                k = normalize_name(name, is_person=is_p)
                if k:
                    self.alias_index[k].add(e.entity_id)
            for t in e.tickers:
                self.ticker_index[t.upper()].add(e.entity_id)

    @classmethod
    def load(cls, path: str | Path) -> Registry:
        data = _File.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
        return cls(data.entries)

    @staticmethod
    def compatible(mention_type: EntityType, entry_type: EntityType) -> bool:
        if mention_type == entry_type:
            return True
        return mention_type in ORG_LIKE and entry_type in ORG_LIKE

    def surface_forms(self) -> list[tuple[str, str, bool]]:
        """(surface, entity_id, is_ticker) for dictionary matching, raw (accented) surfaces."""
        out = []
        for e in self.entries.values():
            for s in {e.canonical_name, *e.aliases}:
                out.append((s, e.entity_id, False))
            for t in e.tickers:
                out.append((t, e.entity_id, True))
        return out
