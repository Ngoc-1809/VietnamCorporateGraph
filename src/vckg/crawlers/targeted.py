"""Small, controlled, signal-targeted crawl (NOT a production crawler).

Discovery: RSS feeds, or public category pages for sources whose RSS/sitemap is unusable (Bao Dau tu).
Ranking: accent-folded keyword score over title/summary/slug for relation signals. Fetching goes through
PoliteClient (robots.txt, per-host delay, retry/backoff) and the normal extraction quality gates."""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import feedparser

from vckg.crawlers.extract import ExtractionRejected, decode_response, extract_article
from vckg.crawlers.http import FetchError, PoliteClient, RobotsDisallowed
from vckg.entity_linking.normalize import fold
from vckg.models import Article
from vckg.storage.sqlite import Staging

SIGNALS: dict[str, int] = {
    "bo nhiem": 3, "mien nhiem": 3, "thoi giu chuc": 3, "tu nhiem": 3, "chu tich hdqt": 3, "chu tich": 1,
    "tong giam doc": 3, "hdqt": 2, "hoi dong quan tri": 2, "co dong lon": 3, "nam giu": 2, "so huu": 2, "thoai von": 2,
    "mua lai": 3, "thau tom": 3, "sap nhap": 3, "chuyen nhuong": 2, "cong ty con": 3, "cong ty me": 3,
    "cap tin dung": 3, "hop dong tin dung": 3, "cho vay": 2, "trai phieu": 2, "xu phat": 3, "khoi to": 3,
    "hop tac chien luoc": 3, "lien doanh": 3, "bat tay": 2, "ky ket": 1,
}


@dataclass
class Entry:
    url: str
    title: str
    summary: str
    source: str
    score: int = 0
    hits: list[str] = field(default_factory=list)


def score_text(text: str) -> tuple[int, list[str]]:
    f = fold(text)
    hits = [k for k in SIGNALS if k in f]
    return sum(SIGNALS[k] for k in hits), hits


def _slug_title(url: str) -> str:
    slug = urlsplit(url).path.rsplit("/", 1)[-1]
    slug = re.sub(r"(?:-d\d+)?\.(?:html|htm|chn)$", "", slug)
    return slug.replace("-", " ")


def entries_from_feed(client: PoliteClient, source: str, feed_url: str) -> list[Entry]:
    r = client.get(feed_url)
    feed = feedparser.parse(r.content)
    out = []
    for e in feed.entries:
        if e.get("link"):
            out.append(Entry(e["link"], e.get("title", ""), re.sub(r"<[^>]+>", " ", e.get("summary", "")), source))
    return out


def entries_from_category_page(client: PoliteClient, source: str, page_url: str) -> list[Entry]:
    r = client.get(page_url)
    html = decode_response(r.content, r.charset_encoding)
    host = "{0.scheme}://{0.netloc}".format(urlsplit(page_url))
    seen, out = set(), []
    for href in re.findall(r'href="((?:https?://[^"/]+)?/[^"]+-d\d+\.html)"', html):
        url = href if href.startswith("http") else host + href
        if url not in seen:
            seen.add(url)
            out.append(Entry(url, _slug_title(url), "", source))
    return out


def discover(client: PoliteClient, source: str, cfg: dict) -> list[Entry]:
    entries: list[Entry] = []
    for f in cfg.get("feeds", []):
        try:
            entries += entries_from_feed(client, source, f)
        except (RobotsDisallowed, FetchError):
            continue
    for p in cfg.get("category_pages", []):
        try:
            entries += entries_from_category_page(client, source, p)
        except (RobotsDisallowed, FetchError):
            continue
    for e in entries:
        e.score, e.hits = score_text(f"{e.title} {e.summary}")
    uniq: dict[str, Entry] = {}
    for e in entries:
        uniq.setdefault(e.url, e)
    return list(uniq.values())


def crawl_targeted(client: PoliteClient, staging: Staging, sources: dict, per_source: int, min_score: int = 3,
                   only: list[str] | None = None) -> tuple[Counter, list[dict], list[Article]]:
    stats: Counter = Counter()
    selected: list[dict] = []
    arts: list[Article] = []
    for key, cfg in sources.items():
        if only and key not in only:
            continue
        try:
            pool = discover(client, key, cfg)
        except Exception as e:  # noqa: BLE001 - one failing source must not stop the run
            stats[f"{key}:discover_error"] += 1
            selected.append({"source": key, "error": str(e)})
            continue
        stats[f"{key}:discovered"] = len(pool)
        ranked = sorted((e for e in pool if e.score >= min_score), key=lambda e: -e.score)
        got = 0
        for e in ranked:
            if got >= per_source:
                break
            if staging.url_seen(e.url) or staging.is_skipped(e.url):
                stats[f"{key}:already_staged"] += 1
                arts_existing = [a for a in staging.get_articles(source=key) if a.url == e.url]
                if arts_existing:
                    arts.append(arts_existing[0])
                    got += 1
                    selected.append({"source": key, "url": e.url, "title": e.title, "score": e.score, "hits": e.hits, "status": "already_staged"})
                continue
            try:
                r = client.get(e.url)
                ex = extract_article(decode_response(r.content, r.charset_encoding), e.url)
            except RobotsDisallowed:
                stats[f"{key}:robots_disallowed"] += 1
                continue
            except FetchError:
                stats[f"{key}:fetch_error"] += 1
                continue
            except ExtractionRejected as ex_err:
                stats[f"{key}:rejected_{str(ex_err).split(':')[0]}"] += 1
                staging.skip(e.url, str(ex_err))
                continue
            status, art = staging.add_article(e.url, key, ex.title or e.title, ex.text, ex.published_at, ex.parser, r.status_code)
            stats[f"{key}:{status}"] += 1
            selected.append({"source": key, "url": e.url, "title": ex.title or e.title, "score": e.score, "hits": e.hits,
                             "status": status, "parser": ex.parser, "chars": len(ex.text)})
            if art is not None:
                arts.append(art)
                got += 1
        stats[f"{key}:selected"] = got
    staging.checkpoint("targeted", sum(v for k, v in stats.items() if k.endswith(":discovered")))
    return stats, selected, arts


def dump_selection(path, selected: list[dict]) -> None:
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in selected), encoding="utf-8")
