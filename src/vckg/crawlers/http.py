"""Polite HTTP client: robots.txt, per-host rate limit, timeout, retry with exponential backoff."""
from __future__ import annotations

import logging
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger("vckg.crawler")


class RobotsDisallowed(Exception):
    pass


class FetchError(Exception):
    pass


class PoliteClient:
    def __init__(self, user_agent: str, min_delay: float = 2.0, timeout: float = 20.0, max_retries: int = 3,
                 backoff_base: float = 1.5, transport: httpx.BaseTransport | None = None,
                 sleep=time.sleep, clock=time.monotonic):
        self.ua, self.min_delay, self.max_retries, self.backoff = user_agent, min_delay, max_retries, backoff_base
        self.client = httpx.Client(headers={"User-Agent": user_agent, "Accept-Language": "vi,en;q=0.5"},
                                   timeout=timeout, follow_redirects=True, transport=transport)
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last: dict[str, float] = {}
        self._sleep, self._clock = sleep, clock

    def _host(self, url: str) -> str:
        p = urlsplit(url)
        return f"{p.scheme}://{p.netloc}"

    def _throttle(self, host: str, delay: float) -> None:
        wait = self._last.get(host, -1e9) + delay - self._clock()
        if wait > 0:
            self._sleep(wait)
        self._last[host] = self._clock()

    def _robots_for(self, url: str) -> RobotFileParser | None:
        host = self._host(url)
        if host not in self._robots:
            rp = RobotFileParser()
            try:
                r = self.client.get(f"{host}/robots.txt")
                if r.status_code == 200:
                    rp.parse(r.text.lstrip("\ufeff").replace("\ufeff", "").splitlines())  # some sites serve a BOM
                elif r.status_code in (401, 403):
                    rp.disallow_all = True
                else:  # 404 etc: no restrictions published
                    rp.allow_all = True
            except httpx.HTTPError:
                rp = None  # unknown -> be conservative: refuse
            self._robots[host] = rp
        return self._robots[host]

    def crawl_delay(self, url: str) -> float:
        rp = self._robots_for(url)
        d = rp.crawl_delay(self.ua) if rp else None
        return max(self.min_delay, float(d)) if d else self.min_delay

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        return bool(rp and rp.can_fetch(self.ua, url))

    def get(self, url: str) -> httpx.Response:
        if not self.allowed(url):
            raise RobotsDisallowed(url)
        host, delay = self._host(url), self.crawl_delay(url)
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._throttle(host, delay)
            try:
                r = self.client.get(url)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise FetchError(f"HTTP {r.status_code}")
                if r.status_code in (401, 402, 403, 451):  # login/paywall/blocked: never circumvent
                    raise FetchError(f"access restricted HTTP {r.status_code}")
                r.raise_for_status()
                return r
            except (httpx.HTTPError, FetchError) as e:
                last_err = e
                if isinstance(e, FetchError) and "restricted" in str(e):
                    break
                wait = self.backoff ** attempt
                log.warning("fetch_retry url=%s attempt=%d err=%s wait=%.1fs", url, attempt + 1, e, wait)
                self._sleep(wait)
        raise FetchError(f"{url}: {last_err}")

    def close(self) -> None:
        self.client.close()
