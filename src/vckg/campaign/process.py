"""Mass-campaign NLP processor: ONE GPU worker that turns the parsed-article queue into graph data, in bounded chunks.

  python -m vckg.campaign.process run [--campaign-dir data/campaign/mass] [--chunk-size 200] [--qwen-budget 90000]

Per chunk (job id `camp-cNNNNN`, own directory + checkpoint):
  reserve the next N parsed articles (highest topic score first) -> chunk staging DB (copy of just those rows; the master staging DB is only read) ->
  Phase 6C Worker (GLiNER NER cache, span recovery, article grounding, rule candidates + Qwen discovery, fusion, hybrid QA, staging graph; one GPU lock) ->
  queue statuses (done / failed / deferred) -> cumulative registry chain (identities grounded in earlier chunks stay available; the SEED registry is never written) ->
  incremental aggregation (Phase 6E; tiers never promoted; people are never merged by name alone).
Budget: at most `qwen-budget` live Qwen calls over the whole campaign (counted across retries and resumes, per call). When it is exhausted the unfinished articles are marked
DEFERRED (never done) and the processor ends INCOMPLETE. A crashed worker resumes its chunk; a poison article is isolated after 3 crashes. Nothing here writes Neo4j."""
from __future__ import annotations

import argparse
import json
import shutil
import signal
import sqlite3
import sys
import threading
import time
from pathlib import Path

from vckg.campaign.queue import Queue
from vckg.jobs.pipeline_worker import (
    PIPE_DIR,
    STAGING_DB,
    JobStore,
    LockHeld,
    Status,
    Worker,
    job_lock,
    now,
)
from vckg.jobs.stages import CachedNER, Runtime
from vckg.storage.sqlite import Staging

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_DIR = ROOT / "data/campaign/mass"
SEED_REGISTRY = ROOT / "data/registry/registry_p5_new.sqlite"
QWEN_CEILING = 90_000
CHUNK_CEILING = 500
TERMINAL = ("COMPLETED", "FAILED", "STOPPED", "INCOMPLETE")


def read_json(p: Path) -> dict:
    for _ in range(5):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            time.sleep(0.1)
    return {}


