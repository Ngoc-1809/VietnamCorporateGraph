"""Mass-campaign discovery: news sitemaps (full archive), RSS feeds and Phase 5 category pages -> scored URL rows in the durable queue.

Scoring uses the Phase 5 topic signals on the title/summary/slug (`discovery.score_entry`) plus the registry-identity bonus (VERIFIED aliases in the slug). Ranking only
decides the ORDER of downloads; it is never evidence for an edge. Everything goes through PoliteClient (robots.txt, >= 2 s/host, backoff), so sitemap downloads obey
the same limits as article pages. Only URLs that look like articles of the source are queued; already-staged URLs are skipped (never recrawled)."""
from __future__ import annotations

import re
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

from vckg.campaign.queue import Queue
from vckg.crawlers.discovery import score_entry
from vckg.crawlers.targeted import Entry, discover
from vckg.jobs.selection import IdentityIndex, identity_bonus, slug_text
from vckg.storage.sqlite import canonicalize_url

ARTICLE_RX = {
    "vietstock": re.compile(r"^https?://(?:www\.)?vietstock\.vn/20\d\d/\d\d/.+-\d+-\d+\.htm$"),
    "cafef": re.compile(r"^https?://(?:www\.)?cafef\.vn/.+-\d{12,}\.chn$"),
}
FULL_SITEMAP = {"vietstock": "https://vietstock.vn/sitemap.xml"}
INDEX_SITEMAP = {"cafef": "https://cafef.vn/sitemap.xml"}
FRESH_SITEMAPS = {"cafef": ["https://cafef.vn/google-news-sitemap.xml", "https://cafef.vn/latest-news-sitemap.xml"]}
_URL_BLOCK = re.compile(r"<url>\s*<loc>([^<]+)</loc>(.*?)</url>", re.DOTALL)
_LASTMOD = re.compile(r"<lastmod>([^<]+)</lastmod>")
_LOC = re.compile(r"<loc>([^<]+)</loc>")
_ARCHIVE_NAME = re.compile(r"sitemaps-(\d{4})-(\d{1,2})-(\d{1,2})-(\d{1,2})\.xml$")


def archive_key(url: str) -> tuple[int, int, int]:
    m = _ARCHIVE_NAME.search(url)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)


def parse_sitemap_urls(xml: str) -> list[tuple[str, str | None]]:
    out = []
    for m in _URL_BLOCK.finditer(xml):
        lm = _LASTMOD.search(m.group(2))
        out.append((m.group(1).strip().replace("&amp;", "&"), lm.group(1) if lm else None))
    return out


def known_staged_urls(staging_db: Path) -> set[str]:
    db = sqlite3.connect(f"file:{Path(staging_db).as_posix()}?mode=ro", uri=True, timeout=60)
    try:
        return {r[0] for r in db.execute("SELECT canonical_url FROM articles")} | {r[0] for r in db.execute("SELECT url FROM skipped_urls")}
    finally:
        db.close()


def score_slug(source: str, url: str, ident: IdentityIndex | None, title: str = "", summary: str = "") -> dict:
    text = title or slug_text(url)
    r = score_entry(Entry(url, text, summary, source), "")
    ids = ident.matches(f"{text} {slug_text(url)}") if ident else []
    bonus = identity_bonus(len(ids))
    return {"score": round(r.score + bonus, 2), "topic": r.topic, "identity_bonus": bonus}


