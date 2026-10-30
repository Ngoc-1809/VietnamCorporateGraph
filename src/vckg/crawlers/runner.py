"""Crawl one source from its RSS feed into SQLite staging (idempotent, resumable)."""
from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

import feedparser
import yaml

from vckg.crawlers.extract import ExtractionRejected, decode_response, extract_article
from vckg.crawlers.http import FetchError, PoliteClient, RobotsDisallowed
from vckg.storage.sqlite import Staging, canonicalize_url

log = logging.getLogger("vckg.crawler")


def load_sources(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def crawl_feed(source: str, feed_url: str, client: PoliteClient, staging: Staging, limit: int = 5) -> Counter:
    stats: Counter = Counter()
    try:
        resp = client.get(feed_url)
    except (RobotsDisallowed, FetchError) as e:
        log.warning(json.dumps({"event": "feed_failed", "source": source, "feed": feed_url, "err": str(e)}))
        stats["feed_failed"] += 1
        return stats
    feed = feedparser.parse(resp.content)
    entries = feed.entries[: limit * 3]  # headroom for dupes/rejections
    for ent in entries:
        if stats["inserted"] >= limit:
            break
        url = ent.get("link")
        if not url:
            continue
        stats["seen"] += 1
        if staging.url_seen(url) or staging.is_skipped(url):
            stats["duplicate_url"] += 1
            continue
        try:
            r = client.get(url)
            html = decode_response(r.content, r.charset_encoding)
            ex = extract_article(html, url)
        except RobotsDisallowed:
            stats["robots_disallowed"] += 1
            continue
        except FetchError as e:
            stats["fetch_error"] += 1
            log.warning(json.dumps({"event": "fetch_error", "url": url, "err": str(e)}))
            continue
        except ExtractionRejected as e:
            stats["rejected_" + str(e).split(":")[0]] += 1
            staging.skip(url, str(e))
            continue
        status, _ = staging.add_article(url, source, ex.title or ent.get("title", ""), ex.text,
                                          ex.published_at or ent.get("published"), ex.parser, r.status_code)
        stats[status] += 1
        log.info(json.dumps({"event": "article", "status": status, "url": canonicalize_url(url), "parser": ex.parser,
                             "chars": len(ex.text)}))
    staging.checkpoint(source, stats["seen"])
    return stats

