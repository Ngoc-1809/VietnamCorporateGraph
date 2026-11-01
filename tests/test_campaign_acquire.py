"""Mass campaign: queue, discovery and acquisition (offline; MockTransport behind the real PoliteClient). Proves bookkeeping, limits, dedup, compliance and failure
isolation, not extraction quality."""
from __future__ import annotations

import json

import httpx
import pytest

from vckg.campaign import acquire as acq
from vckg.campaign import discover as dsc
from vckg.campaign.queue import Queue, RawPages
from vckg.crawlers.http import PoliteClient
from vckg.storage.sqlite import Staging, canonicalize_url

BODY = "Ông Nguyễn Văn An là Chủ tịch Hội đồng quản trị Công ty cổ phần Đầu tư Hoa Sen và đã bổ nhiệm Tổng giám đốc mới. " * 4


def page(i: int) -> bytes:
    paras = "".join(f"<p>{BODY} Bài số {i} đoạn {k} chứa thông tin riêng biệt của bài viết {i}.</p>" for k in range(4))
    return f"<html><head><title>Bài {i}</title></head><body><article>{paras}</article></body></html>".encode()


def vs_url(i: int, slug: str = "bo-nhiem-tong-giam-doc") -> str:
    return f"https://vietstock.vn/2026/10/{slug}-{i}-15{i:05d}.htm"


def cf_url(i: int, slug: str = "mua-lai-co-phan-cong-ty-con") -> str:
    return f"https://cafef.vn/{slug}-18826{i + 500:09d}.chn"


def make_client(hits: list, mode: dict | None = None, delay: float = 0.0):
    mode = mode or {}

    def h(req: httpx.Request) -> httpx.Response:
        hits.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /blocked/\n")
        u = str(req.url)
        if "/blocked/" in u:
            return httpx.Response(200, content=page(1))
        m = [x for k, x in mode.items() if k in u]
        if m and m[0] == "503":
            return httpx.Response(503)
        if m and m[0] == "short":
            return httpx.Response(200, content="<html><body><article><p>quá ngắn</p></article></body></html>".encode())
        if m and m[0].startswith("same:"):
            return httpx.Response(200, content=page(int(m[0][5:])))
        i = int("".join(ch for ch in req.url.path.split("-")[-1] if ch.isdigit())[-4:] or 0)
        return httpx.Response(200, content=page(i), headers={"content-type": "text/html; charset=utf-8"})
    return PoliteClient("bot", delay, 5.0, 0, 1.0, transport=httpx.MockTransport(h), sleep=lambda s: None)


def seed(q: Queue, rows: list[tuple[str, str, float]]):
    q.add_discovered([{"url": canonicalize_url(u), "source": s, "slug": "x", "score": sc, "topic": "board", "via": "test"} for u, s, sc in rows])


@pytest.fixture
def env(tmp_path):
    Staging(tmp_path / "staging.sqlite").add_article("https://vietstock.vn/2026/10/cu-1-1.htm", "vietstock", "cũ", "văn bản cũ khác " * 60, None)
    return tmp_path


COMP = {"cafef": {"cleared": True}, "vietstock": {"cleared": True}, "vneconomy": {"cleared": False}, "baodautu": {"cleared": False}}


def acquirer(env, max_new, hits=None, mode=None, sources=None, **kw):
    hits = hits if hits is not None else []
    a = acq.Acquirer(env / "camp", max_new=max_new, staging_db=env / "staging.sqlite", compliance=COMP, sources=sources, client_factory=lambda s: make_client(hits, mode),
                     ident=None, low_water=0, idle_sleep=0.1, install_signals=False, poll=0.1, **kw)
    a.hits = hits
    return a


def test_queue_dedup_known_urls_and_statuses_are_separate(tmp_path):
    q = Queue(tmp_path / "q.sqlite")
    rows = [{"url": "https://a/x", "source": "cafef", "score": 5.0}, {"url": "https://a/y", "source": "cafef", "score": 9.0}]
    assert q.add_discovered(rows, known_urls={"https://a/x"}) == (1, 1)
    assert q.add_discovered(rows) == (1, 1)  # y already queued; x is now new
    r = q.next_to_crawl("cafef", 1.0)
    assert r["url"] == "https://a/y"  # highest score first
    q.mark_crawl("https://a/y", "fetched", http_status=200)
    q.mark_parse("https://a/y", "ok", article_id="art1", content_hash="h", chars=10)
    row = q.db.execute("SELECT crawl_status, parse_status, nlp_status FROM urls WHERE url='https://a/y'").fetchone()
    assert tuple(row) == ("fetched", "ok", "pending")
    q.mark_crawl("https://a/x", "fetched", http_status=200)
    q.mark_parse("https://a/x", "rejected_too_short")
    assert q.db.execute("SELECT nlp_status FROM urls WHERE url='https://a/x'").fetchone()[0] is None  # a rejected page never reaches NLP
    assert q.acquired_new() == 1 and q.counts()["nlp"] == {"pending": 1}
    ids = q.take_chunk("camp-c00001", 10)
    assert [r["article_id"] for r in ids] == ["art1"] and q.open_chunk() == "camp-c00001" and q.pending_nlp() == 0