class Discovery:
    def __init__(self, queue: Queue, client_for: Callable[[str], object], staging_db: Path, sitemap_dir: Path, ident: IdentityIndex | None = None,
                 insert_floor: float = 1.0, low_water: int = 1500, feeds: dict[str, list[str]] | None = None, category_pages: dict[str, list[str]] | None = None,
                 log: Callable[..., None] = lambda **k: None):
        self.q, self.client_for, self.staging_db, self.dir, self.ident = queue, client_for, Path(staging_db), Path(sitemap_dir), ident
        self.floor, self.low_water, self.feeds, self.cats, self.log = insert_floor, low_water, feeds or {}, category_pages or {}, log
        self.dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ ingestion of a parsed URL list
    def _ingest(self, source: str, items: list[tuple[str, str | None]], via: str, known: set[str]) -> tuple[int, int, int]:
        rx = ARTICLE_RX.get(source)
        rows, dropped = [], 0
        for url, lastmod in items:
            if rx and not rx.match(url):
                continue
            can = canonicalize_url(url)
            sc = score_slug(source, can, self.ident)
            if sc["score"] < self.floor:
                dropped += 1
                continue
            rows.append({"url": can, "source": source, "slug": slug_text(can), "lastmod": lastmod, "via": via, **sc})
        new, _ = self.q.add_discovered(rows, known)
        return len(items), new, dropped

    def _fetch_text(self, source: str, url: str, save_as: str | None = None) -> str:
        r = self.client_for(source).get(url)
        if save_as:
            (self.dir / save_as).write_bytes(r.content)
        return r.content.decode("utf-8", "replace")

    # ------------------------------------------------------------------ per-source tick: make sure the pool of crawlable URLs is not running dry
    def tick(self, source: str, min_score: float) -> dict:
        """Returns what was done. Safe to call repeatedly; network only when the pool is below low-water or a refresh is due."""
        done: dict = {"sitemaps": 0, "new": 0}
        known = known_staged_urls(self.staging_db)
        if source in FULL_SITEMAP:
            u = FULL_SITEMAP[source]
            self.q.sitemap_upsert(u, source, "full")
            self.q.sitemap_reset_if_older(source, "full", 24)
            for sm in self.q.next_sitemaps(source, "full"):
                done = self._do_sitemap(source, sm["url"], known, done, save_as=f"{source}_sitemap.xml")
        if source in INDEX_SITEMAP:
            idx = INDEX_SITEMAP[source]
            self.q.sitemap_upsert(idx, source, "index")
            if self.q.db.execute("SELECT status FROM sitemaps WHERE url=?", (idx,)).fetchone()[0] != "done":
                try:
                    xml = self._fetch_text(source, idx)
                    for loc in _LOC.findall(xml):
                        if _ARCHIVE_NAME.search(loc):
                            self.q.sitemap_upsert(loc, source, "archive")
                    self.q.sitemap_done(idx, len(_LOC.findall(xml)), 0)
                except Exception as e:  # noqa: BLE001
                    self.q.sitemap_done(idx, 0, 0, ok=False, error=repr(e)[:200])
                    self.log(event="sitemap_failed", url=idx, error=repr(e)[:200])
            for f in FRESH_SITEMAPS.get(source, []):
                self.q.sitemap_upsert(f, source, "fresh")
            self.q.sitemap_reset_if_older(source, "fresh", 6)
            for sm in self.q.next_sitemaps(source, "fresh"):
                done = self._do_sitemap(source, sm["url"], known, done)
            while self.q.pool(source, min_score) < self.low_water:
                pend = sorted(self.q.next_sitemaps(source, "archive"), key=lambda r: archive_key(r["url"]), reverse=True)
                if not pend:
                    break
                done = self._do_sitemap(source, pend[0]["url"], known, done)
        if self.feeds.get(source) or self.cats.get(source):
            feed_key = f"rss:{source}"
            last = self.q.meta(feed_key)
            if last is None or time.time() - float(last) > 6 * 3600:
                done = self._do_feeds(source, known, done)
                self.q.set_meta(feed_key, time.time())
        return done

    def _do_sitemap(self, source: str, url: str, known: set[str], done: dict, save_as: str | None = None) -> dict:
        try:
            xml = self._fetch_text(source, url, save_as)
            n, new, dropped = self._ingest(source, parse_sitemap_urls(xml), "sitemap", known)
            self.q.sitemap_done(url, n, new)
            done["sitemaps"] += 1
            done["new"] += new
            self.log(event="sitemap", url=url, urls=n, new=new, below_floor=dropped)
        except Exception as e:  # noqa: BLE001  (a failing sitemap never stops discovery)
            self.q.sitemap_done(url, 0, 0, ok=False, error=repr(e)[:200])
            self.log(event="sitemap_failed", url=url, error=repr(e)[:200])
        return done

    def _do_feeds(self, source: str, known: set[str], done: dict) -> dict:
        try:
            ents = discover(self.client_for(source), source, {"feeds": self.feeds.get(source, []), "category_pages": self.cats.get(source, [])})
        except Exception as e:  # noqa: BLE001
            self.log(event="feeds_failed", source=source, error=repr(e)[:200])
            return done
        rows = []
        for e in ents:
            can = canonicalize_url(e.url)
            rx = ARTICLE_RX.get(source)
            if rx and not rx.match(e.url):
                continue
            sc = score_slug(source, can, self.ident, e.title, e.summary)
            if sc["score"] >= self.floor:
                rows.append({"url": can, "source": source, "slug": slug_text(can), "via": "rss", **sc})
        new, _ = self.q.add_discovered(rows, known)
        done["new"] += new
        self.log(event="feeds", source=source, entries=len(ents), new=new)
        return done
