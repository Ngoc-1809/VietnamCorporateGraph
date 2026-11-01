"""Mass-campaign supervisor: keeps the acquisition worker, the single GPU NLP worker and Ollama alive for days, aggregates and syncs the graph, writes KPIs and reports.

  python -m vckg.campaign.supervisor run [--campaign-dir data/campaign/mass] [--max-articles 30000] [--qwen-budget 90000] [--chunk-size 200] [--no-neo4j]
  python -m vckg.campaign.supervisor status

Children are started through the existing independent runner (`scripts/run-job.ps1`, fully detached) and watched through their own status.json heartbeat + PID.
A crashed child is restarted with backoff (bounded per hour); Ollama is restarted when unreachable; a poison article is isolated by the worker after 3 crashes. At most ONE
NLP worker exists (processor lock + GPU lock). STOP = `<campaign-dir>/STOP` (both children finish their current unit and checkpoint). The supervisor never reports COMPLETED
while articles are still pending/deferred/failed: those end states are INCOMPLETE with the reasons spelled out. When everything is finished it runs the final aggregation +
exports, a last Neo4j sync (if safe), writes the final reports and removes the watchdog task. No precision/recall is ever claimed (no gold labels)."""
from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from vckg.campaign.queue import Queue
from vckg.jobs.pipeline_worker import PIPE_DIR, LockHeld, Status, job_lock, now, pid_alive, read_status

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_DIR = ROOT / "data/campaign/mass"
AGG_DIR = ROOT / "data/aggregate"
REPORT_DIR = ROOT / "reports/campaign"
TERMINAL = ("COMPLETED", "FAILED", "STOPPED", "INCOMPLETE")
WATCHDOG_TASK = "VCKG-campaign-watchdog"
MAX_ARTICLES = 30_000
QWEN_BUDGET = 90_000


def read_json(p: Path) -> dict:
    for _ in range(5):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            time.sleep(0.1)
    return {}