def test_raw_pages_roundtrip_and_never_overwritten(tmp_path):
    r = RawPages(tmp_path / "raw.sqlite")
    r.put("u", b"<html>one</html>" * 100, 200, "utf-8")
    r.put("u", b"changed", 200, "utf-8")
    assert r.get("u") == b"<html>one</html>" * 100


def test_sitemap_parsing_archive_order_and_article_filters():
    xml = "<urlset><url><loc>https://vietstock.vn/2026/10/a-b-1-15.htm</loc><lastmod>2026-10-01</lastmod></url><url><loc>https://vietstock.vn/chu-de/1-2/x.htm</loc></url></urlset>"
    urls = dsc.parse_sitemap_urls(xml)
    assert urls[0] == ("https://vietstock.vn/2026/10/a-b-1-15.htm", "2026-10-01")
    assert dsc.ARTICLE_RX["vietstock"].match(urls[0][0]) and not dsc.ARTICLE_RX["vietstock"].match(urls[1][0])
    assert dsc.ARTICLE_RX["cafef"].match("https://cafef.vn/x-y-188261029094024802.chn") and not dsc.ARTICLE_RX["cafef"].match("https://cafef.vn/thi-truong.chn")
    names = [f"https://cafef.vn/sitemaps/sitemaps-2026-{m}-{d}.xml" for m, d in ((9, "1-5"), (10, "26-31"), (10, "1-5"), (9, "21-25"))]
    assert [dsc.archive_key(u)[1:] for u in sorted(names, key=dsc.archive_key, reverse=True)] == [(10, 26), (10, 1), (9, 21), (9, 1)]  # numeric, newest first (not lexicographic)


def test_discovery_scores_slugs_skips_staged_and_applies_floor(env):
    q = Queue(env / "q.sqlite")
    sm = ("<urlset>" + "".join(f"<url><loc>{u}</loc></url>" for u in [vs_url(2), vs_url(3, "thoi-tiet-ha-noi"), "https://vietstock.vn/2026/10/cu-1-1.htm"]) + "</urlset>")

    class C:
        def get(self, url):
            return type("R", (), {"content": sm.encode()})()
    d = dsc.Discovery(q, lambda s: C(), env / "staging.sqlite", env / "sm", None, insert_floor=1.0, low_water=0)
    res = d.tick("vietstock", 1.0)
    rows = {r["url"]: r for r in q.db.execute("SELECT * FROM urls")}
    assert res["new"] == 1 and len(rows) == 1 and next(iter(rows.values()))["score"] >= 4 and next(iter(rows.values()))["topic"] != "none"
    assert q.db.execute("SELECT status FROM sitemaps WHERE kind='full'").fetchone()[0] == "done"
    assert d.tick("vietstock", 1.0)["new"] == 0  # a finished sitemap is not fetched again within 24 h


def test_acquirer_hard_cap_exact_and_two_publishers_in_parallel(env):
    q = Queue(env / "camp" / "queue.sqlite")
    seed(q, [(vs_url(i), "vietstock", 10 - i * 0.1) for i in range(1, 8)] + [(cf_url(i), "cafef", 9 - i * 0.1) for i in range(1, 8)])
    q.close()
    a = acquirer(env, 5)
    assert a.run() == 0
    q = Queue(env / "camp" / "queue.sqlite")
    assert q.acquired_new() == 5  # never more than the cap (in-flight requests are reserved)
    st = json.loads((env / "camp" / "acquire_status.json").read_text(encoding="utf-8"))
    assert st["state"] == "COMPLETED" and st["acquired_new"] == 5 and st["shortfall"] == 0
    assert sum(1 for h in a.hits if h.endswith((".htm", ".chn"))) <= 6
    assert Staging(env / "staging.sqlite").count_articles() == 6  # 1 old + 5 new
    assert RawPages(env / "camp" / "raw_pages.sqlite").db.execute("SELECT COUNT(*) FROM pages").fetchone()[0] >= 5


def test_rerun_never_recrawls_completed_urls(env):
    q = Queue(env / "camp" / "queue.sqlite")
    seed(q, [(vs_url(i), "vietstock", 9) for i in range(1, 4)])
    q.close()
    acquirer(env, 3, sources=["vietstock"]).run()
    a2 = acquirer(env, 3, sources=["vietstock"])
    a2.run()
    assert not [h for h in a2.hits if h.endswith(".htm")]
    assert Staging(env / "staging.sqlite").count_articles() == 4


