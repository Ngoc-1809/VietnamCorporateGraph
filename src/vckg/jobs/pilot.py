"""Phase 6D - autonomous crawling pilot orchestrator (staging only, <= 20 NEW articles per job).

  python -m vckg.jobs.pilot run --job-id P --target-new N [--max-qwen-calls 100] [--only cafef vietstock ...] [--seed S]

Phases (one process, one job directory data/pipeline/<job_id>/, one status.json):
  CRAWLING   discovery (Phase 5 `run_discovery`, robots.txt + >=2 s/host through PoliteClient) -> `crawl_plan.json` checkpoint;
             then fetch candidate by candidate (`fetch_one` -> SQLite staging, dedup by canonical URL + content hash) until N NEW articles are staged;
             manifest.jsonl is rewritten after every article.
  PROCESSING the unchanged Phase 6C Worker on the manifest (GLiNER, span recovery, grounding, Qwen discovery, fusion, hybrid QA, staging graph)
  FINALIZING final QA + staging export (inside the worker)
  COMPLETED | FAILED | STOPPED
Safety: the pipeline worker's `--crawl` stays disabled; hard ceiling 20 NEW articles per job (trial articles count); a candidate that is not new
(already staged, duplicate content) is never used to fill the quota; shortfall is reported, not padded. One orchestrator per job (lock), and a global GPU
lock so at most one NLP worker runs. Neo4j, the source registry and official edges are never touched. Resume = same job id: the crawl plan and finished
articles are reused (a fetched article is never fetched again; a DONE article is never reprocessed)."""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import threading
from pathlib import Path

from vckg.crawlers.http import check_request_spacing
from vckg.jobs.pipeline_worker import (
    DEFAULT_REGISTRY,
    PIPE_DIR,
    STAGING_DB,
    LockHeld,
    Status,
    Worker,
    job_lock,
    now,
    real_runtime,
)
from vckg.jobs.selection import (
    STRATEGY,
    IdentityIndex,
    cleared_sources,
    identity_bonus,
    load_compliance,
    pick_next,
    slug_text,
)