def ps(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """PowerShell with output to a temp file (never a pipe: detached grandchildren could keep a pipe open and block us)."""
    log = ROOT / "logs" / "campaign-ps.last.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as f:
        r = subprocess.run(check=False, args=["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", *args], stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    r.stdout = log.read_text(encoding="utf-8", errors="replace")
    return r


def launch_detached(name: str, command: str) -> bool:
    """Existing independent runner: detached from this process, logs/exit code under logs/jobs."""
    r = ps(["-File", str(ROOT / "scripts/run-job.ps1"), "-Name", name, "-Command", command, "-Force"], 120)
    return r.returncode == 0


def ollama_up(host: str = "http://127.0.0.1:11434", model: str = "qwen3.5:9b") -> bool:
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as r:
            return any(m["name"] == model for m in json.loads(r.read()).get("models", []))
    except Exception:  # noqa: BLE001
        return False


class Supervisor:
    def __init__(self, campaign_dir: Path = CAMPAIGN_DIR, *, max_articles: int = MAX_ARTICLES, qwen_budget: int = QWEN_BUDGET, chunk_size: int = 200, min_delay: float = 2.5,
                 neo4j: bool = True, neo4j_every_chunks: int = 10, tick: float = 15.0, summary_every: int = 1000, launch=launch_detached, ollama_check=ollama_up,
                 ollama_start=None, restarts_per_hour: int = 12, install_signals: bool = True, finalize_fn=None, neo4j_fn=None, watchdog_remove=None,
                 pipe_dir: Path = PIPE_DIR, agg_dir: Path = AGG_DIR, report_dir: Path = REPORT_DIR, final_report: Path | None = None):
        if max_articles > MAX_ARTICLES or qwen_budget > QWEN_BUDGET:
            raise SystemExit(f"limits exceeded: max {MAX_ARTICLES} articles / {QWEN_BUDGET} Qwen calls")
        self.dir = Path(campaign_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.max_articles, self.budget, self.chunk_size, self.min_delay = max_articles, qwen_budget, chunk_size, min_delay
        self.neo4j, self.neo4j_every, self.tick, self.summary_every = neo4j, neo4j_every_chunks, tick, summary_every
        self.launch, self.ollama_check, self.restarts_per_hour = launch, ollama_check, restarts_per_hour
        self.ollama_start = ollama_start or (lambda: launch_detached("ollama-serve", ". .\\scripts\\enter-project.ps1; & .\\runtime\\ollama\\ollama.exe serve"))
        self.finalize_fn, self.neo4j_fn = finalize_fn, neo4j_fn
        self.watchdog_remove = watchdog_remove or (lambda: ps(["-Command", f"schtasks /Delete /TN {WATCHDOG_TASK} /F"], 60))
        self.install_signals = install_signals
        self.pipe_dir, self.agg_dir, self.report_dir = Path(pipe_dir), Path(agg_dir), Path(report_dir)
        self.final_report = final_report or ROOT / "reports/campaign_final.md"
        self.stop_flag = threading.Event()
        self.restarts: dict[str, list[float]] = {"acquire": [], "process": []}
        self.last_launch: dict[str, float] = {}
        self.status: Status | None = None
        self.neo4j_blocker: str | None = None
        self.neo4j_last_chunks = 0
        self.last_kpi_log = 0.0
        self.last_summary = 0
        self.start_time = time.time()

    # ------------------------------------------------------------------ children
    def _commands(self) -> dict[str, str]:
        return {"acquire": f". .\\scripts\\enter-project.ps1; uv run python -m vckg.campaign.acquire run --campaign-dir {self.dir} --max-new {self.max_articles} --min-delay {self.min_delay}; exit $LASTEXITCODE",
                "process": f". .\\scripts\\enter-project.ps1; uv run python -m vckg.campaign.process run --campaign-dir {self.dir} --chunk-size {self.chunk_size} --qwen-budget {self.budget}; exit $LASTEXITCODE"}

    def child(self, which: str) -> dict:
        st = read_json(self.dir / f"{which}_status.json")
        if not st:
            return {"state": "NOT_STARTED", "alive": False}
        alive = pid_alive(st.get("pid"))
        age = None
        if st.get("heartbeat_at"):
            from datetime import datetime
            age = (datetime.now().astimezone() - datetime.fromisoformat(st["heartbeat_at"])).total_seconds()
        return {**st, "alive": alive, "heartbeat_age_s": age, "terminal": st.get("state") in TERMINAL}

    def ensure(self, which: str, may_start: bool) -> str:
        c = self.child(which)
        if c["state"] == "NOT_STARTED" or (not c["alive"] and not c["terminal"]) or (c["alive"] and not c["terminal"] and c.get("heartbeat_age_s") and c["heartbeat_age_s"] > 600):
            if not may_start:
                return "waiting"
            t = time.time()
            self.restarts[which] = [x for x in self.restarts[which] if t - x < 3600]
            if len(self.restarts[which]) >= self.restarts_per_hour:
                return "restart_limit"
            if t - self.last_launch.get(which, 0) < 45:
                return "backoff"
            if which == "process" and not self.ollama_check():
                return "waiting_ollama"
            if c["alive"]:  # alive but silent for 10 min: do not start a second one (locks would refuse it anyway)
                return "stale"
            ok = self.launch(f"mass-{which}", self._commands()[which])
            self.restarts[which].append(t)
            self.last_launch[which] = t
            self._event(event="child_launch", child=which, ok=ok, previous_state=c["state"])
            return "launched" if ok else "launch_failed"
        unexpected = c["terminal"] and may_start and not self.stop_flag.is_set() and (
            c["state"] == "STOPPED" or (c["state"] == "FAILED" and not (which == "acquire" and "spacing" in str(c.get("last_error") or c.get("errors") or "").lower())))
        if unexpected:  # STOPPED without a STOP request (console closed / signal) or a recoverable FAILED: restart, bounded
            t = time.time()
            self.restarts[which] = [x for x in self.restarts[which] if t - x < 3600]
            if t - self.last_launch.get(which, 0) > 120 and len(self.restarts[which]) < self.restarts_per_hour and (which == "acquire" or self.ollama_check()):
                ok = self.launch(f"mass-{which}", self._commands()[which])
                self.restarts[which].append(t)
                self.last_launch[which] = t
                self._event(event="child_relaunch_after_" + c["state"].lower(), child=which, ok=ok, error=c.get("last_error"))
                return "relaunched"
            return "restart_wait"
        return "ok"

    def _event(self, **kw) -> None:
        with (self.dir / "supervisor_events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), **kw}, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ KPIs
    def kpis(self) -> dict:
        qp = self.dir / "queue.sqlite"
        k: dict = {"at": now(), "uptime_h": round((time.time() - self.start_time) / 3600, 2)}
        if qp.exists():
            q = Queue(qp)
            try:
                c = q.counts()
                k.update(articles_discovered=c["discovered"], articles_downloaded=c["downloaded"], articles_parsed=c["parsed_ok"], crawl_failed=c["failed_crawl"], crawl=c["crawl"], parse=c["parse"], nlp=c["nlp"],
                         articles_processed=c["nlp"].get("done", 0), articles_failed=c["nlp"].get("failed", 0), articles_deferred=c["nlp"].get("deferred", 0),
                         articles_backlog=c["nlp"].get("pending", 0) + c["nlp"].get("chunked", 0), by_publisher=c["by_publisher"], by_topic=c["by_topic"], discovered_by_source=c["discovered_by_source"],
                         sitemaps=c["sitemaps"], chunks_finished=q.db.execute("SELECT COUNT(*) FROM chunks WHERE status='finished'").fetchone()[0],
                         qwen_calls_live=int(q.meta("qwen_live_done", "0") or 0))
            finally:
                q.close()
        acq, prc = self.child("acquire"), self.child("process")
        k["acquire"] = {x: acq.get(x) for x in ("state", "pid", "alive", "heartbeat_age_s", "acquired_new", "counters", "http_spacing_ok", "last_error", "shortfall", "exhausted_sources")}
        k["process"] = {x: prc.get(x) for x in ("state", "pid", "alive", "heartbeat_age_s", "chunk", "stage", "articles_per_min", "eta_hours", "qwen_used", "qwen_budget", "last_error", "stop_reason")}
        k["qwen_calls_live"] = max(k.get("qwen_calls_live", 0), int(prc.get("qwen_used") or 0))
        k["articles_per_min"] = prc.get("articles_per_min")
        k["eta_hours"] = prc.get("eta_hours")
        k["chunk_totals"] = self._chunk_totals()
        agg = read_json(self.agg_dir / "summary.json")
        if agg:
            pt = agg.get("per_tier", {})
            k["graph"] = {"hash": agg.get("content_hash"), "generated_at": agg.get("generated_at"), "nodes_validated": agg.get("unique_domain_nodes", {}).get("validated_union(legacy_official+qa_pass)"),
                          "nodes_all": agg.get("unique_domain_nodes", {}).get("all_tiers(incl. quarantine/reject/legacy_candidate)"),
                          "edges_by_tier": {t: pt[t]["unique_edges"] for t in pt}, "relation_types": agg.get("relation_types", {}).get("all_tiers"), "relation_types_validated": agg.get("relation_types", {}).get("validated_union"),
                          "evidence": agg.get("evidence", {}).get("unique_rows"), "articles_with_evidence": agg.get("evidence", {}).get("articles_all_tiers"),
                          "components": {n: {"components": v["components"], "largest": v["largest"], "nodes": v["nodes"]} for n, v in agg.get("connected_components", {}).items()},
                          "identity_collisions": agg.get("identity_collisions_unresolved", {}).get("total"), "person_merges": agg.get("person_merges")}
            k["new_edges_per_1000_articles"] = self._new_edges_per_1000(k.get("articles_processed", 0))
        du = shutil.disk_usage(str(ROOT))
        k["disk"] = {"free_gb": round(du.free / 1e9, 1), "campaign_gb": round(sum(f.stat().st_size for f in self.dir.rglob("*") if f.is_file()) / 1e9, 2)}
        k["ollama_up"] = self.ollama_check()
        k["neo4j_blocker"] = self.neo4j_blocker
        return k

    def _chunk_totals(self) -> dict:
        tot = {"mentions": 0, "rule_candidates": 0, "llm_candidates": 0, "qa_pass": 0, "qa_quarantine": 0, "qa_reject": 0, "entities_in_candidates": 0, "candidates_unique": 0, "chunks": 0}
        for p in self.pipe_dir.glob("camp-c*/status.json"):
            s = read_json(p)
            tot["chunks"] += 1
            for x in ("rule_candidates", "llm_candidates", "qa_pass", "qa_quarantine", "qa_reject", "entities_in_candidates", "candidates_unique"):
                tot[x] += int(s.get(x) or 0)
        for line in (self.dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if (self.dir / "chunks.jsonl").exists() else []:
            tot["mentions"] += int(json.loads(line).get("mentions", 0))
        return tot

    def _new_edges_per_1000(self, processed: int) -> dict | None:
        db = self.agg_dir / "staging_graph.sqlite"
        if not db.exists() or processed <= 0:
            return None
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT tier, COUNT(*) FROM src_edges WHERE source_id LIKE 'job:camp-c%' GROUP BY tier").fetchall()
        except sqlite3.Error:
            return None
        finally:
            con.close()
        return {t: round(n * 1000 / processed, 1) for t, n in rows} | {"all_tiers": round(sum(n for _, n in rows) * 1000 / processed, 1)}

    def write_summary(self, k: dict, label: str) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        p = self.report_dir / f"summary_{label}.json"
        p.write_text(json.dumps(k, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        g = k.get("graph") or {}
        md = [f"# Campaign summary {label} ({k['at']})", "", "No gold labels exist: PASS/QUARANTINE counts are rule outcomes, NOT precision/recall/F1.", "",
              (f"- articles: discovered {k.get('articles_discovered')}, downloaded {k.get('articles_downloaded')}, parsed {k.get('articles_parsed')}, processed {k.get('articles_processed')}, "
              f"deferred {k.get('articles_deferred')}, failed {k.get('articles_failed')}, backlog {k.get('articles_backlog')}"),
              f"- by publisher: {k.get('by_publisher')}; by topic: {k.get('by_topic')}",
              f"- chunk totals: {k.get('chunk_totals')}",
              (f"- graph: nodes(validated) {g.get('nodes_validated')}, nodes(all) {g.get('nodes_all')}, edges by tier {g.get('edges_by_tier')}, relation types {g.get('relation_types')}, "
              f"components {g.get('components')}, collisions {g.get('identity_collisions')}"),
              f"- new edges per 1000 processed articles: {k.get('new_edges_per_1000_articles')}",
              f"- Qwen live calls {k.get('qwen_calls_live')}/{self.budget}; speed {k.get('articles_per_min')} art/min; ETA {k.get('eta_hours')} h; disk {k.get('disk')}",
              f"- acquire: {k.get('acquire')}", f"- process: {k.get('process')}", f"- neo4j blocker: {k.get('neo4j_blocker')}"]
        p.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
        return p

    # ------------------------------------------------------------------ neo4j
    def maybe_neo4j(self, chunks_finished: int, final: bool = False) -> None:
        if not self.neo4j or (self.neo4j_blocker and not final):
            return
        if not final and chunks_finished - self.neo4j_last_chunks < self.neo4j_every:
            return
        self.neo4j_last_chunks = chunks_finished
        try:
            if self.neo4j_fn:
                res = self.neo4j_fn()
            else:
                out, err = self.dir / "neo4j_sync.out", self.dir / "neo4j_sync.err"
                with out.open("w", encoding="utf-8") as fo, err.open("w", encoding="utf-8") as fe:
                    rc = subprocess.run(check=False, args=[str(ROOT / ".venv/Scripts/python.exe"), "-m", "vckg.graph.neo4j_validated", "sync"], stdin=subprocess.DEVNULL, stdout=fo, stderr=fe,
                                        timeout=3600, cwd=str(ROOT)).returncode
                tail = (err.read_text(encoding="utf-8", errors="replace") or out.read_text(encoding="utf-8", errors="replace")).strip()[-400:]
                if rc == 6:
                    raise RuntimeError("BLOCKED: " + tail)
                if rc != 0:
                    raise RuntimeError(f"neo4j sync exit {rc}: {tail}")
                res = json.loads(out.read_text(encoding="utf-8"))
            self.neo4j_blocker = None
            with (self.dir / "neo4j_sync_log.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"at": now(), "chunks": chunks_finished, "final": final, **(res or {})}, ensure_ascii=False, default=str) + "\n")
            self._event(event="neo4j_sync", ok=True, idempotent=(res or {}).get("idempotent"))
        except Exception as e:  # noqa: BLE001  (Neo4j is optional: the SQLite/GraphML/CSV graph keeps accumulating)
            self.neo4j_blocker = str(e)[:500]
            self._event(event="neo4j_blocked", error=self.neo4j_blocker)

    # ------------------------------------------------------------------ run
    def run(self) -> int:
        try:
            with job_lock(self.dir, "supervisor.lock"):
                return self._run()
        except LockHeld as e:
            print(f"LOCKED: {e}", file=sys.stderr)
            return 5

    def _sig(self, *_a) -> None:
        self.stop_flag.set()

    def _run(self) -> int:
        self.status = Status(self.dir / "status.json", "mass-campaign")
        self.status.update(state="STARTING", mode="staging", limits={"max_new_articles": self.max_articles, "max_qwen_live_calls": self.budget, "chunk_size": self.chunk_size, "min_delay_s": self.min_delay})
        self.status.start_heartbeat()
        if self.install_signals and threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._sig)  # Ctrl+C = stop; a closing console (SIGBREAK) must NOT stop the campaign: the watchdog restarts what dies
            if hasattr(signal, "SIGBREAK"):
                signal.signal(signal.SIGBREAK, signal.SIG_IGN)
        try:
            while True:
                stopping = (self.dir / "STOP").exists() or self.stop_flag.is_set()
                if not stopping and not self.ollama_check():
                    self._event(event="ollama_restart")
                    self.ollama_start()
                    for _ in range(18):
                        time.sleep(5)
                        if self.ollama_check():
                            break
                acq = self.ensure("acquire", may_start=not stopping)
                prc = self.ensure("process", may_start=not stopping)
                k = self.kpis()
                k["supervisor"] = {"acquire": acq, "process": prc}
                state = "STOPPING" if stopping else ("CRAWLING+PROCESSING" if k["acquire"]["state"] == "RUNNING" else "PROCESSING")
                self.status.update(state=state, **{x: k[x] for x in k if x != "at"})
                if time.time() - self.last_kpi_log > 300:
                    with (self.dir / "kpi.jsonl").open("a", encoding="utf-8") as f:
                        f.write(json.dumps(k, ensure_ascii=False, default=str) + "\n")
                    self.last_kpi_log = time.time()
                done = k.get("articles_processed", 0)
                if self.summary_every and done // self.summary_every > self.last_summary:
                    self.last_summary = done // self.summary_every
                    self.write_summary(k, f"{self.last_summary * self.summary_every:06d}")
                self.maybe_neo4j(k.get("chunks_finished", 0))
                a, p = self.child("acquire"), self.child("process")
                if p.get("state") == "INCOMPLETE" and str(p.get("stop_reason")) == "BUDGET_EXHAUSTED" and a.get("alive") and not a.get("terminal"):
                    (self.dir / "acquire.STOP").write_text("Qwen budget exhausted: no point downloading more articles")
                    self._event(event="acquire_stopped_budget_exhausted")
                both_done = a.get("terminal") and p.get("terminal") and not (a.get("state") == "STOPPED" and not stopping) and not (p.get("state") == "STOPPED" and not stopping)
                if both_done or (stopping and not a.get("alive") and not p.get("alive")):
                    return self._finish(k, stopping)
                time.sleep(self.tick)
        except Exception as e:  # noqa: BLE001
            self._event(event="supervisor_error", error=repr(e)[:500])
            self.status.update(state="FAILED", finished_at=now(), last_error=f"{type(e).__name__}: {e}"[:500])
            return 1
        finally:
            self.status.stop_heartbeat()

    def _finish(self, k: dict, stopping: bool) -> int:
        """Final aggregation (+ full exports), final Neo4j sync, final reports, watchdog removal. State reflects reality: COMPLETED only if nothing is unfinished."""
        self.status.update(state="FINALIZING")
        try:
            if self.finalize_fn:
                self.finalize_fn()
            else:
                from vckg.graph import aggregate as ag
                chunks = [p.parent.name for p in self.pipe_dir.glob("camp-c*/pipeline.sqlite")]
                ag.run_all(self.agg_dir, self.pipe_dir, jobs=[{"job_id": c, "allow_incomplete": True} for c in chunks], register_defaults=True, ingest=[f"job:{c}" for c in chunks], export=True)
        except Exception as e:  # noqa: BLE001
            self._event(event="final_aggregate_failed", error=repr(e)[:400])
            self.status.update(last_error=f"final aggregate: {e}"[:300])
        if str(self.child("process").get("stop_reason")) == "BUDGET_EXHAUSTED" and (self.dir / "queue.sqlite").exists():
            q = Queue(self.dir / "queue.sqlite")
            q.db.execute("UPDATE urls SET nlp_status='deferred', nlp_error='Qwen budget exhausted before processing', nlp_updated_at=? WHERE nlp_status IN ('pending','chunked')", (now(),))
            q.db.commit()
            q.close()
        self.maybe_neo4j(k.get("chunks_finished", 0), final=True)
        k = self.kpis()
        a, p = self.child("acquire"), self.child("process")
        unfinished = {"pending": k.get("nlp", {}).get("pending", 0), "chunked": k.get("nlp", {}).get("chunked", 0), "deferred": k.get("articles_deferred", 0), "failed": k.get("articles_failed", 0)}
        reasons = [f"{n} articles {x}" for x, n in unfinished.items() if n]
        if a.get("state") == "FAILED":
            reasons.append(f"acquisition FAILED: {a.get('last_error')}")
        if p.get("state") == "FAILED":
            reasons.append(f"processing FAILED: {p.get('last_error')}")
        shortfall = a.get("shortfall") or 0
        if stopping:
            state = "STOPPED"
        elif reasons:
            state = "INCOMPLETE"
        else:
            state = "COMPLETED"
        report = self.write_final(k, state, reasons, shortfall)
        self.status.update(**{x: k[x] for x in k if x != "at"}, state=state, finished_at=now(), final_report=str(report), incomplete_reasons=reasons, shortfall=shortfall)
        self._event(event="finish", state=state, reasons=reasons, shortfall=shortfall)
        if state != "STOPPED":
            with contextlib.suppress(Exception):
                self.watchdog_remove()
        return 0 if state in ("COMPLETED", "STOPPED") else 3

    def write_final(self, k: dict, state: str, reasons: list[str], shortfall: int) -> Path:
        p = self.write_summary(k, "final")
        md = p.with_suffix(".md")
        extra = ["", f"## FINAL STATE: {state}", *([f"- reason: {r}" for r in reasons] or ["- all acquired articles were processed"]),
                 f"- acquisition shortfall vs {self.max_articles}: {shortfall} (accessible cleared sources exhausted; never padded)" if shortfall else f"- acquisition reached {self.max_articles} or was stopped",
                 "- Compliance: only sources cleared in config/crawl_compliance.yaml (CafeF, Vietstock); VnEconomy and Bao Dau tu are excluded (written-consent clauses).",
                 "- Exports: data/aggregate/export (graph_validated.graphml, graph_all_tiers.graphml, nodes/edges/evidence/collisions CSV), SQLite data/aggregate/staging_graph.sqlite",
                 "- Neo4j: validated layer only (QA_PASS); QUARANTINE/REJECT stay in the SQLite/CSV exports. Blocker: " + str(self.neo4j_blocker)]
        md.write_text(md.read_text(encoding="utf-8") + "\n".join(extra), encoding="utf-8")
        self.final_report.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(md, self.final_report)
        return self.final_report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="supervisor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--campaign-dir", default=str(CAMPAIGN_DIR))
    r.add_argument("--max-articles", type=int, default=MAX_ARTICLES)
    r.add_argument("--qwen-budget", type=int, default=QWEN_BUDGET)
    r.add_argument("--chunk-size", type=int, default=200)
    r.add_argument("--min-delay", type=float, default=2.5)
    r.add_argument("--no-neo4j", action="store_true")
    s = sub.add_parser("status")
    s.add_argument("--campaign-dir", default=str(CAMPAIGN_DIR))
    a = ap.parse_args(argv)
    if a.cmd == "status":
        st = read_status(Path(a.campaign_dir))
        print(json.dumps(st, ensure_ascii=False, indent=1, default=str))
        return 0
    return Supervisor(Path(a.campaign_dir), max_articles=a.max_articles, qwen_budget=a.qwen_budget, chunk_size=a.chunk_size, min_delay=a.min_delay, neo4j=not a.no_neo4j).run()


if __name__ == "__main__":
    sys.exit(main())
