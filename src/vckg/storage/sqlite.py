"""SQLite staging: articles (URL + content-hash dedup), crawl checkpoints."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from vckg.models import Article

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles(
  article_id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, canonical_url TEXT UNIQUE NOT NULL,
  source TEXT NOT NULL, title TEXT, text TEXT NOT NULL, published_at TEXT, fetched_at TEXT NOT NULL,
  content_hash TEXT NOT NULL, parser TEXT, http_status INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS ix_articles_hash ON articles(content_hash);
CREATE TABLE IF NOT EXISTS checkpoints(
  source TEXT PRIMARY KEY, last_run_at TEXT, last_feed_etag TEXT, last_modified TEXT, items_seen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS skipped_urls(url TEXT PRIMARY KEY, reason TEXT, at TEXT);
"""

_TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "zarsrc"}


def canonicalize_url(url: str) -> str:
    p = urlsplit(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in _TRACKING]
    host = p.netloc.lower().removeprefix("www.")
    return urlunsplit((p.scheme.lower(), host, p.path.rstrip("/") or "/", urlencode(sorted(q)), ""))


def content_hash(text: str) -> str:
    norm = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def article_id_for(url: str) -> str:
    return hashlib.sha1(canonicalize_url(url).encode()).hexdigest()[:16]


def utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Staging:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def url_seen(self, url: str) -> bool:
        c = canonicalize_url(url)
        return self.db.execute("SELECT 1 FROM articles WHERE canonical_url=?", (c,)).fetchone() is not None

    def add_article(self, url: str, source: str, title: str, text: str, published_at: str | None,
                    parser: str = "", http_status: int | None = None) -> tuple[str, Article | None]:
        """Returns (status, article): 'inserted' | 'duplicate_url' | 'duplicate_content'."""
        canon = canonicalize_url(url)
        if self.url_seen(url):
            return "duplicate_url", None
        h = content_hash(text)
        if self.db.execute("SELECT 1 FROM articles WHERE content_hash=?", (h,)).fetchone():
            return "duplicate_content", None
        art = Article(article_id=article_id_for(url), url=url, source=source, title=title, text=text,
                      published_at=published_at, fetched_at=utcnow(), content_hash=h)
        self.db.execute(
            "INSERT INTO articles VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (art.article_id, url, canon, source, title, text, published_at, art.fetched_at, h, parser, http_status))
        self.db.commit()
        return "inserted", art

    def get_articles(self, limit: int | None = None, source: str | None = None) -> list[Article]:
        q, args = "SELECT * FROM articles", []
        if source:
            q += " WHERE source=?"
            args.append(source)
        q += " ORDER BY fetched_at"
        if limit:
            q += f" LIMIT {int(limit)}"
        return [Article(**{k: r[k] for k in ("article_id", "url", "source", "title", "text", "published_at",
                                             "fetched_at", "content_hash")}) for r in self.db.execute(q, args)]

    def count_articles(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    def skip(self, url: str, reason: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO skipped_urls VALUES(?,?,?)", (canonicalize_url(url), reason, utcnow()))
        self.db.commit()

    def is_skipped(self, url: str) -> bool:
        return self.db.execute("SELECT 1 FROM skipped_urls WHERE url=?", (canonicalize_url(url),)).fetchone() is not None

    def checkpoint(self, source: str, items_seen: int, etag: str | None = None, modified: str | None = None) -> None:
        self.db.execute(
            "INSERT INTO checkpoints VALUES(?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET last_run_at=excluded.last_run_at,"
            "last_feed_etag=excluded.last_feed_etag,last_modified=excluded.last_modified,"
            "items_seen=items_seen+excluded.items_seen", (source, utcnow(), etag, modified, items_seen))
        self.db.commit()

    def close(self) -> None:
        self.db.close()
