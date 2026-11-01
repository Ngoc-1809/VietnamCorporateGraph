"""Polite HTTP client: robots.txt, per-host rate limit, timeout, retry with exponential backoff."""
from __future__ import annotations

import itertools
import json
import logging
import time
from datetime import datetime
from pathlib import Path
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
                 sleep=time.sleep, clock=time.monotonic, request_log: str | Path | None = None, max_redirects: int = 5):
        self.ua, self.min_delay, self.max_retries, self.backoff = user_agent, min_delay, max_retries, backoff_base
        # redirects are followed MANUALLY (below) so that every hop is robots-checked, throttled per host and logged
        self.client = httpx.Client(headers={"User-Agent": user_agent, "Accept-Language": "vi,en;q=0.5"},
                                   timeout=timeout, follow_redirects=False, transport=transport)
        self.request_log, self.max_redirects = Path(request_log) if request_log else None, max_redirects
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last: dict[str, float] = {}
        self._sleep, self._clock = sleep, clock

    def _host(self, url: str) -> str:
        p = urlsplit(url)
        return f"{p.scheme}://{p.netloc}"

    @staticmethod
    def throttle_key(url: str) -> str:
        """Rate limits apply per HOST NAME (http:// and https:// of the same site share one budget; a leading 'www.' is ignored)."""
        n = urlsplit(url).netloc.lower()
        return n.removeprefix("www.")

    def _throttle(self, host: str, delay: float) -> None:
        wait = self._last.get(host, -1e9) + delay - self._clock()
        if wait > 0:
            self._sleep(wait)
        self._last[host] = self._clock()

    def _log(self, kind: str, url: str, required_delay: float, status: int | None = None) -> None:
        """One line per HTTP request, written at the moment the request STARTS (wall + monotonic clock)."""
        if self.request_log is None:
            return
        self.request_log.parent.mkdir(parents=True, exist_ok=True)
        with self.request_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"started_at": datetime.now().astimezone().isoformat(timespec="milliseconds"), "mono": round(self._clock(), 3), "host": self._host(url),
                                "kind": kind, "url": url, "required_delay": required_delay}, ensure_ascii=False) + "\n")

    def _request(self, url: str, kind: str, delay: float) -> httpx.Response:
        """One logical request = initial request + redirect hops; every hop is throttled (same host spacing) and logged. Cross-host hops are re-checked against robots."""
        for hop in range(self.max_redirects + 1):
            d = delay if hop == 0 else self.crawl_delay(url) if kind != "robots" else delay
            self._throttle(self.throttle_key(url), d)
            self._log(kind if hop == 0 else f"{kind}_redirect", url, d)
            r = self.client.get(url)
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                nxt = str(httpx.URL(url).join(r.headers["location"]))
                if kind != "robots" and not self.allowed(nxt):
                    raise RobotsDisallowed(nxt)
                url = nxt
                continue
            return r
        raise FetchError(f"too many redirects: {url}")

    def _robots_for(self, url: str) -> RobotFileParser | None:
        host = self._host(url)
        if host not in self._robots:
            rp = RobotFileParser()
            try:
                r = self._request(f"{host}/robots.txt", "robots", self.min_delay)
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
        delay = self.crawl_delay(url)
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                r = self._request(url, "page", delay)
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


def check_request_spacing(path: str | Path, min_gap: float = 2.0, tolerance: float = 0.02, clock: str = "wall") -> dict:
    """Verify per-host spacing of request START times from a `request_log`. Required gap = max(min_gap, the crawl-delay in force for that request).
    clock='wall' (ISO timestamps, valid across process restarts) or 'mono' (fake-clock tests)."""
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()] if Path(path).exists() else []
    by: dict[str, list[tuple[float, float, str, str]]] = {}
    for r in rows:
        t = datetime.fromisoformat(r["started_at"]).timestamp() if clock == "wall" else float(r["mono"])
        by.setdefault(PoliteClient.throttle_key(r["url"]), []).append((t, float(r.get("required_delay", min_gap)), r["kind"], r["url"]))  # grouped by host NAME, not by scheme+host
    out = {}
    for host, lst in by.items():
        lst.sort()
        gaps, bad = [], []
        for (t0, _d0, _k0, _u0), (t1, d1, k1, u1) in itertools.pairwise(lst):
            g = t1 - t0
            gaps.append(g)
            if g + tolerance < max(min_gap, d1):
                bad.append({"gap": round(g, 3), "required": max(min_gap, d1), "kind": k1, "url": u1})
        out[host] = {"requests": len(lst), "min_gap_s": round(min(gaps), 3) if gaps else None, "violations": bad, "kinds": sorted({k for _t, _d, k, _u in lst})}
    return {"hosts": out, "total_requests": len(rows), "violations": sum(len(h["violations"]) for h in out.values()), "ok": all(not h["violations"] for h in out.values())}
