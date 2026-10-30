"""Phase 5 / Task D: topic-targeted article discovery + ranking + controlled (targeted + random control) selection.

Ranking only decides WHICH articles to download and process; it is never evidence for an edge. Discovery uses public RSS
feeds / category pages through PoliteClient (robots.txt, rate limit, backoff). Titles/summaries are folded (accent-free)
before keyword matching. Near-duplicate titles (token Jaccard) form duplicate groups to avoid train/eval leakage."""
from __future__ import annotations

import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from vckg.crawlers.extract import ExtractionRejected, decode_response, extract_article
from vckg.crawlers.http import FetchError, PoliteClient, RobotsDisallowed
from vckg.crawlers.targeted import Entry, discover
from vckg.entity_linking.normalize import fold
from vckg.storage.sqlite import Staging

TOPICS: dict[str, dict[str, int]] = {
    "appointment": {"bo nhiem": 4, "mien nhiem": 4, "thoi giu chuc": 4, "tu nhiem": 4, "nhan su": 2, "tan chu tich": 4,
                    "tan tong giam doc": 4, "tro lai ghe": 3, "bau bo sung": 3, "len lam": 2, "nghi huu": 1, "ban lanh dao": 2},
    "board": {"hdqt": 3, "hoi dong quan tri": 3, "hdtv": 3, "ban dieu hanh": 3, "tong giam doc": 2, "chu tich": 2, "dai hoi dong co dong": 2,
              "thanh vien doc lap": 3, "ban kiem soat": 2},
    "shareholding": {"co dong lon": 4, "so huu": 2, "nam giu": 2, "thoai von": 3, "ty le so huu": 3, "giao dich noi bo": 3,
                     "mua vao co phieu": 2, "ban ra co phieu": 2, "dang ky mua": 2, "dang ky ban": 2, "nguoi lien quan": 3},
    "subsidiary": {"cong ty con": 4, "cong ty me": 4, "cong ty lien ket": 3, "truc thuoc": 3, "cong ty thanh vien": 3, "gop von thanh lap": 3,
                   "nang ty le so huu": 3},
    "mna": {"mua lai": 4, "thau tom": 4, "sap nhap": 4, "chuyen nhuong": 3, "m&a": 3, "thuong vu": 3, "chao mua": 3, "nhan chuyen nhuong": 4},
    "credit": {"cap tin dung": 4, "hop dong tin dung": 4, "cho vay": 2, "khoan vay": 2, "hop von": 3, "han muc tin dung": 3, "tai tro von": 3,
               "giai ngan": 2},
    "bond": {"phat hanh trai phieu": 4, "trai phieu": 2, "lo trai phieu": 3, "huy dong trai phieu": 3, "chao ban trai phieu": 4,
             "tpdn": 2, "mua lai trai phieu": 3},
    "jv_partnership": {"lien doanh": 4, "hop tac chien luoc": 4, "bat tay": 3, "ky ket hop tac": 3, "thoa thuan hop tac": 3, "doi tac chien luoc": 3,
                       "bien ban ghi nho": 3},
    "sanction": {"xu phat": 4, "bi phat": 3, "phat hanh chinh": 4, "vi pham": 1, "cong bo thong tin cham": 3, "dinh chi giao dich": 3,
                 "ubck": 2},
    "prosecution": {"khoi to": 4, "truy to": 4, "bat tam giam": 4, "bi can": 3, "dieu tra": 2, "vu an": 2, "cong an": 1, "bat giam": 3},
}
FEED_HINT = {"tang-von-m-a": "mna", "trai-phieu-doanh-nghiep": "bond", "thi-truong-trai-phieu": "bond", "giao-dich-noi-bo": "shareholding",
             "nhan-vat": "appointment", "ngan-hang": "credit", "ngan-hang--bao-hiem": "credit"}
_ORG_HINT = re.compile(r"\b(?:ctcp|tap doan|ngan hang|tong cong ty|cong ty|hose|hnx|upcom)\b|\b[a-z]{3}\b\s*(?::|\))")
_STOP = {"cua", "va", "la", "cho", "voi", "nhung", "cac", "mot", "trong", "duoc", "tai", "ve", "den", "tu", "se", "da", "co"}