def test_failures_are_isolated_tracked_separately_and_shortfall_is_reported(env):
    q = Queue(env / "camp" / "queue.sqlite")
    seed(q, [(vs_url(1), "vietstock", 9), (vs_url(2, "short-page"), "vietstock", 8.9), (vs_url(3, "fail-503"), "vietstock", 8.8), (vs_url(4, "dup"), "vietstock", 8.7),
             ("https://vietstock.vn/blocked/x-5-1500005.htm", "vietstock", 8.6), (vs_url(6), "vietstock", 8.5)])
    q.close()
    a = acquirer(env, 100, mode={"short-page": "short", "fail-503": "503", "dup": "same:1"}, sources=["vietstock"])
    assert a.run() == 0
    q = Queue(env / "camp" / "queue.sqlite")
    st = {r["url"].rsplit("/", 1)[-1]: (r["crawl_status"], r["parse_status"], r["crawl_attempts"]) for r in q.db.execute("SELECT * FROM urls")}
    assert st[vs_url(1).rsplit("/", 1)[-1]][:2] == ("fetched", "ok")
    assert st[vs_url(2, "short-page").rsplit("/", 1)[-1]][:2] == ("fetched", "rejected_too_short")
    assert st[vs_url(3, "fail-503").rsplit("/", 1)[-1]][0] == "pending"  # retry scheduled with backoff, not lost
    assert st[vs_url(4, "dup").rsplit("/", 1)[-1]][:2] == ("fetched", "duplicate_content")
    assert st["x-5-1500005.htm"][0] == "robots_disallowed"
    assert q.acquired_new() == 2
    s = json.loads((env / "camp" / "acquire_status.json").read_text(encoding="utf-8"))
    assert s["state"] == "COMPLETED" and s["shortfall"] == 98 and s["counters"]["robots"] == 1 and s["counters"]["rejected"] == 1 and s["counters"]["duplicates"] == 1


def test_uncleared_publishers_and_bad_limits_are_refused(env):
    with pytest.raises(SystemExit):
        acq.Acquirer(env / "c", max_new=5, compliance=COMP, sources=["vneconomy", "baodautu"], staging_db=env / "staging.sqlite")
    for kw in ({"max_new": 30001}, {"max_new": 0}, {"min_delay": 1.0}):
        with pytest.raises(SystemExit):
            acq.Acquirer(env / "c", compliance=COMP, staging_db=env / "staging.sqlite", **{"max_new": 5, **kw})
    a = acq.Acquirer(env / "c", max_new=5, compliance=COMP, sources=["cafef", "vneconomy"], staging_db=env / "staging.sqlite")
    assert a.sources == ["cafef"]


def test_stop_file_stops_acquisition_and_keeps_queue(env):
    q = Queue(env / "camp" / "queue.sqlite")
    seed(q, [(vs_url(i), "vietstock", 9) for i in range(1, 6)])
    q.close()
    (env / "camp").mkdir(exist_ok=True)
    a = acquirer(env, 5, sources=["vietstock"])
    orig = a._fetch
    n = []

    def fetch_then_stop(*args, **kw):
        orig(*args, **kw)
        n.append(1)
        if len(n) == 2:
            (env / "camp" / "STOP").write_text("x")
    a._fetch = fetch_then_stop
    assert a.run() == 0
    st = json.loads((env / "camp" / "acquire_status.json").read_text(encoding="utf-8"))
    q = Queue(env / "camp" / "queue.sqlite")
    assert st["state"] == "STOPPED" and q.acquired_new() == 2 and q.pool("vietstock", 0) == 3


def test_http_spacing_audit_failure_halts_acquisition(env):
    q = Queue(env / "camp" / "queue.sqlite")
    seed(q, [(vs_url(i), "vietstock", 9) for i in range(1, 6)])
    q.close()
    (env / "camp").mkdir(exist_ok=True)
    bad = [{"started_at": f"2026-11-01T10:00:00.{i:03d}+07:00", "mono": 1.0, "host": "https://vietstock.vn", "kind": "page", "url": f"https://vietstock.vn/{i}", "required_delay": 2.5} for i in range(3)]
    (env / "camp" / "http_vietstock.jsonl").write_text("\n".join(json.dumps(r) for r in bad), encoding="utf-8")
    a = acquirer(env, 5, sources=["vietstock"], audit_every=1)
    assert a.run() == 4
    st = json.loads((env / "camp" / "acquire_status.json").read_text(encoding="utf-8"))
    assert st["state"] == "FAILED" and st["http_spacing_ok"] is False
