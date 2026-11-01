"""Mass-campaign acquisition worker: crawl the durable queue (one thread per cleared publisher, each with its own PoliteClient => >= 2 s per HOST, robots.txt, backoff).

  python -m vckg.campaign.acquire run [--campaign-dir data/campaign/mass] [--max-new 30000] [--min-score 1.0] [--min-delay 2.5]

Per URL: raw HTML -> raw_pages.sqlite (zlib), extracted article -> staging.sqlite (dedup by canonical URL + content hash; existing rows never touched), statuses -> queue.sqlite
(crawl / parse tracked separately). Stops when `max_new` NEW articles are stored (hard cap, in-flight requests reserved), when no accessible candidates remain (reported as a
shortfall, never padded), on STOP, or when the HTTP-spacing audit fails. Only sources cleared in config/crawl_compliance.yaml are crawled. Resume = rerun (state is in SQLite)."""
from __future__ import annotations

import argparse
import json
import signal
import sqlite3
import sys
import threading
import time
from pathlib import Path

from vckg.campaign.discover import Discovery
from vckg.campaign.queue import Queue, RawPages, retry_locked
from vckg.crawlers.extract import ExtractionRejected, decode_response, extract_article
from vckg.crawlers.http import FetchError, PoliteClient, RobotsDisallowed, check_request_spacing
from vckg.jobs.pipeline_worker import LockHeld, Status, job_lock, now
from vckg.jobs.selection import IdentityIndex, cleared_sources, load_compliance
from vckg.storage.sqlite import Staging

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_DIR = ROOT / "data/campaign/mass"
STAGING_DB = ROOT / "data/staging/staging.sqlite"
REGISTRY = ROOT / "data/registry/registry_p5_new.sqlite"
COMPLIANCE_FILE = ROOT / "config/crawl_compliance.yaml"
MAX_NEW_CEILING = 30_000