def _tokens(title: str) -> frozenset[str]:
    return frozenset(t for t in fold(title).split() if t not in _STOP and len(t) > 1)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


@dataclass
class Ranked:
    url: str
    source: str
    title: str
    summary: str
    feed: str = ""
    published: str | None = None
    topic: str = "none"
    topic_scores: dict[str, int] = field(default_factory=dict)
    score: float = 0.0
    hits: list[str] = field(default_factory=list)
    n_org_hints: int = 0
    dup_group: int = -1


def score_entry(e: Entry, feed: str = "") -> Ranked:
    title_f, rest_f = fold(e.title), fold(f"{e.summary} {e.url}")
    scores: dict[str, int] = {}
    hits: list[str] = []
    for topic, kws in TOPICS.items():
        sc = 0
        for kw, w in kws.items():
            if kw in title_f:
                sc += 2 * w
                hits.append(f"{topic}:{kw}(title)")
            elif kw in rest_f:
                sc += w
                hits.append(f"{topic}:{kw}")
        if sc:
            scores[topic] = sc
    hint = next((v for k, v in FEED_HINT.items() if k in feed), None)
    if hint:
        scores[hint] = scores.get(hint, 0) + 2
    best = max(scores, key=scores.get) if scores else "none"
    n_org = len(_ORG_HINT.findall(f"{title_f} {rest_f}"))
    total = scores.get(best, 0) + 0.5 * min(n_org, 4)
    return Ranked(url=e.url, source=e.source, title=e.title, summary=e.summary[:300], feed=feed, topic=best, topic_scores=scores,
                  score=round(total, 2), hits=hits[:8], n_org_hints=n_org)


def group_duplicates(items: list[Ranked], known_titles: list[frozenset[str]], thr: float = 0.75) -> None:
    """Assign dup_group ids (items near-identical in title share a group); group -2 = duplicate of an already staged article."""
    reps: list[frozenset[str]] = []
    for it in items:
        t = _tokens(it.title)
        if any(jaccard(t, k) >= thr for k in known_titles):
            it.dup_group = -2
            continue
        for gi, r in enumerate(reps):
            if jaccard(t, r) >= thr:
                it.dup_group = gi
                break
        else:
            reps.append(t)
            it.dup_group = len(reps) - 1


def select(items: list[Ranked], n: int = 200, targeted_share: float = 0.75, min_score: float = 4.0, seed: int = 20261030,
           per_source_cap: float = 0.45) -> list[dict]:
    """Targeted: top-score per topic, topic round-robin, source cap. Control: seeded random from the REST of the pool
    (not score-filtered), source-proportional, never in a duplicate group of a targeted pick."""
    rng = random.Random(seed)
    usable = [i for i in items if i.dup_group != -2]
    t_n = round(n * targeted_share)
    by_topic: dict[str, list[Ranked]] = defaultdict(list)
    for i in sorted(usable, key=lambda x: (-x.score, x.url)):
        if i.topic != "none" and i.score >= min_score:
            by_topic[i.topic].append(i)
    chosen: list[Ranked] = []
    used_groups: set[int] = set()
    src_count: Counter = Counter()
    cap = max(1, math.ceil(t_n * per_source_cap))
    while len(chosen) < t_n and any(by_topic.values()):
        progressed = False
        for topic in sorted(by_topic):
            q = by_topic[topic]
            while q:
                it = q.pop(0)
                if it.dup_group in used_groups or src_count[it.source] >= cap:
                    continue
                chosen.append(it)
                used_groups.add(it.dup_group)
                src_count[it.source] += 1
                progressed = True
                break
            if len(chosen) >= t_n:
                break
        if not progressed:
            break
    rest = [i for i in usable if i not in chosen and i.dup_group not in used_groups]
    rng.shuffle(rest)
    c_n = n - len(chosen) if len(chosen) < t_n else n - t_n
    by_src: dict[str, list[Ranked]] = defaultdict(list)
    for i in rest:
        by_src[i.source].append(i)
    control: list[Ranked] = []
    srcs = sorted(by_src)
    while len(control) < c_n and any(by_src.values()):
        for s in srcs:
            if by_src[s] and len(control) < c_n:
                it = by_src[s].pop(0)
                if it.dup_group in used_groups:
                    continue
                used_groups.add(it.dup_group)
                control.append(it)
    out = []
    for subset, lst in (("targeted", chosen), ("control", control)):
        for it in lst:
            reason = ", ".join(it.hits[:4]) if subset == "targeted" else "random control (seeded, not score-filtered)"
            out.append({"subset": subset, "source": it.source, "url": it.url, "title": it.title, "feed": it.feed, "published": it.published,
                        "topic": it.topic, "selection_score": it.score, "selection_reason": reason, "dup_group": it.dup_group,
                        "topic_scores": it.topic_scores})
    return out


