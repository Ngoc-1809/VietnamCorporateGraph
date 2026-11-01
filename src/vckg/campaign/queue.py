"""Durable acquisition + NLP queue for the mass campaign (SQLite on T:). Discovery, crawl, parse and NLP statuses are tracked SEPARATELY per URL.

  discovery   a row exists  (discovered_via: sitemap | rss | seed)
  crawl_status  pending | fetched | failed | robots_disallowed | restricted | skipped
  parse_status  NULL | ok | rejected_too_short | rejected_encoding_errors | duplicate_url | duplicate_content | failed
  nlp_status    NULL | pending | chunked | done | failed | deferred        (deferred = NOT processed because the inference budget ran out; never 'done')

Raw pages (zlib) live in a separate SQLite (`raw_pages.sqlite`); extracted articles go to the project staging SQLite (`Staging.add_article`, which deduplicates by
canonical URL and content hash and is never rewritten). Nothing in this module deletes data."""
from __future__ import annotations

import sqlite3
import time
import zlib
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS urls(
  url TEXT PRIMARY KEY, source TEXT NOT NULL, slug TEXT, lastmod TEXT, score REAL NOT NULL DEFAULT 0, topic TEXT, identity_bonus REAL NOT NULL DEFAULT 0,
  discovered_via TEXT, discovered_at TEXT,
  crawl_status TEXT NOT NULL DEFAULT 'pending', crawl_attempts INTEGER NOT NULL DEFAULT 0, next_try_at TEXT, crawl_error TEXT, http_status INTEGER, fetched_at TEXT,
  parse_status TEXT, parse_detail TEXT, article_id TEXT, content_hash TEXT, chars INTEGER,
  nlp_status TEXT, chunk_id TEXT, nlp_error TEXT, nlp_updated_at TEXT);
CREATE INDEX IF NOT EXISTS ix_urls_crawl ON urls(crawl_status, source, score DESC);
CREATE INDEX IF NOT EXISTS ix_urls_nlp ON urls(nlp_status, score DESC);
CREATE INDEX IF NOT EXISTS ix_urls_article ON urls(article_id);
CREATE TABLE IF NOT EXISTS sitemaps(url TEXT PRIMARY KEY, source TEXT NOT NULL, kind TEXT, status TEXT NOT NULL DEFAULT 'pending', n_urls INTEGER, n_new INTEGER, lastmod TEXT,
  fetched_at TEXT, attempts INTEGER NOT NULL DEFAULT 0, error TEXT);
