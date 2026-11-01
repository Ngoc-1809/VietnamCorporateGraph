"""Phase 6F - candidate ranking helpers for the crawl pilot: registry-identity signal and per-source cap. Ranking only decides WHICH articles are fetched; it is
never evidence for an edge. Everything is recorded per candidate in crawl_plan.json (strategy, bonus, matched identities, reason)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from vckg.entity_linking.normalize import fold

STRATEGY = "topic-ranked(phase5 signals) + registry-identity bonus + per-source cap (fallback only when no other cleared source has candidates)"
IDENTITY_STATUSES = ("VERIFIED", "EXTERNAL_VERIFIED")
_GENERIC = {"viet nam", "ngan hang", "tap doan", "xay dung", "dau tu", "cong nghe", "thuong mai", "dich vu", "phat trien", "quoc te", "nha nuoc", "chung khoan", "bat dong san",
            "viet", "nam", "hoa", "phat", "bao", "bank", "group", "holdings", "vina", "trang", "song hong", "co dien lanh"}


def load_compliance(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["sources"]


def cleared_sources(compliance: dict, wanted: list[str] | tuple[str, ...] | None = None) -> list[str]:
    ok = [k for k, v in compliance.items() if v.get("cleared") is True]
    return [k for k in (wanted or ok) if k in ok]


def slug_text(url: str) -> str:
    s = urlsplit(url).path.rsplit("/", 1)[-1]
    s = re.sub(r"(?:-?\d{6,}|-d\d+|-\d{10,})?\.(?:html|htm|chn)$", "", s)
    return s.replace("-", " ")


class IdentityIndex:
    """VERIFIED organisation names/aliases of the registry (read-only). `matches(text)` -> entity ids whose alias occurs as a whole-token n-gram in the folded text.
    3-letter tickers and generic words are ignored (too ambiguous for a ranking signal)."""

    def __init__(self, registry: Path):
        self.alias: dict[str, set[str]] = {}
        db = sqlite3.connect(f"file:{Path(registry).as_posix()}?mode=ro", uri=True)
        try:
            q = ",".join("?" * len(IDENTITY_STATUSES))
            for eid, key in db.execute(f"SELECT a.entity_id, a.alias_key FROM aliases a JOIN entities e ON e.entity_id=a.entity_id WHERE e.merged_into IS NULL "
                                       f"AND e.entity_type<>'PERSON' AND e.resolution_status IN ({q})", IDENTITY_STATUSES):
                k = (key or "").strip()
                toks = k.split()
                if k in _GENERIC or (len(toks) == 1 and len(k) < 5) or len(toks) > 6:
                    continue
                self.alias.setdefault(k, set()).add(eid)
        finally:
            db.close()

    def matches(self, text: str) -> list[str]:
        toks = fold(text).split()
        found: dict[str, str] = {}
        for n in range(1, 7):
            for i in range(len(toks) - n + 1):
                k = " ".join(toks[i:i + n])
                if k in self.alias:
                    for e in self.alias[k]:
                        found.setdefault(e, k)
        return sorted(found.values())


def identity_bonus(n_matches: int) -> float:
    return round(min(n_matches, 2) * 1.5, 2)


def pick_next(pending: list[dict], inserted_by_source: dict[str, int], cap: int) -> dict | None:
    """Highest strategy score first; skip sources at their cap unless NO other source still has pending candidates (then the cap is lifted and the row says so)."""
    def key(r):
        return (-(float(r.get("selection_score") or 0) + float(r.get("identity_bonus") or 0)), r["url"])
    under = [r for r in pending if inserted_by_source.get(r["source"], 0) < cap]
    if under:
        return min(under, key=key)
    if pending:
        r = min(pending, key=key)
        r["cap_lifted"] = True
        return r
    return None
