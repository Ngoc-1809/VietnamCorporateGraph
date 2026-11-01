"""Phase 6F: HTTP request-start log + per-host spacing check (fake clock; no network)."""
from __future__ import annotations

import json

import httpx
import pytest

from vckg.crawlers.http import PoliteClient, RobotsDisallowed, check_request_spacing


class FakeTime:
    def __init__(self):
        self.t = 100.0

    def clock(self):
        return self.t

    def sleep(self, s):
        self.t += s


def client(tmp_path, handler, delay=2.0, ft=None):
    ft = ft or FakeTime()
    log = tmp_path / "http.jsonl"
    c = PoliteClient("bot", delay, 5.0, 0, 1.0, transport=httpx.MockTransport(handler), sleep=ft.sleep, clock=ft.clock, request_log=log)
    return c, log, ft


def robots_ok(req):
    return httpx.Response(200, text="User-agent: *\nAllow: /\n") if req.url.path == "/robots.txt" else None


def test_every_request_start_is_logged_and_spaced_including_robots(tmp_path):
    def h(req):
        return robots_ok(req) or httpx.Response(200, text="<html>x</html>")
    c, log, _ft = client(tmp_path, h)
    for i in range(3):
        c.get(f"https://a.example/p{i}")
    c.get("https://b.example/p")
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert [r["kind"] for r in rows if r["host"] == "https://a.example"] == ["robots", "page", "page", "page"]  # robots.txt is logged AND throttled too
    assert all(r["required_delay"] >= 2.0 for r in rows)
    res = check_request_spacing(log, 2.0, clock="mono")
    assert res["ok"] and res["hosts"]["a.example"]["min_gap_s"] >= 2.0 and res["total_requests"] == 6


def test_redirect_hops_are_throttled_logged_and_robots_checked(tmp_path):
    def h(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        if req.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        if req.url.path == "/hop":
            return httpx.Response(302, headers={"location": "/private/x"})
        return httpx.Response(200, text="ok")
    c, log, _ft = client(tmp_path, h)
    assert c.get("https://a.example/old").text == "ok"
    kinds = [json.loads(x)["kind"] for x in log.read_text(encoding="utf-8").splitlines()]
    assert kinds == ["robots", "page", "page_redirect"]
    assert check_request_spacing(log, 2.0, clock="mono")["ok"]
    with pytest.raises(RobotsDisallowed):
        c.get("https://a.example/hop")


def test_checker_detects_a_violation_and_honours_robots_crawl_delay(tmp_path):
    log = tmp_path / "x.jsonl"
    rows = [{"started_at": "2026-11-01T10:00:00.000+07:00", "mono": 1.0, "host": "h", "kind": "page", "url": "http://h/u1", "required_delay": 2.0},
            {"started_at": "2026-11-01T10:00:01.000+07:00", "mono": 2.0, "host": "h", "kind": "page", "url": "http://h/u2", "required_delay": 2.0},
            {"started_at": "2026-11-01T10:00:03.000+07:00", "mono": 4.0, "host": "h", "kind": "page", "url": "http://h/u3", "required_delay": 5.0}]
    log.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    r = check_request_spacing(log, 2.0)
    assert not r["ok"] and r["violations"] == 2 and r["hosts"]["h"]["min_gap_s"] == 1.0


def test_crawl_delay_in_robots_is_respected(tmp_path):
    def h(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nCrawl-delay: 7\n")
        return httpx.Response(200, text="ok")
    c, log, _ft = client(tmp_path, h)
    c.get("https://a.example/1")
    c.get("https://a.example/2")
    assert check_request_spacing(log, 2.0, clock="mono")["ok"]
    assert min(json.loads(x)["required_delay"] for x in log.read_text(encoding="utf-8").splitlines() if '"page"' in x) == 7.0


def test_http_to_https_redirect_of_the_same_site_shares_one_rate_budget(tmp_path):
    """Regression (found in Phase 6F): http:// and https:// of one site were throttled as two hosts, so the redirect hop was sent immediately."""
    def h(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if req.url.scheme == "http":
            return httpx.Response(301, headers={"location": str(req.url.copy_with(scheme="https"))})
        return httpx.Response(200, text="ok")
    c, log, _ft = client(tmp_path, h)
    assert c.get("http://www.a.example/x").text == "ok"
    res = check_request_spacing(log, 2.0, clock="mono")
    assert res["ok"] and list(res["hosts"]) == ["a.example"] and res["hosts"]["a.example"]["min_gap_s"] >= 2.0
    assert {"page", "page_redirect"} <= set(res["hosts"]["a.example"]["kinds"])


def test_checker_groups_by_host_name_not_by_scheme(tmp_path):
    log = tmp_path / "x.jsonl"
    rows = [{"started_at": "2026-11-01T10:00:00.000+07:00", "mono": 1.0, "host": "http://s.vn", "kind": "page", "url": "http://s.vn/a", "required_delay": 2.5},
            {"started_at": "2026-11-01T10:00:00.100+07:00", "mono": 1.1, "host": "https://s.vn", "kind": "page_redirect", "url": "https://s.vn/a", "required_delay": 2.5}]
    log.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    r = check_request_spacing(log, 2.0)
    assert not r["ok"] and r["violations"] == 1 and list(r["hosts"]) == ["s.vn"]
