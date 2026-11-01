"""Phase 6C - independent end-to-end pipeline worker (staging only).

  python -m vckg.jobs.pipeline_worker run --job-id J --manifest M.jsonl [--max-articles N] [--max-qwen-calls N] [--no-llm] [--retry-failed]
  python -m vckg.jobs.pipeline_worker select --from experiments_manifest.jsonl --limit N --out M.jsonl
  python -m vckg.jobs.pipeline_worker finalize --job-id J        (rebuild QA + staging graph from stored artifacts; no inference)
  python -m vckg.jobs.pipeline_worker status --job-id J          (machine-readable status, adds STALE detection)

Job directory data/pipeline/<job_id>/: pipeline.sqlite (articles, artifacts, staging graph), registry.sqlite (PRIVATE COPY of the source registry),
status.json (heartbeat), events.jsonl, STOP (stop request), worker.lock, qa/, qa_report/, export/. Shared versioned caches: data/pipeline/_cache/.
Safety: one worker per job (lock file); each job owns its registry copy, so jobs never write the same database; Neo4j, the source registry and official
edges are never opened for writing; mode 'official-sync' is refused in Phase 6C. A stored/finished article is never reprocessed (same content hash and
same configuration fingerprint); a failed article never aborts the batch and is NEVER reported as success."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import signal
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil

from vckg.jobs.stages import (
    NER_CACHE_VERSION,
    PIPELINE_VERSION,
    CachedNER,
    NonRetryable,
    Runtime,
    load_article,
    process_one,
)

ROOT = Path(__file__).resolve().parents[3]
PIPE_DIR = ROOT / "data/pipeline"
CACHE_DIR = PIPE_DIR / "_cache"
DEFAULT_REGISTRY = ROOT / "data/registry/registry_p5_new.sqlite"
STAGING_DB = ROOT / "data/staging/staging.sqlite"
REL_PATH = ROOT / "config/relations.yaml"
STALE_AFTER_S = 60  # heartbeat is written every <=5 s
HARD_ARTICLE_CEILING = 20  # Phase 6C safety ceiling for an approved smoke run; raise only with an explicit --allow-large
TERMINAL = ("COMPLETED", "FAILED", "STOPPED", "INCOMPLETE")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def pid_alive(pid: int | None) -> bool:
    if not pid or not psutil.pid_exists(pid):
        return False
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


# ------------------------------------------------------------------------------------------------ job store
SCHEMA = """
CREATE TABLE IF NOT EXISTS articles(article_id TEXT PRIMARY KEY, url TEXT, source TEXT, subset TEXT, content_hash TEXT, status TEXT NOT NULL DEFAULT 'PENDING',
  attempts INTEGER NOT NULL DEFAULT 0, stage TEXT, error TEXT, fingerprint TEXT, started_at TEXT, finished_at TEXT, stats TEXT);
CREATE TABLE IF NOT EXISTS artifacts(article_id TEXT, kind TEXT, payload TEXT NOT NULL, PRIMARY KEY(article_id, kind));
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS staging_edges(edge_key TEXT PRIMARY KEY, subject_id TEXT NOT NULL, subject_name TEXT, subject_type TEXT, predicate TEXT NOT NULL,
  object_id TEXT NOT NULL, object_name TEXT, object_type TEXT, factual_status TEXT NOT NULL, valid_from TEXT, valid_to TEXT, decision TEXT NOT NULL,
  quarantine_class TEXT, discovery_method TEXT, agreement TEXT, n_evidence INTEGER, official INTEGER NOT NULL DEFAULT 0 CHECK(official = 0));
CREATE TABLE IF NOT EXISTS staging_evidence(edge_key TEXT NOT NULL, article_id TEXT NOT NULL, evidence_start INTEGER NOT NULL, evidence_end INTEGER NOT NULL,
  evidence_text TEXT, source_url TEXT, extraction_method TEXT, PRIMARY KEY(edge_key, article_id, evidence_start, evidence_end));
