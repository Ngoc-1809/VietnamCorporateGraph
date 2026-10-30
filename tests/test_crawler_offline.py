"""Crawler unit tests using httpx.MockTransport (transport-level fixture, no network)."""
import httpx
import pytest

from vckg.crawlers.extract import ExtractionRejected, extract_article
from vckg.crawlers.http import FetchError, PoliteClient, RobotsDisallowed

BODY = "".join(f"<p>Đoạn {i}: Ngân hàng công bố kết quả kinh doanh quý với lợi nhuận tăng trưởng đáng kể so với cùng kỳ.</p>" for i in range(12))
HTML = f"<html><head><title>Tin</title></head><body><article>{BODY}</article></body></html>"


def make_client(handler, **kw):
    sleeps = []
    c = PoliteClient("test-bot", min_delay=0.0, transport=httpx.MockTransport(handler), sleep=sleeps.append, **kw)
    return c, sleeps


def test_robots_disallow_blocks():
    def h(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        return httpx.Response(200, text="ok")
    c, _ = make_client(h)
    assert c.get("https://x.test/public").text == "ok"
    with pytest.raises(RobotsDisallowed):
        c.get("https://x.test/private/a")


def test_robots_unreachable_is_conservative():
    def h(req):
        raise httpx.ConnectError("down")
    c, _ = make_client(h)
    assert c.allowed("https://x.test/a") is False


def test_retry_with_backoff_then_success():
    calls = {"n": 0}

    def h(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else httpx.Response(200, text="fine")
    c, sleeps = make_client(h)
    assert c.get("https://x.test/a").text == "fine"
    assert calls["n"] == 3 and sleeps[-2:] == [1.0, 1.5]  # exponential: base**attempt


def test_paywall_not_retried_or_bypassed():
    calls = {"n": 0}

    def h(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        return httpx.Response(403)
    c, _ = make_client(h)
    with pytest.raises(FetchError):
        c.get("https://x.test/a")
    assert calls["n"] == 1


def test_extract_ok_and_short_rejected():
    ex = extract_article(HTML, "https://x.test/a")
    assert len(ex.text) > 400 and ex.parser in ("trafilatura", "bs4")
    with pytest.raises(ExtractionRejected):
        extract_article("<html><body><article><p>Quá ngắn.</p></article></body></html>")


def test_encoding_error_rejected():
    bad = HTML.replace("Ngân", "\ufffd\ufffd\ufffd" * 30)
    with pytest.raises(ExtractionRejected):
        extract_article(bad)