def run_discovery(client: PoliteClient, staging: Staging, sources: dict, n: int, seed: int, only: list[str] | None = None,
                  min_score: float = 4.0) -> tuple[list[dict], dict]:
    pool: list[Ranked] = []
    staged_urls = {a.url for a in staging.get_articles()}
    staged_titles = [_tokens(a.title) for a in staging.get_articles() if a.title]
    discovered = Counter()
    for key, cfg in sources.items():
        if only and key not in only:
            continue
        feeds = [(f, f) for f in cfg.get("feeds", [])]
        for f, tag in feeds:
            try:
                entries = discover(client, key, {"feeds": [f]})
            except Exception:  # noqa: BLE001, S112 - one failing feed must not stop discovery
                continue
            for e in entries:
                if e.url in staged_urls or staging.url_seen(e.url) or staging.is_skipped(e.url):
                    continue
                r = score_entry(e, tag)
                pool.append(r)
        for p in cfg.get("category_pages", []):
            try:
                for e in discover(client, key, {"category_pages": [p]}):
                    if e.url not in staged_urls and not staging.url_seen(e.url) and not staging.is_skipped(e.url):
                        pool.append(score_entry(e, p))
            except Exception:  # noqa: BLE001, S112 - one failing feed must not stop discovery
                continue
    uniq: dict[str, Ranked] = {}
    for r in pool:
        old = uniq.get(r.url)
        if old is None or r.score > old.score:
            uniq[r.url] = r
    items = list(uniq.values())
    for it in items:
        discovered[it.source] += 1
    group_duplicates(items, staged_titles)
    sel = select(items, n=n, seed=seed, min_score=min_score)
    stats = {"pool_new_unique": len(items), "pool_by_source": dict(discovered), "dup_of_staged": sum(1 for i in items if i.dup_group == -2),
             "topic_pool": dict(Counter(i.topic for i in items)), "selected": len(sel)}
    return sel, stats


def fetch_selected(client: PoliteClient, staging: Staging, selection: list[dict]) -> tuple[list[dict], Counter]:
    """Download + extract + stage. Updates each manifest row with status/article_id/chars/parser. Robots/paywall respected."""
    stats: Counter = Counter()
    seen_hash: dict[str, str] = {}
    for row in selection:
        url = row["url"]
        try:
            r = client.get(url)
            ex = extract_article(decode_response(r.content, r.charset_encoding), url)
        except RobotsDisallowed:
            row["status"] = "robots_disallowed"
        except FetchError:
            row["status"] = "fetch_error"
        except ExtractionRejected as err:
            row["status"] = "rejected_" + str(err).split(":")[0]
            staging.skip(url, str(err))
        else:
            status, art = staging.add_article(url, row["source"], ex.title or row["title"], ex.text, ex.published_at or row.get("published"),
                                              ex.parser, r.status_code)
            row.update(status=status, parser=ex.parser, chars=len(ex.text), date=ex.published_at or row.get("published"))
            if art is not None:
                row["article_id"] = art.article_id
                row["content_hash"] = art.content_hash
                seen_hash[art.content_hash] = art.article_id
        stats[f"{row['subset']}:{row['status']}"] += 1
    return selection, stats


def dump(path: str | Path, rows: list[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


__all__ = ["TOPICS", "Ranked", "asdict", "dump", "fetch_selected", "group_duplicates", "jaccard", "run_discovery", "score_entry", "select"]