CREATE TABLE IF NOT EXISTS staging_entities(entity_id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, resolution_status TEXT, in_validated_edge INTEGER NOT NULL);
"""


class JobStore:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(str(path), timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    def meta(self, key: str, default=None):
        r = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(r[0]) if r else default

    def set_meta(self, key: str, value) -> None:
        self.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, json.dumps(value, ensure_ascii=False)))
        self.db.commit()

    def add_manifest(self, rows: list[dict]) -> tuple[int, int]:
        new = dup = 0
        for r in rows:
            cur = self.db.execute("INSERT OR IGNORE INTO articles(article_id,url,source,subset) VALUES(?,?,?,?)",
                                  (r["article_id"], r.get("url"), r.get("source"), r.get("subset")))
            new += cur.rowcount
            dup += 1 - cur.rowcount
        self.db.commit()
        return new, dup

    def counts(self) -> dict:
        c = {r[0]: r[1] for r in self.db.execute("SELECT status, COUNT(*) FROM articles GROUP BY 1")}
        return {"total": sum(c.values()), "done": c.get("DONE", 0), "failed": c.get("FAILED", 0), "pending": c.get("PENDING", 0) + c.get("RUNNING", 0)}

    def mark_running(self, aid: str, stage: str = "start") -> None:
        self.db.execute("UPDATE articles SET status='RUNNING', stage=?, started_at=?, attempts=attempts+1 WHERE article_id=?", (stage, now(), aid))
        self.db.commit()

    def mark_done(self, aid: str, art: dict, fp: str, content_hash: str, url: str, source: str) -> None:
        with self.db:  # ONE transaction: an article is DONE only together with all its artifacts
            self.db.execute("DELETE FROM artifacts WHERE article_id=?", (aid,))
            for kind in ("mentions", "rule", "chunks", "overlay", "fixes", "decisions"):
                self.db.execute("INSERT INTO artifacts VALUES(?,?,?)", (aid, kind, json.dumps(art[kind], ensure_ascii=False)))
            self.db.execute("UPDATE articles SET status='DONE', error=NULL, stage='done', fingerprint=?, content_hash=?, url=?, source=?, finished_at=?, stats=? WHERE article_id=?",
                            (fp, content_hash, url, source, now(), json.dumps(art["stats"]), aid))

    def mark_failed(self, aid: str, stage: str, err: str, final: bool) -> None:
        self.db.execute("UPDATE articles SET status=?, stage=?, error=?, finished_at=? WHERE article_id=?", ("FAILED" if final else "PENDING", stage, err[:500], now(), aid))
        self.db.commit()

    def done_ids(self, fp: str) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT article_id FROM articles WHERE status='DONE' AND fingerprint=? ORDER BY article_id", (fp,))]

    def artifact(self, aid: str, kind: str):
        r = self.db.execute("SELECT payload FROM artifacts WHERE article_id=? AND kind=?", (aid, kind)).fetchone()
        return json.loads(r[0]) if r else None


# ------------------------------------------------------------------------------------------------ status / heartbeat
class Status:
    """status.json is rewritten atomically by the worker itself (heartbeat thread every <=5 s). Readers must treat an old heartbeat as STALE."""
    FIELDS = ("job_id", "pid", "state", "started_at", "heartbeat_at", "finished_at", "total_articles", "processed_articles", "succeeded_articles",
              "failed_articles", "rule_candidates", "llm_candidates", "qa_pass", "qa_quarantine", "qa_reject", "unique_staging_edges",
              "unique_staging_entities", "llm_calls", "last_error")

    def __init__(self, path: Path, job_id: str):
        self.path, self.lock = path, threading.Lock()
        self.s = {k: None for k in self.FIELDS}
        self.s.update(job_id=job_id, pid=os.getpid(), state="STARTING", started_at=now(), llm_calls=0, qwen_cache_hits=0, rule_candidates=0, llm_candidates=0,
                      qa_pass=0, qa_quarantine=0, qa_reject=0, unique_staging_edges=0, unique_staging_entities=0, mode="staging", current_article=None, stage=None)
        self._stop = threading.Event()

    def update(self, **kw) -> None:
        with self.lock:
            self.s.update(kw)
            self.s["heartbeat_at"] = now()
            self._write()

    def _write(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        data = json.dumps(self.s, ensure_ascii=False, indent=1)
        for i in range(8):
            try:
                tmp.write_text(data, encoding="utf-8")
                os.replace(tmp, self.path)
                return
            except OSError:  # a reader holds the file on Windows: retry
                time.sleep(0.05 * (i + 1))

    def start_heartbeat(self, every: float = 5.0) -> None:
        def loop():
            while not self._stop.wait(every):
                self.update()
        threading.Thread(target=loop, daemon=True, name="heartbeat").start()

    def stop_heartbeat(self) -> None:
        self._stop.set()


def read_status(job_dir: Path) -> dict:
    """Reader view: adds `liveness` = RUNNING_OK | STALE | DEAD | FINISHED | NO_STATUS. Never claims RUNNING without a fresh heartbeat."""
    p = job_dir / "status.json"
    if not p.exists():
        return {"liveness": "NO_STATUS", "job_dir": str(job_dir)}
    for _ in range(5):
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
            break
        except (OSError, ValueError):
            time.sleep(0.1)
    else:
        return {"liveness": "NO_STATUS", "job_dir": str(job_dir)}
    age = (datetime.now().astimezone() - datetime.fromisoformat(s["heartbeat_at"])).total_seconds() if s.get("heartbeat_at") else None
    s["heartbeat_age_s"] = None if age is None else round(age, 1)
    s["pid_alive"] = pid_alive(s.get("pid"))
    if s["state"] in TERMINAL:
        s["liveness"] = "FINISHED"
    elif not s["pid_alive"]:
        s["liveness"] = "DEAD"  # worker vanished without a terminal state (crash/kill): checkpoint kept, rerun to resume
    elif age is not None and age > STALE_AFTER_S:
        s["liveness"] = "STALE"
    else:
        s["liveness"] = "RUNNING_OK"
    return s


class LockHeld(RuntimeError):
    pass


@contextlib.contextmanager
def job_lock(job_dir: Path, name: str = "worker.lock"):
    job_dir.mkdir(parents=True, exist_ok=True)
    p = job_dir / name
    for _ in range(2):
        try:
            fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "at": now()}).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                other = json.loads(p.read_text(encoding="utf-8")).get("pid")
            except (OSError, ValueError):
                other = None
            if pid_alive(other):
                raise LockHeld(f"another worker (PID {other}) owns job {job_dir.name}") from None
            p.unlink(missing_ok=True)  # stale lock of a dead worker
    else:
        raise LockHeld("cannot acquire lock")
    try:
        yield
    finally:
        p.unlink(missing_ok=True)


# ------------------------------------------------------------------------------------------------ staging graph / QA
def edge_key(subject: str, predicate: str, obj: str, status: str, vf: str = "", vt: str = "") -> str:
    return hashlib.sha1("|".join([subject, predicate, obj, status, vf or "", vt or ""]).encode()).hexdigest()[:16]


def build_staging(store: JobStore, rows: list[dict], info: dict, arts_url: dict) -> dict:
    """Rebuild the staging graph tables from QA result rows in ONE transaction (deterministic => idempotent; PK constraints forbid duplicates)."""
    dup = 0
    with store.db:
        for t in ("staging_edges", "staging_evidence", "staging_entities"):
            store.db.execute(f"DELETE FROM {t}")
        used_validated: set[str] = set()
        for r in sorted(rows, key=lambda r: json.dumps(r["key"])):
            s, _, o, st = r["key"]
            ek = edge_key(s, r["predicate"], o, st)
            h = r["hybrid"]
            cur = store.db.execute("INSERT OR IGNORE INTO staging_edges VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                                   (ek, s, info.get(s, {}).get("name", r["subject"]), info.get(s, {}).get("type"), r["predicate"], o, info.get(o, {}).get("name", r["object"]),
                                    info.get(o, {}).get("type"), st, "", "", h["decision"], h["quarantine_class"], r["discovery_method"], h["agreement"], len(r["evidence_all"])))
            if not cur.rowcount:
                dup += 1
                continue
            for e in r["evidence_all"]:
                store.db.execute("INSERT OR IGNORE INTO staging_evidence VALUES(?,?,?,?,?,?,?)",
                                 (ek, e["article_id"], e["evidence_start"], e["evidence_end"], e["evidence_text"], arts_url.get(e["article_id"], ""), e["method"]))
            if h["decision"] in ("PASS", "AUTO_CORRECT"):
                used_validated.update((s, o))
        ents = {x for r in rows for x in (r["key"][0], r["key"][2])}
        for eid in sorted(ents):
            i = info.get(eid, {})
            store.db.execute("INSERT OR IGNORE INTO staging_entities VALUES(?,?,?,?,?)", (eid, i.get("name", eid), i.get("type"), i.get("status"), int(eid in used_validated)))
    q = lambda sql: store.db.execute(sql).fetchone()[0]
    return {"edges_total": q("SELECT COUNT(*) FROM staging_edges"), "edges_validated": q("SELECT COUNT(*) FROM staging_edges WHERE decision IN ('PASS','AUTO_CORRECT')"),
            "edges_quarantine": q("SELECT COUNT(*) FROM staging_edges WHERE decision='QUARANTINE'"), "edges_rejected": q("SELECT COUNT(*) FROM staging_edges WHERE decision='REJECT'"),
            "entities_validated": q("SELECT COUNT(*) FROM staging_entities WHERE in_validated_edge=1"), "evidence_rows": q("SELECT COUNT(*) FROM staging_evidence"),
            "duplicate_edge_keys_dropped": dup, "official_edges": q("SELECT COUNT(*) FROM staging_edges WHERE official=1")}


def export_staging(store: JobStore, out: Path) -> dict:
    """Staging graph files (JSONL + Neo4j-importable CSV). Written to the job dir only; Neo4j is never contacted."""
    from vckg.graph.neo4j_sync import LABELS
    out.mkdir(parents=True, exist_ok=True)
    import csv
    ev = {}
    for r in store.db.execute("SELECT * FROM staging_evidence ORDER BY edge_key, article_id, evidence_start"):
        ev.setdefault(r["edge_key"], []).append({k: r[k] for k in ("article_id", "evidence_start", "evidence_end", "evidence_text", "source_url", "extraction_method")})
    files = {"validated": ("PASS", "AUTO_CORRECT"), "quarantine": ("QUARANTINE",), "rejected": ("REJECT",)}
    n = {}
    for name, decs in files.items():
        rows = [dict(r) for r in store.db.execute(f"SELECT * FROM staging_edges WHERE decision IN ({','.join('?' * len(decs))}) ORDER BY edge_key", decs)]
        for r in rows:
            r["evidence"] = ev.get(r["edge_key"], [])
            r["derived"] = False
            r["namespace"] = "staging"
        (out / f"staging_edges_{name}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        n[name] = len(rows)
    nodes = [dict(r) for r in store.db.execute("SELECT * FROM staging_entities WHERE in_validated_edge=1 ORDER BY entity_id")]
    (out / "staging_nodes.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in nodes), encoding="utf-8")
    with (out / "neo4j_staging_nodes.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id:ID(StagingEntity)", "name", "resolution_status", ":LABEL"])
        for r in nodes:
            w.writerow([r["entity_id"], r["name"], r["resolution_status"], "StagingEntity;" + LABELS.get(r["entity_type"] or "", "Organization").replace(":", ";")])
    with (out / "neo4j_staging_rels.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([":START_ID(StagingEntity)", ":END_ID(StagingEntity)", ":TYPE", "edge_key", "factual_status", "evidence_count", "official:boolean"])
        for r in store.db.execute("SELECT * FROM staging_edges WHERE decision IN ('PASS','AUTO_CORRECT') ORDER BY edge_key"):
            w.writerow([r["subject_id"], r["object_id"], r["predicate"], r["edge_key"], r["factual_status"], r["n_evidence"], "false"])
    return n


# ------------------------------------------------------------------------------------------------ worker
class Worker:
    def __init__(self, job_id: str, manifest: list[dict], *, rt: Runtime | None = None, make_runtime=None, pipe_dir: Path = PIPE_DIR, staging_db: Path = STAGING_DB,
                 registry_source: Path = DEFAULT_REGISTRY, max_articles: int | None = None, max_qwen_calls: int = 60, max_attempts: int = 2, retry_failed: bool = False,
                 qa_every: int = 10, llm_enabled: bool = True, backoff_s: float = 2.0, mode: str = "staging", fingerprint_extra: dict | None = None, install_signals: bool = True,
                 external_status: Status | None = None, gpu_lock: bool = True, batch_ceiling: int = HARD_ARTICLE_CEILING):
        if mode != "staging":
            raise SystemExit("mode 'official-sync' is NOT enabled in Phase 6C: staging only (no Neo4j production writes)")
        if len(manifest) > batch_ceiling and (max_articles is None or max_articles > batch_ceiling) and not os.environ.get("VCKG_ALLOW_LARGE_BATCH"):
            raise SystemExit(f"{len(manifest)} articles exceed the batch ceiling ({batch_ceiling}); pass --max-articles <= {batch_ceiling}")
        self.job_id, self.dir = job_id, pipe_dir / job_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest, self.staging_db, self.registry_source = manifest, staging_db, registry_source
        self.max_articles, self.max_qwen, self.max_attempts, self.retry_failed = max_articles, max_qwen_calls, max_attempts, retry_failed
        self.qa_every, self.llm_enabled, self.backoff, self.mode = qa_every, llm_enabled, backoff_s, mode
        self.rt, self.make_runtime, self.extra = rt, make_runtime, fingerprint_extra or {}
        self.stop_reason: str | None = None
        self.install_signals = install_signals
        self.ext, self.use_gpu_lock, self.pipe_dir = external_status, gpu_lock, pipe_dir  # external: an orchestrator (Phase 6D) owns status.json, the job lock, STOP and the terminal state
        self.final_state: str | None = None
        self.status: Status | None = None

    # -- config fingerprint: a finished article is reusable only if everything that influences its artifacts is unchanged
    def fingerprint(self) -> str:
        from vckg.ner.span_recovery import RECOVERY_VERSION
        from vckg.relation_extraction.llm_discovery import DISCOVERY_PROMPT_VERSION
        from vckg.validation.hybrid_validator import VALIDATOR_VERSION
        return sha({"pipeline": PIPELINE_VERSION, "ner_cache": NER_CACHE_VERSION, "recovery": RECOVERY_VERSION, "prompt": DISCOVERY_PROMPT_VERSION,
                    "validator": VALIDATOR_VERSION, "relations": hashlib.sha256(REL_PATH.read_bytes()).hexdigest()[:16], "llm": self.llm_enabled, **self.extra})

    def stop_requested(self) -> bool:
        if (self.dir / "STOP").exists():
            self.stop_reason = self.stop_reason or "STOP_FILE"
        return self.stop_reason is not None

    def _event(self, **kw) -> None:
        with (self.dir / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), **kw}, ensure_ascii=False) + "\n")

    def _signal(self, signum, _frame) -> None:
        self.stop_reason = f"SIGNAL_{signum}"

    def run(self) -> int:
        try:
            with contextlib.ExitStack() as st:
                if self.use_gpu_lock:  # at most ONE NLP worker (GLiNER + Qwen) on the GPU at a time, across all jobs
                    st.enter_context(job_lock(self.pipe_dir / "_locks", "gpu.lock"))
                if self.ext is None:
                    st.enter_context(job_lock(self.dir))
                return self._run()
        except LockHeld as e:
            print(f"LOCKED: {e}", file=sys.stderr)
            return 5

    def _refresh_counts(self, store: JobStore, qwen_total: dict) -> None:
        c = store.counts()
        self.status.update(total_articles=c["total"], processed_articles=c["done"] + c["failed"], succeeded_articles=c["done"], failed_articles=c["failed"],
                           llm_calls=qwen_total["live"], qwen_cache_hits=qwen_total["cached"], qwen_failed=qwen_total["failed"])

    def _run(self) -> int:
        if self.ext is None:
            (self.dir / "STOP").unlink(missing_ok=True)  # a stale STOP from a previous run must not stop a fresh start
        self.status = self.ext or Status(self.dir / "status.json", self.job_id)
        prev = self.dir / "summary.json"
        if prev.exists():  # resume: show the last known QA numbers until the next finalize instead of zeros
            with contextlib.suppress(OSError, ValueError, KeyError):
                d = json.loads(prev.read_text(encoding="utf-8"))
                dec, g = d["decisions"], d["staging"]
                self.status.s.update(rule_candidates=d["rule_candidates_raw"], llm_candidates=d["llm_candidates_raw"], qa_pass=dec.get("PASS", 0) + dec.get("AUTO_CORRECT", 0),
                                     qa_quarantine=dec.get("QUARANTINE", 0), qa_reject=dec.get("REJECT", 0), unique_staging_edges=g["edges_validated"], unique_staging_entities=g["entities_validated"])
        self.status.update(mode=self.mode)
        if self.ext is None:
            self.status.start_heartbeat()
        if self.install_signals and threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", None)):
                if sig is not None:
                    signal.signal(sig, self._signal)
        store = JobStore(self.dir / "pipeline.sqlite")
        fp = self.fingerprint()
        code = 0
        try:
            rows = self.manifest[: self.max_articles] if self.max_articles else self.manifest
            new, dup = store.add_manifest(rows)
            old_fp = store.meta("fingerprint")
            store.set_meta("fingerprint", fp)
            store.set_meta("registry_source", str(self.registry_source))
            qt = store.meta("qwen_totals", {"live": 0, "cached": 0, "failed": 0})
            self._event(event="start", manifest_rows=len(rows), new=new, already_known=dup, fingerprint=fp, previous_fingerprint=old_fp)
            self._refresh_counts(store, qt)
            if self.rt is None:
                reg = self.dir / "registry.sqlite"
                if not reg.exists():
                    shutil.copy(self.registry_source, reg)  # PRIVATE copy; the source registry is only read
                self.rt = self.make_runtime(self.dir, reg, self.staging_db, self.llm_enabled)
            # we hold the job lock: any RUNNING row belongs to a worker that died mid-article; a crash does not count as an article failure
            crashes = store.meta("crashes", {})
            for r in store.db.execute("SELECT article_id FROM articles WHERE status='RUNNING'").fetchall():
                crashes[r[0]] = crashes.get(r[0], 0) + 1  # the worker died while processing this article
                if crashes[r[0]] >= 3:  # poison article: isolate it instead of crashing the worker forever
                    store.db.execute("UPDATE articles SET status='FAILED', error='CRASHED_WORKER x3', attempts=? WHERE article_id=?", (self.max_attempts, r[0]))
            store.set_meta("crashes", crashes)
            store.db.execute("UPDATE articles SET status='PENDING', attempts=MAX(attempts-1,0) WHERE status='RUNNING'")
            if self.rt.llm is not None:
                self._wrap_llm(store, qt, self.rt.llm)
            pending = []
            for r in rows:
                a = store.db.execute("SELECT status, attempts, fingerprint FROM articles WHERE article_id=?", (r["article_id"],)).fetchone()
                if a["status"] == "DONE" and a["fingerprint"] == fp:
                    continue  # idempotent: never reprocess finished work
                if a["status"] == "FAILED" and not self.retry_failed and a["attempts"] >= self.max_attempts:
                    continue
                if a["status"] == "FAILED" and self.retry_failed:
                    store.db.execute("UPDATE articles SET attempts=0 WHERE article_id=?", (r["article_id"],))
                pending.append(r["article_id"])
            store.db.commit()
            pending = list(dict.fromkeys(pending))
            self.status.update(state="PROCESSING" if self.ext else "RUNNING")
            self._event(event="pending", n=len(pending), skipped_done=len(rows) - len(pending))
            since_qa = 0
            for aid in pending:
                if self.stop_requested():
                    break
                ok = self._article(store, aid, fp, qt)
                since_qa += 1
                self._refresh_counts(store, qt)
                if ok is None:  # budget exhausted / fatal -> stop gracefully, keep checkpoint
                    break
                if since_qa >= self.qa_every:
                    self.finalize(store)
                    since_qa = 0
            self.status.update(current_article=None, stage="finalize", **({"state": "FINALIZING"} if self.ext else {}))
            self.finalize(store)
            c = store.counts()
            if self.stop_reason:
                state, code = "STOPPED", 3 if self.stop_reason == "BUDGET" else 0  # user-requested stop is a clean exit
            elif c["failed"] or c["pending"]:
                state, code = "FAILED", 4  # partial failure is NEVER reported as COMPLETED
            else:
                state = "COMPLETED"
            self.final_state = state
            self.status.update(stop_reason=self.stop_reason, current_article=None, stage=None, **({} if self.ext else {"state": state, "finished_at": now()}))
            self._event(event="finish", state=state, counts=c)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001  (worker-level failure: recorded, never silent)
            self.final_state = "FAILED"
            self.status.update(last_error=f"{type(e).__name__}: {e}"[:500], **({} if self.ext else {"state": "FAILED", "finished_at": now()}))
            self._event(event="worker_error", error=repr(e))
            code = 1
        finally:
            if self.ext is None:
                self.status.stop_heartbeat()
            store.db.close()
        return code

    def _article(self, store: JobStore, aid: str, fp: str, qt: dict) -> bool | None:
        """True = done, False = failed (isolated, batch continues), None = stop the whole worker (Qwen budget)."""
        from vckg.relation_extraction.llm_discovery import BudgetExceeded
        llm = self.rt.llm
        while True:
            attempts = store.db.execute("SELECT attempts FROM articles WHERE article_id=?", (aid,)).fetchone()[0]
            if attempts >= self.max_attempts:
                err = store.db.execute("SELECT error FROM articles WHERE article_id=?", (aid,)).fetchone()[0] or "unknown"
                store.mark_failed(aid, "retries_exhausted", err, True)
                return False
            store.mark_running(aid)
            self.status.update(current_article=aid, stage="load")
            try:
                if llm is not None:
                    remaining = self.max_qwen - qt["live"]
                    if remaining <= 0:
                        raise BudgetExceeded("live Qwen call cap reached")
                    llm.max_live = llm.stats.calls + remaining
                art = load_article(self.staging_db, aid)
                res = process_one(self.rt, art, progress=lambda s: self.status.update(stage=s), stop=self.stop_requested)
                store.mark_done(aid, res, fp, art.content_hash, art.url, art.source)
                self._event(event="article_done", article_id=aid, **res["stats"])
                return True
            except BudgetExceeded as e:
                # windows already executed are cached; the article stays PENDING (attempt not counted) and resumes after the cap is raised
                store.db.execute("UPDATE articles SET status='PENDING', attempts=MAX(attempts-1,0), error=? WHERE article_id=?", (str(e), aid))
                store.db.commit()
                self.stop_reason = "BUDGET"
                self.status.update(last_error=f"BudgetExceeded: {e}")
                self._event(event="budget_stop", article_id=aid)
                return None
            except NonRetryable as e:
                store.mark_failed(aid, "load", str(e), True)
                store.db.execute("UPDATE articles SET attempts=? WHERE article_id=?", (self.max_attempts, aid))
                store.db.commit()
                self.status.update(last_error=str(e))
                self._event(event="article_failed", article_id=aid, error=str(e), final=True)
                return False
            except Exception as e:  # noqa: BLE001  error isolation: this article only
                msg = f"{type(e).__name__}: {e}"
                final = attempts + 1 >= self.max_attempts
                store.mark_failed(aid, self.status.s.get("stage") or "?", msg, final)
                self.status.update(last_error=f"{aid}: {msg}"[:500])
                self._event(event="article_failed", article_id=aid, error=msg, final=final, attempt=attempts + 1)
                if final or self.stop_requested():
                    return False
                time.sleep(self.backoff * (attempts + 1))

    @staticmethod
    def _wrap_llm(store: JobStore, qt: dict, llm) -> None:
        """Persist the cumulative Qwen accounting after EVERY call (also failed attempts), so a hard kill cannot lose it."""
        orig = llm.discover
        last = [llm.stats.calls, llm.stats.cache_hits, llm.stats.failures]

        def discover(*a, **k):
            try:
                return orig(*a, **k)
            finally:
                st = llm.stats
                qt.update(live=qt["live"] + st.calls - last[0], cached=qt["cached"] + st.cache_hits - last[1], failed=qt["failed"] + st.failures - last[2])
                last[:] = [st.calls, st.cache_hits, st.failures]
                store.set_meta("qwen_totals", qt)
        llm.discover = discover

    # -- fusion + hybrid QA + staging graph over all finished articles (deterministic; no inference)
    def finalize(self, store: JobStore) -> dict:
        from vckg.graph.neo4j_sync import registry_info
        from vckg.validation import hybrid_qa
        fp = store.meta("fingerprint")
        ids = store.done_ids(fp)
        reg = self.dir / "registry.sqlite"
        merged = 0
        if self.rt is not None:  # batch-level person consolidation exactly as in the Phase 5 pipeline (same name + same organisation; logged, idempotent)
            merged = self.rt.resolver.consolidate_persons()
            self.rt.store.db.commit()
        out = {"articles": len(ids), "persons_consolidated_now": merged}
        if not ids:
            self.status.update(rule_candidates=0, llm_candidates=0)
            return out
        run_dir = self.dir / "run"
        run_dir.mkdir(exist_ok=True)
        ments, rule, chunks, overlay, manifest = [], [], [], {}, {}
        meta = {r["article_id"]: dict(r) for r in store.db.execute("SELECT * FROM articles WHERE status='DONE'")}
        for aid in ids:
            ments += store.artifact(aid, "mentions")
            rule += store.artifact(aid, "rule")
            chunks += store.artifact(aid, "chunks")
            overlay.update(store.artifact(aid, "overlay"))
            manifest[aid] = {"source": meta[aid]["source"], "subset": meta[aid]["subset"] or "n/a", "url": meta[aid]["url"]}
        (run_dir / "entities.jsonl").write_text("\n".join(json.dumps(m, ensure_ascii=False) for m in ments), encoding="utf-8")
        n_llm = sum(len(c["accepted"]) for c in chunks)
        out.update(rule_candidates=len(rule), llm_candidates=n_llm)
        if not rule and not n_llm:
            build_staging(store, [], {}, {})
            self.status.update(rule_candidates=0, llm_candidates=0, qa_pass=0, qa_quarantine=0, qa_reject=0, unique_staging_edges=0, unique_staging_entities=0)
            return out
        hybrid_qa.run(registry=reg, out_dir=self.dir / "qa", rep_dir=self.dir / "qa_report", overlay=overlay, manifest=manifest, run_dir=run_dir,
                      staging_db=self.staging_db, rule_rows=rule, llm_chunks=chunks)
        rows = [json.loads(x) for x in (self.dir / "qa/results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        info = registry_info(reg)
        urls = {a: m["url"] for a, m in manifest.items()}
        g = build_staging(store, rows, info, urls)
        export_staging(store, self.dir / "export")
        dec = {}
        for r in rows:
            dec[r["hybrid"]["decision"]] = dec.get(r["hybrid"]["decision"], 0) + 1
        out.update(decisions=dec, staging=g)
        summary = {"job_id": self.job_id, "articles_in_qa": len(ids), "fingerprint": fp, "decisions": dec, "staging": g, "rule_candidates_raw": len(rule), "llm_candidates_raw": n_llm,
                   "qa_note": "No gold: PASS/QUARANTINE are rule outcomes, not precision. SEMANTIC_ONLY_CLEAN is quarantine, never official.", "mode": self.mode, "at": now()}
        (self.dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status.update(rule_candidates=len(rule), llm_candidates=n_llm, qa_pass=dec.get("PASS", 0) + dec.get("AUTO_CORRECT", 0), qa_quarantine=dec.get("QUARANTINE", 0),
                           qa_reject=dec.get("REJECT", 0), unique_staging_edges=g["edges_validated"], unique_staging_entities=g["entities_validated"],
                           candidates_unique=g["edges_total"], entities_in_candidates=store.db.execute("SELECT COUNT(*) FROM staging_entities").fetchone()[0])
        return out


# ------------------------------------------------------------------------------------------------ real backends
def real_runtime(job_dir: Path, registry: Path, staging_db: Path, llm_enabled: bool) -> Runtime:
    from vckg.entity_linking.resolver import EntityResolver
    from vckg.entity_linking.store import RegistryStore
    from vckg.relation_extraction.candidates import load_relations
    store = RegistryStore(registry)

    def factory():
        from vckg.ner.gliner_adapter import GlinerNER
        return GlinerNER()
    ner = CachedNER(CACHE_DIR / "ner_cache.sqlite", factory)
    llm = None
    if llm_enabled:
        from vckg.relation_extraction.llm_discovery import DiscoveryLLM
        from vckg.relation_extraction.qwen_verifier import LLMCache
        llm = DiscoveryLLM(LLMCache(CACHE_DIR / "llm_cache.sqlite"), max_live_calls=10**6)
        if not llm.available():
            raise RuntimeError("UNAVAILABLE: Ollama/qwen3.5:9b not reachable (start runtime\\ollama\\ollama.exe or use --no-llm explicitly)")
    return Runtime(store=store, resolver=EntityResolver(store), relations=load_relations(str(REL_PATH)), ner=ner, llm=llm, staging_db=staging_db)


def read_manifest(path: Path) -> list[dict]:
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8-sig").splitlines() if x.strip()]  # tolerate a BOM
    for r in rows:
        if "article_id" not in r:
            raise SystemExit(f"manifest row without article_id: {r}")
    return rows


def select_from(src: Path, limit: int, out: Path) -> list[dict]:
    """Deterministic article selection from an existing manifest: alternate targeted/control in file order, article ids must exist in staging."""
    rows = read_manifest(src)
    t = [r for r in rows if r.get("subset") == "targeted"]
    c = [r for r in rows if r.get("subset") != "targeted"]
    pick = []
    while len(pick) < limit and (t or c):
        for pool, k in ((t, 2), (c, 1)):
            for _ in range(k):
                if pool and len(pick) < limit:
                    pick.append(pool.pop(0))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps({k: r.get(k) for k in ("article_id", "url", "source", "subset")}, ensure_ascii=False) for r in pick), encoding="utf-8")
    return pick


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline_worker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--job-id", required=True)
    r.add_argument("--manifest", required=True)
    r.add_argument("--max-articles", type=int)
    r.add_argument("--max-qwen-calls", type=int, default=60)
    r.add_argument("--max-attempts", type=int, default=2)
    r.add_argument("--retry-failed", action="store_true")
    r.add_argument("--no-llm", action="store_true", help="explicit rule-only run (recorded in the fingerprint)")
    r.add_argument("--qa-every", type=int, default=10)
    r.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    r.add_argument("--mode", choices=["staging", "official-sync"], default="staging")
    r.add_argument("--crawl", action="store_true", help="NOT enabled: production crawl needs explicit approval")
    s = sub.add_parser("select")
    s.add_argument("--from", dest="src", required=True)
    s.add_argument("--limit", type=int, required=True)
    s.add_argument("--out", required=True)
    for n in ("finalize", "status"):
        x = sub.add_parser(n)
        x.add_argument("--job-id", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "select":
        rows = select_from(Path(a.src), a.limit, Path(a.out))
        print(f"{len(rows)} articles -> {a.out}")
        return 0
    if a.cmd == "status":
        print(json.dumps(read_status(PIPE_DIR / a.job_id), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "finalize":
        w = Worker(a.job_id, [], make_runtime=real_runtime, llm_enabled=True, install_signals=False)
        w.status = Status(w.dir / "status_finalize.json", a.job_id)
        store = JobStore(w.dir / "pipeline.sqlite")
        print(json.dumps(w.finalize(store), ensure_ascii=False, default=str, indent=1))
        return 0
    if a.crawl:
        print("--crawl is not enabled in Phase 6C (production crawl requires approval)", file=sys.stderr)
        return 2
    manifest = read_manifest(Path(a.manifest))
    w = Worker(a.job_id, manifest, make_runtime=real_runtime, registry_source=Path(a.registry), max_articles=a.max_articles, max_qwen_calls=a.max_qwen_calls,
               max_attempts=a.max_attempts, retry_failed=a.retry_failed, qa_every=a.qa_every, llm_enabled=not a.no_llm, mode=a.mode)
    return w.run()


if __name__ == "__main__":
    sys.exit(main())