CREATE TABLE IF NOT EXISTS chunks(chunk_id TEXT PRIMARY KEY, created_at TEXT, n_articles INTEGER, status TEXT NOT NULL, started_at TEXT, finished_at TEXT, qwen_live INTEGER,
  done INTEGER, failed INTEGER, deferred INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def retry_locked(fn, tries: int = 8):
    """Run a sqlite write that may hit 'database is locked' (several writers share staging.sqlite)."""
    for i in range(tries):
        try:
            return fn()
        except sqlite3.OperationalError as e:
            if "locked" not in str(e).lower() or i == tries - 1:
                raise
            time.sleep(0.5 * (i + 1))


class Queue:
    """One instance per thread (sqlite3 connections are thread-bound); all share the same file. Writers retry on lock."""

    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = Path(path)
        self.db = sqlite3.connect(str(path), timeout=60)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=60000")
        retry_locked(lambda: self.db.execute("PRAGMA journal_mode=WAL"))
        retry_locked(lambda: self.db.executescript(SCHEMA))

    def close(self) -> None:
        self.db.close()

    # ------------------------------------------------------------------ meta
    def meta(self, key: str, default: str | None = None) -> str | None:
        r = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r[0] if r else default

    def set_meta(self, key: str, value) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, str(value)))

    # ------------------------------------------------------------------ discovery
    def add_discovered(self, rows: list[dict], known_urls: set[str] | None = None) -> tuple[int, int]:
        """rows: url (canonical), source, slug, lastmod, score, topic, identity_bonus, via. Existing queue rows and already-staged URLs are skipped. -> (new, skipped)"""
        new = skipped = 0
        t = now()
        with self.db:
            for r in rows:
                if known_urls is not None and r["url"] in known_urls:
                    skipped += 1
                    continue
                cur = self.db.execute("INSERT OR IGNORE INTO urls(url,source,slug,lastmod,score,topic,identity_bonus,discovered_via,discovered_at) VALUES(?,?,?,?,?,?,?,?,?)",
                                      (r["url"], r["source"], r.get("slug"), r.get("lastmod"), r.get("score", 0.0), r.get("topic"), r.get("identity_bonus", 0.0), r.get("via"), t))
                new += cur.rowcount
                skipped += 1 - cur.rowcount
        return new, skipped

    def sitemap_upsert(self, url: str, source: str, kind: str) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO sitemaps(url,source,kind) VALUES(?,?,?)", (url, source, kind))

    def sitemap_done(self, url: str, n_urls: int, n_new: int, ok: bool = True, error: str | None = None) -> None:
        with self.db:
            self.db.execute("UPDATE sitemaps SET status=?, n_urls=?, n_new=?, fetched_at=?, attempts=attempts+1, error=? WHERE url=?",
                            ("done" if ok else "failed", n_urls, n_new, now(), error, url))

    def next_sitemaps(self, source: str, kind: str | None = None, max_attempts: int = 3) -> list[sqlite3.Row]:
        """All pending/failed sitemaps (caller sorts: CafeF archive names embed y-m-d ranges, which do not sort lexicographically)."""
        q = "SELECT * FROM sitemaps WHERE source=? AND status IN ('pending','failed') AND attempts<?"
        a: list = [source, max_attempts]
        if kind:
            q += " AND kind=?"
            a.append(kind)
        return list(self.db.execute(q, a))

    def sitemap_reset_if_older(self, source: str, kind: str, hours: float) -> int:
        cutoff = (datetime.now().astimezone() - timedelta(hours=hours)).isoformat(timespec="seconds")
        with self.db:
            return self.db.execute("UPDATE sitemaps SET status='pending', attempts=0 WHERE source=? AND kind=? AND status='done' AND fetched_at<?", (source, kind, cutoff)).rowcount

    # ------------------------------------------------------------------ crawl
    def pool(self, source: str, min_score: float) -> int:
        return self.db.execute("SELECT COUNT(*) FROM urls WHERE source=? AND crawl_status='pending' AND score>=? AND (next_try_at IS NULL OR next_try_at<=?)", (source, min_score, now())).fetchone()[0]

    def next_to_crawl(self, source: str, min_score: float) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM urls WHERE source=? AND crawl_status='pending' AND score>=? AND (next_try_at IS NULL OR next_try_at<=?) "
                               "ORDER BY score DESC, url LIMIT 1", (source, min_score, now())).fetchone()

    def mark_crawl(self, url: str, status: str, *, http_status: int | None = None, error: str | None = None, retry_in: float | None = None) -> None:
        with self.db:
            if retry_in is not None:
                self.db.execute("UPDATE urls SET crawl_status='pending', crawl_attempts=crawl_attempts+1, crawl_error=?, next_try_at=? WHERE url=?",
                                (error, (datetime.now().astimezone() + timedelta(seconds=retry_in)).isoformat(timespec="seconds"), url))
            else:
                self.db.execute("UPDATE urls SET crawl_status=?, crawl_attempts=crawl_attempts+1, crawl_error=?, http_status=?, fetched_at=? WHERE url=?", (status, error, http_status, now(), url))

    def mark_parse(self, url: str, status: str, *, detail: str | None = None, article_id: str | None = None, content_hash: str | None = None, chars: int | None = None) -> None:
        with self.db:
            self.db.execute("UPDATE urls SET parse_status=?, parse_detail=?, article_id=COALESCE(?,article_id), content_hash=COALESCE(?,content_hash), chars=?, "
                            "nlp_status=CASE WHEN ?='ok' THEN 'pending' ELSE nlp_status END WHERE url=?", (status, detail, article_id, content_hash, chars, status, url))

    # ------------------------------------------------------------------ nlp
    def pending_nlp(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM urls WHERE nlp_status='pending'").fetchone()[0]

    def take_chunk(self, chunk_id: str, size: int) -> list[sqlite3.Row]:
        """Reserve the next `size` parsed articles (highest score first, sources interleaved by rank) for a chunk."""
        with self.db:
            rows = list(self.db.execute("SELECT * FROM urls WHERE nlp_status='pending' AND article_id IS NOT NULL ORDER BY score DESC, url LIMIT ?", (size,)))
            ids = [r["url"] for r in rows]
            for u in ids:
                self.db.execute("UPDATE urls SET nlp_status='chunked', chunk_id=?, nlp_updated_at=? WHERE url=?", (chunk_id, now(), u))
            if rows:
                self.db.execute("INSERT OR REPLACE INTO chunks(chunk_id,created_at,n_articles,status) VALUES(?,?,?,'created')", (chunk_id, now(), len(rows)))
        return rows

    def chunk_rows(self, chunk_id: str) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM urls WHERE chunk_id=? ORDER BY score DESC, url", (chunk_id,)))

    def open_chunk(self) -> str | None:
        r = self.db.execute("SELECT chunk_id FROM chunks WHERE status IN ('created','running') ORDER BY chunk_id LIMIT 1").fetchone()
        return r[0] if r else None

    def next_chunk_id(self, prefix: str = "camp-c") -> str:
        n = self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        return f"{prefix}{n + 1:05d}"

    def set_nlp(self, article_id: str, status: str, error: str | None = None) -> None:
        with self.db:
            self.db.execute("UPDATE urls SET nlp_status=?, nlp_error=?, nlp_updated_at=? WHERE article_id=?", (status, error, now(), article_id))

    def release_to_pending(self, article_id: str) -> None:
        with self.db:
            self.db.execute("UPDATE urls SET nlp_status='pending', chunk_id=NULL, nlp_updated_at=? WHERE article_id=?", (now(), article_id))

    def chunk_update(self, chunk_id: str, **kw) -> None:
        with self.db:
            for k, v in kw.items():
                self.db.execute(f"UPDATE chunks SET {k}=? WHERE chunk_id=?", (v, chunk_id))

    # ------------------------------------------------------------------ KPIs
    def counts(self) -> dict:
        q = lambda s, *a: self.db.execute(s, a).fetchall()
        one = lambda s, *a: self.db.execute(s, a).fetchone()[0]
        return {
            "discovered": one("SELECT COUNT(*) FROM urls"),
            "discovered_by_source": {r[0]: r[1] for r in q("SELECT source, COUNT(*) FROM urls GROUP BY 1")},
            "crawl": {r[0]: r[1] for r in q("SELECT crawl_status, COUNT(*) FROM urls GROUP BY 1")},
            "parse": {str(r[0]): r[1] for r in q("SELECT parse_status, COUNT(*) FROM urls WHERE crawl_status<>'pending' GROUP BY 1")},
            "downloaded": one("SELECT COUNT(*) FROM urls WHERE crawl_status='fetched'"),
            "parsed_ok": one("SELECT COUNT(*) FROM urls WHERE parse_status='ok'"),
            "nlp": {str(r[0]): r[1] for r in q("SELECT nlp_status, COUNT(*) FROM urls WHERE parse_status='ok' GROUP BY 1")},
            "by_publisher": {r[0]: r[1] for r in q("SELECT source, COUNT(*) FROM urls WHERE parse_status='ok' GROUP BY 1")},
            "by_topic": {str(r[0]): r[1] for r in q("SELECT topic, COUNT(*) FROM urls WHERE parse_status='ok' GROUP BY 1")},
            "failed_crawl": one("SELECT COUNT(*) FROM urls WHERE crawl_status IN ('failed','robots_disallowed','restricted')"),
            "sitemaps": {r[0]: r[1] for r in q("SELECT status, COUNT(*) FROM sitemaps GROUP BY 1")},
        }

    def acquired_new(self) -> int:
        """Genuinely new articles stored by the campaign (parse ok => a NEW staging row was inserted)."""
        return self.db.execute("SELECT COUNT(*) FROM urls WHERE parse_status='ok'").fetchone()[0]


class RawPages:
    """Raw HTML store (zlib). One row per URL; re-fetches never overwrite an existing page."""

    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), timeout=60)
        self.db.execute("PRAGMA busy_timeout=60000")
        retry_locked(lambda: self.db.execute("PRAGMA journal_mode=WAL"))
        retry_locked(lambda: self.db.execute("CREATE TABLE IF NOT EXISTS pages(url TEXT PRIMARY KEY, fetched_at TEXT, http_status INTEGER, charset TEXT, nbytes INTEGER, html BLOB)"))

    def put(self, url: str, content: bytes, http_status: int, charset: str | None) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO pages VALUES(?,?,?,?,?,?)", (url, now(), http_status, charset, len(content), zlib.compress(content, 6)))

    def get(self, url: str) -> bytes | None:
        r = self.db.execute("SELECT html FROM pages WHERE url=?", (url,)).fetchone()
        return zlib.decompress(r[0]) if r else None

    def close(self) -> None:
        self.db.close()