class Processor:
    def __init__(self, campaign_dir: Path = CAMPAIGN_DIR, *, chunk_size: int = 200, qwen_budget: int = QWEN_CEILING, min_chunk: int = 20, pipe_dir: Path = PIPE_DIR,
                 master_staging: Path = STAGING_DB, seed_registry: Path = SEED_REGISTRY, make_runtime=None, aggregate_fn="default", export_every: int = 10, idle_sleep: float = 20.0,
                 max_chunk_failures: int = 5, install_signals: bool = True, worker_kwargs: dict | None = None, error_sleep: float = 60.0,
                 chunk_prefix: str = "camp-c"):
        if not 0 < chunk_size <= CHUNK_CEILING:
            raise SystemExit(f"chunk-size must be in 1..{CHUNK_CEILING}")
        if qwen_budget > QWEN_CEILING:
            raise SystemExit(f"Qwen budget {qwen_budget} exceeds the campaign ceiling {QWEN_CEILING}")
        self.dir = Path(campaign_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size, self.budget, self.min_chunk, self.pipe = chunk_size, qwen_budget, min_chunk, Path(pipe_dir)
        self.master, self.seed_registry = Path(master_staging), Path(seed_registry)
        self.cumulative = self.dir / "registry_cumulative.sqlite"
        self.make_runtime_override, self.aggregate_fn, self.export_every, self.idle_sleep = make_runtime, aggregate_fn, export_every, idle_sleep
        self.max_chunk_failures, self.install_signals, self.worker_kwargs = max_chunk_failures, install_signals, worker_kwargs or {}
        self.error_sleep, self.chunk_prefix = error_sleep, chunk_prefix
        self.stop = threading.Event()
        self.status: Status | None = None
        self.q: Queue | None = None
        self._ner: CachedNER | None = None
        self.recent: list[tuple[float, int]] = []  # (time, articles done) for speed
        self.worker: Worker | None = None

    # ------------------------------------------------------------------ helpers
    def _event(self, **kw) -> None:
        with (self.dir / "process_events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), **kw}, ensure_ascii=False) + "\n")

    def stop_requested(self) -> bool:
        if (self.dir / "STOP").exists() or (self.dir / "process.STOP").exists():
            self.stop.set()
        return self.stop.is_set()

    def acquire_finished(self) -> bool:
        st = read_json(self.dir / "acquire_status.json")
        return st.get("state") in TERMINAL

    def qwen_used(self) -> int:
        q = self.q
        used = int(q.meta("qwen_live_done", "0") or 0)
        for r in q.db.execute("SELECT chunk_id FROM chunks WHERE status NOT IN ('finished')").fetchall():
            db = self.pipe / r[0] / "pipeline.sqlite"
            if db.exists():
                try:
                    s = JobStore(db)
                    used += int((s.meta("qwen_totals", {}) or {}).get("live", 0))
                    s.db.close()
                except sqlite3.Error:
                    pass
        return used

    def _make_runtime(self, job_dir, registry, staging_db, llm_enabled) -> Runtime:
        if self.make_runtime_override:
            return self.make_runtime_override(job_dir, registry, staging_db, llm_enabled)
        from vckg.entity_linking.resolver import EntityResolver
        from vckg.entity_linking.store import RegistryStore
        from vckg.jobs.pipeline_worker import CACHE_DIR
        from vckg.relation_extraction.candidates import load_relations
        from vckg.relation_extraction.llm_discovery import DiscoveryLLM
        from vckg.relation_extraction.qwen_verifier import LLMCache
        store = RegistryStore(registry)
        if self._ner is None:  # GLiNER stays loaded across chunks (the cache key still includes model id + version)
            def factory():
                from vckg.ner.gliner_adapter import GlinerNER
                return GlinerNER()
            self._ner = CachedNER(CACHE_DIR / "ner_cache.sqlite", factory)
        llm = None
        if llm_enabled:
            llm = DiscoveryLLM(LLMCache(CACHE_DIR / "llm_cache.sqlite"), max_live_calls=10**6)
            if not llm.available():
                raise RuntimeError("UNAVAILABLE: Ollama/qwen3.5:9b not reachable")
        return Runtime(store=store, resolver=EntityResolver(store), relations=load_relations(str(ROOT / "config/relations.yaml")), ner=self._ner, llm=llm, staging_db=staging_db)

    def _prepare_chunk_staging(self, cid: str, article_ids: list[str]) -> Path:
        d = self.pipe / cid
        d.mkdir(parents=True, exist_ok=True)
        path = d / "staging.sqlite"
        Staging(path).close()  # schema
        con = sqlite3.connect(f"file:{path.as_posix()}", uri=True)
        con.execute("ATTACH DATABASE ? AS master", (f"file:{self.master.as_posix()}?mode=ro",))
        for i in range(0, len(article_ids), 200):
            part = article_ids[i:i + 200]
            con.execute(f"INSERT OR IGNORE INTO main.articles SELECT * FROM master.articles WHERE article_id IN ({','.join('?' * len(part))})", part)
        con.commit()
        con.execute("DETACH DATABASE master")
        n = con.execute("SELECT COUNT(*) FROM main.articles").fetchone()[0]
        con.close()
        if n < len(article_ids):
            raise RuntimeError(f"chunk staging has {n}/{len(article_ids)} articles (master staging lacks rows)")
        return path

    # ------------------------------------------------------------------ one chunk
    def run_chunk(self, cid: str) -> dict:
        q = self.q
        rows = q.chunk_rows(cid)
        ids = [r["article_id"] for r in rows]
        staging = self._prepare_chunk_staging(cid, ids)
        if not self.cumulative.exists():
            shutil.copy(self.seed_registry, self.cumulative)  # the seed registry is only READ
        manifest = [{"article_id": r["article_id"], "url": r["url"], "source": r["source"], "subset": r["topic"] or "none"} for r in rows]
        remaining = self.budget - self.qwen_used()
        q.chunk_update(cid, status="running", started_at=now())
        self.status.update(chunk=cid, chunk_articles=len(rows), stage="nlp")
        kw = {"backoff_s": 2.0, **self.worker_kwargs}
        w = Worker(cid, manifest, make_runtime=self._make_runtime, pipe_dir=self.pipe, staging_db=staging, registry_source=self.cumulative, max_articles=len(manifest),
                   max_qwen_calls=max(remaining, 0), max_attempts=2, qa_every=10**6, llm_enabled=True, install_signals=False, batch_ceiling=max(len(manifest), 1), **kw)
        self.worker = w
        stopper = threading.Thread(target=self._propagate_stop, args=(w,), daemon=True)
        stopper.start()
        code = w.run()
        self.worker = None
        return self._finish_chunk(cid, code, w)

    def _propagate_stop(self, w: Worker) -> None:
        while self.worker is w:
            if self.stop_requested():
                w.stop_reason = w.stop_reason or "STOP_REQUEST"
                return
            time.sleep(2)

    def _finish_chunk(self, cid: str, code: int, w: Worker) -> dict:
        q = self.q
        jdb = self.pipe / cid / "pipeline.sqlite"
        done = failed = left = 0
        live = 0
        mentions = 0
        if jdb.exists():
            s = JobStore(jdb)
            live = int((s.meta("qwen_totals", {}) or {}).get("live", 0))
            budget_stop = w.stop_reason == "BUDGET"
            for r in s.db.execute("SELECT article_id, status, error, stats FROM articles").fetchall():
                if r["status"] == "DONE":
                    q.set_nlp(r["article_id"], "done")
                    done += 1
                    mentions += int(json.loads(r["stats"] or "{}").get("mentions", 0))
                elif r["status"] == "FAILED":
                    q.set_nlp(r["article_id"], "failed", r["error"])
                    failed += 1
                elif budget_stop:
                    q.set_nlp(r["article_id"], "deferred", "Qwen budget exhausted before processing")
                    left += 1
                else:  # stopped/crashed before this article: back to the queue (re-chunked later), NOT done
                    q.release_to_pending(r["article_id"])
                    left += 1
            s.db.close()
        q.chunk_update(cid, status="finished", finished_at=now(), qwen_live=live, done=done, failed=failed, deferred=left if w.stop_reason == "BUDGET" else 0,
                       note=f"worker_exit={code} stop={w.stop_reason}")
        q.set_meta("qwen_live_done", int(q.meta("qwen_live_done", "0") or 0) + live)
        if done:
            tmp = self.cumulative.with_suffix(".tmp")
            shutil.copy(self.pipe / cid / "registry.sqlite", tmp)  # identities grounded in this chunk are available to the next ones
            tmp.replace(self.cumulative)
        rec = {"chunk": cid, "done": done, "failed": failed, "left": left, "qwen_live": live, "mentions": mentions, "worker_exit": code, "stop_reason": w.stop_reason, "at": now()}
        with (self.dir / "chunks.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._event(event="chunk_finished", **rec)
        return rec

    def aggregate(self, cid: str, n_chunks: int) -> None:
        if self.aggregate_fn is None:
            return
        self.status.update(stage="aggregate")
        try:
            pending = json.loads(self.q.meta("not_aggregated", "[]") or "[]")
            if cid not in pending:
                pending.append(cid)
            fn = self.aggregate_fn
            if fn == "default":
                from vckg.graph import aggregate as ag
                m = ag.run_all(ag.OUT, self.pipe, jobs=[{"job_id": c, "allow_incomplete": True} for c in pending], register_defaults=True, ingest=[f"job:{c}" for c in pending],
                               export=(n_chunks % self.export_every == 0))
            else:
                m = fn(pending, n_chunks)
            self.q.set_meta("not_aggregated", "[]")
            self._event(event="aggregated", chunks=pending, content_hash=(m or {}).get("content_hash"))
        except Exception as e:  # noqa: BLE001  (never lose the chunk: it is retried together with the next one)
            pending = json.loads(self.q.meta("not_aggregated", "[]") or "[]")
            if cid not in pending:
                pending.append(cid)
            self.q.set_meta("not_aggregated", json.dumps(pending))
            self._event(event="aggregate_failed", chunk=cid, error=repr(e)[:400])
            self.status.update(last_error=f"aggregate: {type(e).__name__}: {e}"[:300])

    # ------------------------------------------------------------------ run
    def run(self) -> int:
        try:
            with job_lock(self.dir, "process.lock"):
                return self._run()
        except LockHeld as e:
            print(f"LOCKED: {e}", file=sys.stderr)
            return 5

    def _kpis(self) -> dict:
        c = self.q.counts()
        nlp = c["nlp"]
        done = nlp.get("done", 0)
        t = time.time()
        self.recent = [(a, b) for a, b in self.recent if t - a < 1800] + [(t, done)]
        rate = (self.recent[-1][1] - self.recent[0][1]) / max((self.recent[-1][0] - self.recent[0][0]) / 60, 1e-9) if len(self.recent) > 1 else None
        backlog = nlp.get("pending", 0) + nlp.get("chunked", 0)
        return {"nlp": nlp, "articles_done": done, "articles_failed": nlp.get("failed", 0), "articles_deferred": nlp.get("deferred", 0), "backlog": backlog, "parsed_ok": c["parsed_ok"],
                "articles_per_min": round(rate, 2) if rate else None, "eta_hours": round(backlog / rate / 60, 1) if rate else None, "qwen_used": self.qwen_used(), "qwen_budget": self.budget}

    def _run(self) -> int:
        (self.dir / "process.STOP").unlink(missing_ok=True)
        self.status = Status(self.dir / "process_status.json", "mass-process")
        self.status.update(state="RUNNING", mode="staging", chunk_size=self.chunk_size, qwen_budget=self.budget)
        self.status.start_heartbeat()
        if self.install_signals and threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", None)):
                if sig is not None:
                    signal.signal(sig, lambda *_: self.stop.set())
        self.q = Queue(self.dir / "queue.sqlite")
        failures = 0
        n_chunks = self.q.db.execute("SELECT COUNT(*) FROM chunks WHERE status='finished'").fetchone()[0]
        last_kpi = 0.0
        try:
            while True:
                if self.stop_requested():
                    return self._end("STOPPED", 0, stop_reason="STOP")
                if time.time() - last_kpi > 10:
                    self.status.update(**self._kpis())
                    last_kpi = time.time()
                if self.qwen_used() >= self.budget:
                    left = self.q.db.execute("UPDATE urls SET nlp_status='deferred', nlp_error='Qwen budget exhausted before processing', nlp_updated_at=? WHERE nlp_status IN ('pending','chunked')", (now(),)).rowcount
                    self.q.db.commit()
                    self._event(event="budget_exhausted", deferred=left)
                    return self._end("INCOMPLETE", 3, stop_reason="BUDGET_EXHAUSTED", deferred_now=left)
                cid = self.q.open_chunk()
                if cid is None:
                    pending = self.q.pending_nlp()
                    finished = self.acquire_finished()
                    if pending == 0:
                        if finished:
                            break
                        self.status.update(stage="waiting_for_articles")
                        time.sleep(self.idle_sleep)
                        continue
                    if pending < self.min_chunk and not finished:
                        self.status.update(stage="waiting_for_articles")
                        time.sleep(self.idle_sleep)
                        continue
                    cid = self.q.next_chunk_id(self.chunk_prefix)
                    self.q.take_chunk(cid, self.chunk_size)
                self._event(event="chunk_start", chunk=cid)
                try:
                    rec = self.run_chunk(cid)
                except Exception as e:  # noqa: BLE001  (chunk-level infrastructure failure: bounded retries, then the processor ends FAILED)
                    failures += 1
                    self._event(event="chunk_error", chunk=cid, error=repr(e)[:400], consecutive=failures)
                    self.status.update(last_error=f"{cid}: {type(e).__name__}: {e}"[:300])
                    if failures >= self.max_chunk_failures:
                        return self._end("FAILED", 4, last_error=f"{failures} consecutive chunk failures")
                    time.sleep(min(self.error_sleep * failures, 300))
                    continue
                if rec["worker_exit"] == 1 and rec["done"] == 0 and rec["failed"] == 0 and not rec["left"]:
                    failures += 1  # worker-level failure without any article outcome (e.g. Ollama down)
                    self.q.chunk_update(cid, status="created")
                    if failures >= self.max_chunk_failures:
                        return self._end("FAILED", 4, last_error=f"{failures} consecutive worker failures (see chunk {cid})")
                    time.sleep(min(self.error_sleep * failures, 300))
                    continue
                failures = 0
                n_chunks += 1
                if rec["done"]:
                    self.aggregate(cid, n_chunks)
                self.status.update(**self._kpis(), last_chunk=rec, chunks_finished=n_chunks, stage="idle")
                if rec["stop_reason"] == "BUDGET":
                    return self._end("INCOMPLETE", 3, stop_reason="BUDGET_EXHAUSTED")
            c = self.q.counts()["nlp"]
            bad = c.get("failed", 0) + c.get("deferred", 0)
            return self._end("INCOMPLETE" if bad else "COMPLETED", 0, failed_articles=c.get("failed", 0), deferred_articles=c.get("deferred", 0))
        except Exception as e:  # noqa: BLE001
            self._event(event="processor_error", error=repr(e)[:500])
            return self._end("FAILED", 1, last_error=f"{type(e).__name__}: {e}"[:400])
        finally:
            self.status.stop_heartbeat()
            self.q.close()

    def _end(self, state: str, code: int, **kw) -> int:
        self.status.update(state=state, finished_at=now(), stage=None, chunk=None, **self._kpis(), **kw)
        self._event(event="finish", state=state, **kw)
        return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="process")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--campaign-dir", default=str(CAMPAIGN_DIR))
    r.add_argument("--chunk-size", type=int, default=200)
    r.add_argument("--qwen-budget", type=int, default=QWEN_CEILING)
    r.add_argument("--chunk-prefix", default="camp-c")
    a = ap.parse_args(argv)
    return Processor(Path(a.campaign_dir), chunk_size=a.chunk_size, qwen_budget=a.qwen_budget, chunk_prefix=a.chunk_prefix).run()


if __name__ == "__main__":
    sys.exit(main())
