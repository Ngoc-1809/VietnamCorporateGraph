"""Dictionary/alias matcher producing Mentions with exact offsets."""
from __future__ import annotations

import re

from vckg.entity_linking.registry import Registry
from vckg.models import Mention


class DictionaryMatcher:
    def __init__(self, registry: Registry):
        self.registry = registry
        forms: dict[str, list[tuple[str, bool]]] = {}
        for surface, eid, is_ticker in registry.surface_forms():
            forms.setdefault(surface, []).append((eid, is_ticker))
        # longest surface first so that 'Ngân hàng VPBank' wins over 'VPBank'
        self._forms = sorted(forms.items(), key=lambda kv: -len(kv[0]))
        self._compiled = [
            (re.compile(rf"(?<![\w]){re.escape(s)}(?![\w])", 0 if (len(s) <= 4 or ids[0][1]) else re.IGNORECASE), s, ids)
            for s, ids in self._forms
        ]

    def find(self, text: str) -> list[Mention]:
        taken: list[tuple[int, int]] = []
        out: list[Mention] = []
        for rx, surface, ids in self._compiled:
            for m in rx.finditer(text):
                s, e = m.span()
                if any(s < te and ts < e for ts, te in taken):
                    continue
                eids = sorted({i for i, _ in ids})
                etype = self.registry.entries[eids[0]].type
                men = Mention(text=text[s:e], start=s, end=e, label=etype, confidence=1.0, method="dictionary")
                if len(eids) == 1:
                    men.entity_id, men.link_status, men.link_score = eids[0], "resolved", 100.0
                else:
                    men.link_status = "ambiguous"
                taken.append((s, e))
                out.append(men)
        return sorted(out, key=lambda x: x.start)