ROOT = Path(__file__).resolve().parents[3]
COMPLIANCE_FILE = ROOT / "config/crawl_compliance.yaml"
HARD_NEW_CEILING = 20
DEFAULT_SOURCES = ("cafef", "vietstock", "vneconomy", "baodautu")
MAX_FETCH_ATTEMPTS = 2  # attempts per candidate over the life of the job (PoliteClient already retries 3x inside one attempt)


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class Pilot:
    def __init__(self, job_id: str, target_new: int, *, max_qwen_calls: int = 100, only: list[str] | None = None, seed: int = 20261101,
                 pipe_dir: Path = PIPE_DIR, staging_db: Path = STAGING_DB, sources_cfg: dict | None = None, client_factory=None, discover_fn=None,
                 make_runtime=real_runtime, registry_source: Path = DEFAULT_REGISTRY, rt=None, worker_kwargs: dict | None = None, install_signals: bool = True,
                 compliance: dict | str | None = "default", min_delay: float = 2.0, source_cap: float = 0.6, identity_index: IdentityIndex | None | str = "auto"):
        if not 0 < target_new <= HARD_NEW_CEILING:
            raise SystemExit(f"target-new must be in 1..{HARD_NEW_CEILING} (Phase 6D ceiling), got {target_new}")
        self.job_id, self.target, self.max_qwen, self.only, self.seed = job_id, target_new, max_qwen_calls, only, seed
        self.pipe_dir, self.staging_db, self.dir = pipe_dir, staging_db, pipe_dir / job_id
        self.sources_cfg, self.client_factory, self.discover_fn = sources_cfg, client_factory, discover_fn
        self.make_runtime, self.registry_source, self.rt, self.worker_kwargs = make_runtime, registry_source, rt, worker_kwargs or {}
        self.install_signals = install_signals
        self.compliance = load_compliance(COMPLIANCE_FILE) if compliance == "default" else compliance
        self.min_delay, self.source_cap, self.identity_index = min_delay, source_cap, identity_index
        self.stop_reason: str | None = None
        self.worker: Worker | None = None
        self.status: Status | None = None
        self.plan: dict = {}

    # ---------------------------------------------------------------- helpers
    def stop_requested(self) -> bool:
        if (self.dir / "STOP").exists():
            self.stop_reason = self.stop_reason or "STOP_FILE"
        return self.stop_reason is not None

    def _signal(self, signum, _frame) -> None:
        self.stop_reason = f"SIGNAL_{signum}"
        if self.worker:
            self.worker.stop_reason = self.stop_reason

    def _event(self, **kw) -> None:
        with (self.dir / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), "phase": "crawl", **kw}, ensure_ascii=False) + "\n")

    def _save_plan(self) -> None:
        _atomic_write(self.dir / "crawl_plan.json", json.dumps(self.plan, ensure_ascii=False, indent=1))

    def _rows(self, *statuses: str) -> list[dict]:
        return [r for r in self.plan["candidates"] if r.get("status") in statuses]

    def _crawl_counts(self) -> dict:
        c = self.plan["candidates"]
        new = len(self._rows("inserted"))
        failed = sum(1 for r in c if r.get("status") in ("fetch_error",) and r.get("attempts", 0) >= MAX_FETCH_ATTEMPTS)
        skipped = sum(1 for r in c if str(r.get("status", "")).startswith(("robots", "rejected", "duplicate")))
        return {"target_new": min(self.target, HARD_NEW_CEILING), "discovered": len(c), "candidates_planned": len(self._rows("planned")), "fetched_ok": new,
                "fetch_failed": failed, "fetch_skipped": skipped}

    def _write_manifest(self) -> list[dict]:
        rows = [{"article_id": r["article_id"], "url": r["url"], "source": r["source"], "subset": r.get("subset"), "topic": r.get("topic"), "title": r.get("title"),
                 "selection_score": r.get("selection_score")} for r in self._rows("inserted")]
        _atomic_write(self.dir / "manifest.jsonl", "\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
        return rows

    # ---------------------------------------------------------------- crawl
    def _load_or_create_plan(self, staging) -> None:
        p = self.dir / "crawl_plan.json"
        if p.exists():
            self.plan = json.loads(p.read_text(encoding="utf-8"))
            return
        ids = sorted(a.article_id for a in staging.get_articles())
        _atomic_write(self.dir / "baseline_article_ids.json", json.dumps(ids))  # what was stored BEFORE this job: the definition of "new"
        self.plan = {"job_id": self.job_id, "created_at": now(), "seed": self.seed, "baseline_articles": len(ids), "candidates": [], "discovery": []}
        self._save_plan()

    def _discover(self, staging, client, need: int) -> None:
        from vckg.crawlers.discovery import run_discovery
        known = {r["url"] for r in self.plan["candidates"]}
        wanted = list(self.only) if self.only else list(DEFAULT_SOURCES)
        allowed = cleared_sources(self.compliance, wanted) if self.compliance is not None else wanted
        if not allowed:
            raise SystemExit(f"no cleared source among {wanted} (see config/crawl_compliance.yaml)")
        self.plan["allowed_sources"] = allowed
        self.plan["refused_sources"] = [w for w in wanted if w not in allowed]
        self.plan["strategy"] = STRATEGY
        if self.identity_index == "auto":
            self.identity_index = IdentityIndex(self.registry_source) if Path(self.registry_source).exists() else None
        sel, stats = (self.discover_fn or run_discovery)(client, staging, self.sources_cfg["sources"], max(need * 3, 6), self.seed + len(self.plan["discovery"]), allowed, 4.0, 1.0)
        added = 0
        for r in sel:
            if r["url"] in known or staging.url_seen(r["url"]) or staging.is_skipped(r["url"]):
                continue
            if r.get("source") not in allowed:
                continue  # never plan a source that is not cleared
            ids = self.identity_index.matches(f"{r.get('title') or ''} {slug_text(r['url'])}") if self.identity_index else []
            self.plan["candidates"].append({**{k: r.get(k) for k in ("url", "source", "subset", "title", "topic", "selection_score", "selection_reason", "feed", "published")},
                                            "registry_identity_matches": ids, "identity_bonus": identity_bonus(len(ids)), "strategy": STRATEGY, "status": "planned", "attempts": 0})
            added += 1
        self.plan["discovery"].append({"at": now(), "selected": len(sel), "added": added, **{k: v for k, v in stats.items() if k != "topic_pool"}, "topic_pool": stats.get("topic_pool")})
        self._save_plan()
        self._event(event="discovery", added=added, **{k: stats.get(k) for k in ("pool_new_unique", "dup_of_staged", "selected")})

    def crawl(self) -> bool:
        """-> True if the crawl phase finished normally (quota met or candidates exhausted); False when stopped."""
        from vckg.crawlers.discovery import fetch_one
        from vckg.storage.sqlite import Staging
        staging = Staging(self.staging_db)
        client = None
        try:
            self._load_or_create_plan(staging)
            target = min(self.target, HARD_NEW_CEILING)
            self.status.update(state="CRAWLING", stage="discovery", **self._crawl_counts())
            if len(self._rows("inserted")) < target and len(self._rows("planned")) < target - len(self._rows("inserted")) and not self.stop_requested():
                client = self.client_factory()
                self._discover(staging, client, target - len(self._rows("inserted")))
            while len(self._rows("inserted")) < target:
                if self.stop_requested():
                    return False
                pending = [r for r in self.plan["candidates"] if r.get("status") in ("planned", "fetch_error") and r.get("attempts", 0) < MAX_FETCH_ATTEMPTS]
                if self.compliance is not None:
                    for r in pending:
                        if not self.compliance.get(r["source"], {}).get("cleared"):
                            r["status"] = "source_not_cleared"
                    pending = [r for r in pending if r["status"] != "source_not_cleared"]
                by_src = {}
                for r in self._rows("inserted"):
                    by_src[r["source"]] = by_src.get(r["source"], 0) + 1
                row = pick_next(pending, by_src, max(1, math.ceil(target * self.source_cap)))
                if row is None:
                    break
                client = client or self.client_factory()
                row["attempts"] = row.get("attempts", 0) + 1
                self.status.update(stage="fetch", current_article=row["url"][-80:])
                if staging.url_seen(row["url"]):  # became known since planning (e.g. another job): never "new"
                    row["status"] = "duplicate_url"
                else:
                    fetch_one(client, staging, row)
                self._save_plan()
                self._write_manifest()
                self._event(event="fetched", url=row["url"], status=row["status"], article_id=row.get("article_id"), chars=row.get("chars"))
                self.status.update(**self._crawl_counts())
            return True
        finally:
            self._write_manifest()
            staging.close()
            if client is not None:
                client.close()

    # ---------------------------------------------------------------- run
    def run(self) -> int:
        self.dir.mkdir(parents=True, exist_ok=True)
        try:
            with job_lock(self.dir):
                return self._run()
        except LockHeld as e:
            print(f"LOCKED: {e}", file=sys.stderr)
            return 5

    def _finish(self, state: str, code: int, **extra) -> int:
        self.status.update(state=state, finished_at=now(), current_article=None, stage=None, stop_reason=self.stop_reason, **extra)
        self._event(event="finish", state=state)
        return code

    def _run(self) -> int:
        (self.dir / "STOP").unlink(missing_ok=True)
        self.status = Status(self.dir / "status.json", self.job_id)
        self.status.update(mode="staging", phase="CRAWLING")
        self.status.start_heartbeat()
        if self.install_signals and threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", None)):
                if sig is not None:
                    signal.signal(sig, self._signal)
        try:
            if self.client_factory is None:
                from vckg.crawlers.http import PoliteClient
                from vckg.crawlers.runner import load_sources
                self.sources_cfg = self.sources_cfg or load_sources(ROOT / "config/sources.yaml")
                c = self.sources_cfg["crawler"]
                self.client_factory = lambda: PoliteClient(c["user_agent"], max(float(c["min_delay_seconds"]), self.min_delay), c["timeout_seconds"], c["max_retries"], c["backoff_base"],
                                                           request_log=self.dir / "http_requests.jsonl")
            done = self.crawl()
            sp = check_request_spacing(self.dir / "http_requests.jsonl", self.min_delay) if (self.dir / "http_requests.jsonl").exists() else None
            if sp is not None:
                self.plan["http_spacing"] = sp
                self._save_plan()
                self.status.update(http_requests=sp["total_requests"], http_spacing_ok=sp["ok"], http_min_gap_s=min((h["min_gap_s"] for h in sp["hosts"].values() if h["min_gap_s"] is not None), default=None))
                if not sp["ok"]:
                    self._write_manifest()
                    return self._finish("FAILED", 6, last_error=f"HTTP spacing violation(s): {sp['violations']} (see http_requests.jsonl)")
            rows = self._write_manifest()
            counts = self._crawl_counts()
            shortfall = counts["target_new"] - counts["fetched_ok"]
            self.status.update(total_articles=len(rows), crawl_shortfall=max(shortfall, 0), **counts)
            if not done:
                return self._finish("STOPPED", 0)
            if not rows:
                return self._finish("COMPLETED" if not counts["fetch_failed"] else "FAILED", 0 if not counts["fetch_failed"] else 4,
                                    last_error="no new article could be staged")
            self.status.update(state="PROCESSING", stage="start")
            self.worker = Worker(self.job_id, rows, rt=self.rt, make_runtime=self.make_runtime, pipe_dir=self.pipe_dir, staging_db=self.staging_db, registry_source=self.registry_source,
                                 max_articles=len(rows), max_qwen_calls=self.max_qwen, install_signals=False, external_status=self.status, **self.worker_kwargs)
            self.worker.stop_reason = self.stop_reason
            code = self.worker.run()
            st = self.worker.final_state
            if code == 5:
                return self._finish("FAILED", 5, last_error="another NLP worker holds the GPU lock (or this job)")
            if st == "COMPLETED":
                return self._finish("COMPLETED", 0)
            if st == "STOPPED":
                return self._finish("STOPPED", code)
            return self._finish("FAILED", code or 4)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001  (never silent)
            self.status.update(last_error=f"{type(e).__name__}: {e}"[:500])
            self._event(event="orchestrator_error", error=repr(e))
            return self._finish("FAILED", 1)
        finally:
            self.status.stop_heartbeat()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pilot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--job-id", required=True)
    r.add_argument("--target-new", type=int, required=True)
    r.add_argument("--max-qwen-calls", type=int, default=100)
    r.add_argument("--only", nargs="*")
    r.add_argument("--seed", type=int, default=20261101)
    a = ap.parse_args(argv)
    return Pilot(a.job_id, a.target_new, max_qwen_calls=a.max_qwen_calls, only=a.only, seed=a.seed).run()


if __name__ == "__main__":
    sys.exit(main())