class Acquirer:
    def __init__(self, campaign_dir: Path = CAMPAIGN_DIR, *, max_new: int = MAX_NEW_CEILING, min_score: float = 1.0, min_delay: float = 2.5, staging_db: Path = STAGING_DB,
                 compliance: dict | None = None, sources: list[str] | None = None, client_factory=None, ident: IdentityIndex | None | str = "auto", low_water: int = 1500,
                 feeds: dict | None = None, category_pages: dict | None = None, audit_every: int = 100, idle_sleep: float = 30.0, install_signals: bool = True, poll: float = 5.0):
        if not 0 < max_new <= MAX_NEW_CEILING:
            raise SystemExit(f"max-new must be in 1..{MAX_NEW_CEILING}")
        if min_delay < 2.0:
            raise SystemExit("min-delay must be >= 2.0 s per host")
        self.dir = Path(campaign_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.max_new, self.min_score, self.min_delay, self.staging_db = max_new, min_score, min_delay, Path(staging_db)
        self.compliance = compliance if compliance is not None else load_compliance(COMPLIANCE_FILE)
        self.sources = cleared_sources(self.compliance, sources)
        if not self.sources:
            raise SystemExit("no cleared source (config/crawl_compliance.yaml)")
        self.client_factory, self.low_water, self.audit_every, self.idle_sleep = client_factory, low_water, audit_every, idle_sleep
        self.feeds, self.cats = feeds or {}, category_pages or {}
        self.ident = ident
        self.queue_path, self.raw_path = self.dir / "queue.sqlite", self.dir / "raw_pages.sqlite"
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.inflight = 0
        self.counters = {"fetched": 0, "stored_new": 0, "failed": 0, "robots": 0, "rejected": 0, "duplicates": 0, "retries": 0}
        self.exhausted: set[str] = set()
        self.errors: list[str] = []
        self.status: Status | None = None
        self.spacing_ok: bool | None = None
        self.install_signals = install_signals
        self.poll = poll
        self.started_wall = time.time()

    # ------------------------------------------------------------------ helpers
    def _event(self, **kw) -> None:
        with self.lock, (self.dir / "acquire_events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), **kw}, ensure_ascii=False) + "\n")

    def _client(self, source: str):
        if self.client_factory:
            return self.client_factory(source)
        from vckg.crawlers.runner import load_sources
        c = load_sources(ROOT / "config/sources.yaml")["crawler"]
        return PoliteClient(c["user_agent"], max(float(c["min_delay_seconds"]), self.min_delay), 60.0, c["max_retries"], c["backoff_base"], request_log=self.dir / f"http_{source}.jsonl")

    def stop_requested(self) -> bool:
        if (self.dir / "STOP").exists() or (self.dir / "acquire.STOP").exists():
            self.stop.set()
        return self.stop.is_set()

    def _reserve(self, q: Queue) -> bool:
        with self.lock:
            if q.acquired_new() + self.inflight >= self.max_new:
                return False
            self.inflight += 1
            return True

    def _release(self) -> None:
        with self.lock:
            self.inflight -= 1

    # ------------------------------------------------------------------ one source
    def _source_loop(self, source: str) -> None:
        q = raw = staging = client = None
        try:
            q = Queue(self.queue_path)
            raw = RawPages(self.raw_path)
            staging = Staging(self.staging_db)
            client = self._client(source)
            ident = IdentityIndex(REGISTRY) if self.ident == "auto" and REGISTRY.exists() else (self.ident if isinstance(self.ident, IdentityIndex) else None)
            disc = Discovery(q, lambda s: client, self.staging_db, self.dir / "sitemaps", ident, 1.0, self.low_water, self.feeds, self.cats,
                             log=lambda **k: self._event(source=source, **k))
        except Exception as e:  # noqa: BLE001
            self.errors.append(f"{source}: init {type(e).__name__}: {e}")
            self._event(source=source, event="thread_init_error", error=repr(e)[:400])
            return
        last_tick = 0.0
        try:
            while not self.stop_requested():
                if q.pool(source, self.min_score) < self.low_water and time.time() - last_tick > 60:
                    try:
                        last_tick = time.time()
                        disc.tick(source, self.min_score)
                    except Exception as e:  # noqa: BLE001
                        self._event(source=source, event="discovery_error", error=repr(e)[:300])
                if not self._reserve(q):
                    return  # quota reached
                row = q.next_to_crawl(source, self.min_score)
                if row is None:
                    self._release()
                    more = bool(q.next_sitemaps(source)) or (self.feeds.get(source) and time.time() - last_tick > 6 * 3600)
                    if not more:
                        self.exhausted.add(source)
                        self._event(source=source, event="exhausted")
                        return
                    last_tick = 0.0
                    time.sleep(min(self.idle_sleep, 5))
                    continue
                try:
                    self._fetch(source, row, q, raw, staging, client)
                finally:
                    self._release()
        except Exception as e:  # noqa: BLE001  (an unexpected error in one publisher thread must not kill the other; it is recorded and the run ends FAILED/partial)
            self.errors.append(f"{source}: {type(e).__name__}: {e}")
            self._event(source=source, event="thread_error", error=repr(e)[:400])
        finally:
            for x in (q, raw, staging):
                if x is not None:
                    x.close()
            if client is not None:
                client.close()

    def _fetch(self, source: str, row, q: Queue, raw: RawPages, staging: Staging, client) -> None:
        url = row["url"]
        try:
            r = client.get(url)
        except RobotsDisallowed:
            q.mark_crawl(url, "robots_disallowed")
            self.counters["robots"] += 1
            return
        except FetchError as e:
            msg = str(e)
            if "access restricted" in msg:
                q.mark_crawl(url, "restricted", error=msg[:200])
                self.counters["failed"] += 1
            elif row["crawl_attempts"] + 1 >= 3:
                q.mark_crawl(url, "failed", error=msg[:200])
                self.counters["failed"] += 1
            else:
                q.mark_crawl(url, "failed", retry_in=120 * 2 ** row["crawl_attempts"], error=msg[:200])
                self.counters["retries"] += 1
            return
        self.counters["fetched"] += 1
        retry_locked(lambda: raw.put(url, r.content, r.status_code, r.charset_encoding))
        q.mark_crawl(url, "fetched", http_status=r.status_code)
        try:
            ex = extract_article(decode_response(r.content, r.charset_encoding), url)
        except ExtractionRejected as err:
            reason = str(err)
            q.mark_parse(url, "rejected_" + reason.split(":")[0], detail=reason[:200])
            self.counters["rejected"] += 1
            retry_locked(lambda: staging.skip(url, reason))
            return
        except Exception as e:  # noqa: BLE001
            q.mark_parse(url, "failed", detail=repr(e)[:200])
            self.counters["failed"] += 1
            return
        try:
            status, art = retry_locked(lambda: staging.add_article(url, source, ex.title or row["slug"] or "", ex.text, ex.published_at, ex.parser, r.status_code))
        except sqlite3.IntegrityError:  # the other publisher thread stored the same content between the hash check and the insert
            status, art = "duplicate_content", None
        if art is None:
            q.mark_parse(url, status, detail="not new")
            self.counters["duplicates"] += 1
            return
        q.mark_parse(url, "ok", article_id=art.article_id, content_hash=art.content_hash, chars=len(ex.text))
        self.counters["stored_new"] += 1
        if self.counters["fetched"] % self.audit_every == 0:
            self._audit()

    def _audit(self) -> None:
        logs = list(self.dir.glob("http_*.jsonl"))
        if not logs:
            return
        bad = 0
        for lg in logs:
            bad += check_request_spacing(lg, self.min_delay, since=self.started_wall)["violations"]
        self.spacing_ok = bad == 0
        if bad:
            self.errors.append(f"HTTP spacing violations: {bad}")
            self.stop.set()

    # ------------------------------------------------------------------ run
    def run(self) -> int:
        try:
            with job_lock(self.dir, "acquire.lock"):
                return self._run()
        except LockHeld as e:
            print(f"LOCKED: {e}", file=sys.stderr)
            return 5

    def _kpi(self, q: Queue) -> dict:
        c = q.counts()
        return {"discovered": c["discovered"], "downloaded": c["downloaded"], "parsed_ok": c["parsed_ok"], "crawl": c["crawl"], "parse": c["parse"], "by_publisher": c["by_publisher"],
                "by_topic": c["by_topic"], "discovered_by_source": c["discovered_by_source"], "failed_crawl": c["failed_crawl"], "sitemaps": c["sitemaps"]}

    def _run(self) -> int:
        (self.dir / "acquire.STOP").unlink(missing_ok=True)
        self.status = Status(self.dir / "acquire_status.json", "mass-acquire")
        self.status.update(state="RUNNING", mode="staging", max_new=self.max_new, min_score=self.min_score, min_delay=self.min_delay, sources=self.sources)
        self.status.start_heartbeat()
        if self.install_signals and threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", None)):
                if sig is not None:
                    signal.signal(sig, lambda *_: self.stop.set())
        q = Queue(self.queue_path)
        RawPages(self.raw_path).close()  # create schemas once, before the publisher threads open the same files
        Staging(self.staging_db).close()
        threads = [threading.Thread(target=self._source_loop, args=(s,), name=f"acq-{s}", daemon=True) for s in self.sources]
        for t in threads:
            t.start()
        try:
            while any(t.is_alive() for t in threads):
                self.stop_requested()
                k = self._kpi(q)
                self.status.update(counters=dict(self.counters), inflight=self.inflight, acquired_new=q.acquired_new(), exhausted_sources=sorted(self.exhausted), http_spacing_ok=self.spacing_ok,
                                   last_error=self.errors[-1] if self.errors else None, **k)
                time.sleep(self.poll)
            for t in threads:
                t.join()
            self._audit()
            acquired = q.acquired_new()
            self.status.update(counters=dict(self.counters), acquired_new=acquired, http_spacing_ok=self.spacing_ok, exhausted_sources=sorted(self.exhausted), **self._kpi(q))
            if self.errors:
                state, code = "FAILED", 4
            elif self.stop.is_set():
                state, code = "STOPPED", 0
            elif acquired >= self.max_new:
                state, code = "COMPLETED", 0
            else:
                state, code = "COMPLETED", 0  # candidates exhausted on every accessible source: a REPORTED shortfall, never padded
            self.status.update(last_error=(self.errors[-1] if self.errors else None), errors=list(self.errors), state=state, finished_at=now(), shortfall=max(self.max_new - acquired, 0) if state == "COMPLETED" else None, stop_reason="STOP" if state == "STOPPED" else None)
            self._event(event="finish", state=state, acquired=acquired)
            return code
        finally:
            self.status.stop_heartbeat()
            q.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="acquire")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--campaign-dir", default=str(CAMPAIGN_DIR))
    r.add_argument("--max-new", type=int, default=MAX_NEW_CEILING)
    r.add_argument("--min-score", type=float, default=1.0)
    r.add_argument("--min-delay", type=float, default=2.5)
    r.add_argument("--sources", nargs="*")
    r.add_argument("--low-water", type=int, default=1500)
    a = ap.parse_args(argv)
    feeds, cats = {}, {}
    from vckg.crawlers.runner import load_sources
    cfg = load_sources(ROOT / "config/sources.yaml")["sources"]
    for k, v in cfg.items():
        feeds[k], cats[k] = v.get("feeds", []), v.get("category_pages", [])
    return Acquirer(Path(a.campaign_dir), max_new=a.max_new, min_score=a.min_score, min_delay=a.min_delay, sources=a.sources, feeds=feeds, category_pages=cats, low_water=a.low_water).run()


if __name__ == "__main__":
    sys.exit(main())
