"""Auxiliary identity sources (Entity Registry only). Everything produced here is identity_only=True:
names / tickers / legal-name slugs. These records never create graph edges and never count as press evidence."""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, Field

from vckg.entity_linking.store import RegistryStore, now
from vckg.models import EntityType, ResolutionStatus


class IdentityRecord(BaseModel):
    provider: str
    source_url: str
    fetched_at: str
    identity_only: bool = True
    name: str
    entity_type: EntityType = EntityType.ORGANIZATION
    ticker: str | None = None
    aliases: list[str] = Field(default_factory=list)
    name_is_accentless: bool = False
    status: ResolutionStatus = ResolutionStatus.VERIFIED
    source_type: str = "identity_provider"


class IdentityProvider(Protocol):
    name: str

    def fetch(self) -> Iterable[IdentityRecord]: ...


_COMPANY_URL = re.compile(r"^/([A-Z][A-Z0-9]{1,4})-([a-z0-9][a-z0-9\-]+)\.htm$")


def _is_bank(name_words: str) -> bool:
    return name_words.startswith(("ngan hang", "tmcp ngan hang", "ngan-hang"))


class VietstockSitemapProvider:
    """Reads company page slugs `/TICKER-ten-phap-nhan.htm` from the public Vietstock Finance sitemap
    (robots.txt lists the sitemap explicitly; one polite request). Slugs carry no accents, so records are
    flagged name_is_accentless. We take only ticker + legal-name words, nothing from the page bodies."""

    name = "vietstock_finance_sitemap"

    def __init__(self, client, sitemap_url: str = "https://finance.vietstock.vn/sitemap.xml"):
        self.client, self.sitemap_url = client, sitemap_url

    def fetch(self) -> Iterable[IdentityRecord]:
        r = self.client.get(self.sitemap_url)  # PoliteClient: robots.txt, rate limit, retry
        fetched = now()
        locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
        yield from self.parse(locs, fetched)

    def parse(self, locs: Iterable[str], fetched_at: str) -> Iterable[IdentityRecord]:
        seen: set[str] = set()
        for url in locs:
            path = unquote(urlsplit(url).path)
            m = _COMPANY_URL.match(path)
            if not m:
                continue
            ticker, slug = m.group(1), m.group(2)
            if ticker in seen or slug.count("-") < 1:
                continue
            seen.add(ticker)
            words = slug.replace("-", " ")
            yield IdentityRecord(
                provider=self.name, source_url=url, fetched_at=fetched_at, name=words, ticker=ticker,
                entity_type=EntityType.BANK if _is_bank(words) else EntityType.ORGANIZATION, name_is_accentless=True)


class HandwrittenSeedProvider:
    """The 19 hand-written Phase-1 entries: PROVISIONAL (no external verification), source_type=seed_handwritten."""

    name = "handwritten_seed"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def fetch(self) -> Iterable[IdentityRecord]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for e in data["entries"]:
            yield IdentityRecord(
                provider=self.name, source_url=f"file://{self.path.name}", fetched_at=now(), identity_only=True,
                name=e["canonical_name"], entity_type=EntityType(e["type"]), ticker=(e.get("tickers") or [None])[0],
                aliases=e.get("aliases", []), status=ResolutionStatus.PROVISIONAL, source_type="seed_handwritten")


def load_provider(store: RegistryStore, provider: IdentityProvider, limit: int | None = None) -> dict:
    """Idempotent: re-running adds nothing new. Returns counters."""
    added = existing = n = 0
    for rec in provider.fetch():
        if limit and n >= limit:
            break
        n += 1
        if rec.entity_type == EntityType.PERSON:
            continue  # providers here supply organizations only
        eid, created = store.add_entity(
            rec.name, rec.entity_type, ticker=rec.ticker, status=rec.status, provider=rec.provider,
            source_url=rec.source_url, fetched_at=rec.fetched_at, identity_only=rec.identity_only,
            source_type=rec.source_type)
        for a in rec.aliases:
            store.add_alias(eid, a, "alias", source_type=rec.source_type, provider=rec.provider,
                            source_url=rec.source_url, fetched_at=rec.fetched_at, identity_only=rec.identity_only)
        added += created
        existing += not created
    return {"provider": provider.name, "records": n, "entities_added": added, "already_present": existing}

