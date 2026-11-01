"""Phase 6F - controlled scale-up campaign: up to 50 NEW articles as 3 SEQUENTIAL jobs (20 + 20 + 10), then aggregation (Phase 6E). Staging only.

  python -m vckg.jobs.scaleup run --campaign-id scale-campaign [--plan scale01:20,scale02:20,scale03:10] [--budget 160] [--min-delay 2.5]

One process runs the Phase 6D `Pilot` (crawl + Phase 6C worker) for each job in turn, so there is never more than one NLP worker/GPU user; each job has its own
directory, checkpoint and registry copy. A job starts only if the previous one is COMPLETED with no serious data error (failed articles, HTTP spacing violation,
official edges, article overlap with earlier jobs). Hard limits: <= 20 NEW articles per job, <= 50 in total, <= 160 live Qwen calls for the whole campaign
(the remaining budget is passed to each job; exhaustion => STOPPED, checkpoint kept). Only sources cleared in config/crawl_compliance.yaml are crawled.
Resume = rerun with the same ids (COMPLETED jobs are skipped). STOP = data/pipeline/<campaign_id>/STOP (propagated to the running job).
Neo4j, the source registry, official edges, hard validation and prompts are never touched. Aggregation: only COMPLETED jobs are loaded into the 6E aggregate."""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

from vckg.jobs.pilot import HARD_NEW_CEILING, Pilot
from vckg.jobs.pipeline_worker import PIPE_DIR, LockHeld, Status, job_lock, now

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PLAN = (("scale01", 20), ("scale02", 20), ("scale03", 10))
TOTAL_NEW_CEILING = 50
QWEN_BUDGET = 160
MIRROR = ("total_articles", "processed_articles", "succeeded_articles", "failed_articles", "rule_candidates", "llm_candidates", "qa_pass", "qa_quarantine", "qa_reject",
          "unique_staging_edges", "unique_staging_entities", "candidates_unique", "entities_in_candidates", "target_new", "discovered", "fetched_ok", "fetch_failed", "fetch_skipped",
          "candidates_planned", "crawl_shortfall", "http_requests", "http_spacing_ok", "http_min_gap_s", "stage", "current_article", "qwen_cache_hits", "qwen_failed")


def read_json(p: Path) -> dict:
    for _ in range(5):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            time.sleep(0.1)
    return {}


def validate_job(job_dir: Path, earlier_ids: set[str], target: int) -> list[str]:
    """Serious-data-error checks between jobs. -> list of problems (empty = OK)."""
    st = read_json(job_dir / "status.json")
    problems = []
    if st.get("state") != "COMPLETED":
        problems.append(f"state {st.get('state')!r} != COMPLETED ({st.get('last_error')})")
    if st.get("failed_articles"):
        problems.append(f"{st['failed_articles']} article(s) failed")
    if st.get("http_spacing_ok") is False:
        problems.append("HTTP spacing violation")
    if (st.get("fetched_ok") or 0) > min(target, HARD_NEW_CEILING):
        problems.append("more new articles than the job target")
    if st.get("total_articles") != st.get("succeeded_articles"):
        problems.append("processed != fetched")
    sm = read_json(job_dir / "summary.json")
    if sm and (sm.get("staging") or {}).get("official_edges"):
        problems.append("official edges found in staging")
    man = job_dir / "manifest.jsonl"
    ids = {json.loads(x)["article_id"] for x in man.read_text(encoding="utf-8").splitlines() if x.strip()} if man.exists() else set()
    if ids & earlier_ids:
        problems.append(f"{len(ids & earlier_ids)} article(s) overlap with an earlier job (not new)")
    return problems


class Campaign:
    def __init__(self, campaign_id: str, plan=DEFAULT_PLAN, budget: int = QWEN_BUDGET, min_delay: float = 2.5, pipe_dir: Path = PIPE_DIR, pilot_factory=None,
                 aggregate_fn=None, install_signals: bool = True):
        if any(not 0 < n <= HARD_NEW_CEILING for _, n in plan) or sum(n for _, n in plan) > TOTAL_NEW_CEILING:
            raise SystemExit(f"plan violates limits (<= {HARD_NEW_CEILING} per job, <= {TOTAL_NEW_CEILING} total): {plan}")
        if budget > QWEN_BUDGET:
            raise SystemExit(f"Qwen budget {budget} exceeds the Phase 6F ceiling {QWEN_BUDGET}")
        self.id, self.plan, self.budget, self.min_delay, self.pipe = campaign_id, list(plan), budget, min_delay, pipe_dir
        self.dir = pipe_dir / campaign_id
        self.pilot_factory = pilot_factory or (lambda job, n, left: Pilot(job, n, max_qwen_calls=left, min_delay=self.min_delay, pipe_dir=self.pipe, install_signals=False))
        self.aggregate_fn, self.install_signals = aggregate_fn, install_signals
        self.stop_reason: str | None = None
        self.current: str | None = None
        self.status: Status | None = None
        self.jobs: dict[str, dict] = {}
        self._halt = threading.Event()

    def _event(self, **kw) -> None:
        with (self.dir / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), "phase": "campaign", **kw}, ensure_ascii=False) + "\n")

    def _signal(self, signum, _f) -> None:
        self._request_stop(f"SIGNAL_{signum}")

    def _request_stop(self, why: str) -> None:
        self.stop_reason = self.stop_reason or why
        if self.current:
            (self.pipe / self.current).mkdir(parents=True, exist_ok=True)
            (self.pipe / self.current / "STOP").write_text(why)

    def _mirror_loop(self) -> None:
        while not self._halt.wait(3.0):
            if (self.dir / "STOP").exists():
                self._request_stop("STOP_FILE")
            self._mirror()

    def _mirror(self) -> None:
        kw = {"jobs": self.jobs, "current_job": self.current, "qwen_budget": self.budget, "qwen_used": self._qwen_used()}
        if self.current:
            js = read_json(self.pipe / self.current / "status.json")
            kw.update({k: js[k] for k in MIRROR if k in js})
            if js.get("state") in ("CRAWLING", "PROCESSING", "FINALIZING"):
                kw["state"] = js["state"]
            kw["llm_calls"] = self._qwen_used()
        self.status.update(**kw)

    def _qwen_done(self) -> int:
        return sum(j.get("llm_calls", 0) for j in self.jobs.values() if j.get("counted"))

    def _qwen_used(self) -> int:
        used = self._qwen_done()
        if self.current and not self.jobs.get(self.current, {}).get("counted"):
            used += read_json(self.pipe / self.current / "status.json").get("llm_calls") or 0
        return used

    def run(self) -> int:
        self.dir.mkdir(parents=True, exist_ok=True)
        try:
            with job_lock(self.dir):
                return self._run()
        except LockHeld as e:
            print(f"LOCKED: {e}", file=sys.stderr)
            return 5

    def _finish(self, state: str, code: int, **kw) -> int:
        self._halt.set()
        self.current = None
        self.status.update(state=state, finished_at=now(), stop_reason=self.stop_reason, current_job=None, stage=None, current_article=None, jobs=self.jobs,
                           qwen_budget=self.budget, qwen_used=self._qwen_done(), llm_calls=self._qwen_done(), **kw)
        self._event(event="finish", state=state, **kw)
        return code

    def _run(self) -> int:
        (self.dir / "STOP").unlink(missing_ok=True)
        self.status = Status(self.dir / "status.json", self.id)
        self.status.update(mode="staging", campaign=True, state="STARTING", plan=[list(p) for p in self.plan], qwen_budget=self.budget, qwen_used=0)
        if self.install_signals and threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", None)):
                if sig is not None:
                    signal.signal(sig, self._signal)
        threading.Thread(target=self._mirror_loop, daemon=True, name="campaign-mirror").start()
        try:
            earlier: set[str] = set()
            completed: list[str] = []
            for job, target in self.plan:
                jd = self.pipe / job
                if self.stop_reason or (self.dir / "STOP").exists():
                    self.stop_reason = self.stop_reason or "STOP_FILE"
                    break
                st0 = read_json(jd / "status.json")
                self.jobs.setdefault(job, {"target": target})
                if st0.get("state") == "COMPLETED" and not validate_job(jd, earlier, target):
                    self.jobs[job].update(state="COMPLETED", skipped_already_completed=True, llm_calls=st0.get("llm_calls") or 0, counted=True)
                    earlier |= self._ids(jd)
                    completed.append(job)
                    self._event(event="job_skipped_completed", job=job)
                    continue
                left = self.budget - self._qwen_done()
                if left <= 0:
                    self.stop_reason = "BUDGET"
                    self._event(event="budget_exhausted", job=job)
                    break
                self.current = job
                self.jobs[job].update(state="RUNNING", counted=False, started_at=now(), budget_for_job=left)
                self._event(event="job_start", job=job, target=target, qwen_left=left)
                self.status.update(state="CRAWLING", stage="start", current_job=job)
                code = self.pilot_factory(job, target, left).run()
                js = read_json(jd / "status.json")
                self.jobs[job].update(state=js.get("state"), exit_code=code, llm_calls=js.get("llm_calls") or 0, counted=True, finished_at=now(),
                                      fetched_ok=js.get("fetched_ok"), succeeded=js.get("succeeded_articles"), failed=js.get("failed_articles"), qa=[js.get("qa_pass"), js.get("qa_quarantine"), js.get("qa_reject")],
                                      crawl_shortfall=js.get("crawl_shortfall"), http_spacing_ok=js.get("http_spacing_ok"), stop_reason=js.get("stop_reason"))
                self.current = None
                self._event(event="job_end", job=job, **{k: v for k, v in self.jobs[job].items() if k != "counted"})
                if js.get("state") == "STOPPED":
                    self.stop_reason = self.stop_reason or js.get("stop_reason") or "STOPPED"
                    break
                problems = validate_job(jd, earlier, target)
                if problems:
                    self.jobs[job]["problems"] = problems
                    self._event(event="job_problem", job=job, problems=problems)
                    self.status.update(last_error=f"{job}: " + "; ".join(problems))
                    return self._finish("FAILED", 4, failed_job=job)
                earlier |= self._ids(jd)
                completed.append(job)
            agg = None
            if completed:
                self.status.update(state="FINALIZING", stage="aggregate")
                try:
                    agg = (self.aggregate_fn or self._aggregate)(completed)
                    self._event(event="aggregated", jobs=completed, content_hash=(agg or {}).get("content_hash"))
                except SystemExit as e:
                    self.status.update(last_error=f"aggregation refused: {e}")
                    return self._finish("FAILED", 4, completed_jobs=completed)
                except Exception as e:  # noqa: BLE001
                    self.status.update(last_error=f"aggregation failed: {type(e).__name__}: {e}"[:400])
                    return self._finish("FAILED", 1, completed_jobs=completed)
            if self.stop_reason:
                return self._finish("STOPPED", 3 if self.stop_reason == "BUDGET" else 0, completed_jobs=completed)
            return self._finish("COMPLETED", 0, completed_jobs=completed)
        except Exception as e:  # noqa: BLE001  (never silent)
            self.status.update(last_error=f"{type(e).__name__}: {e}"[:500])
            self._event(event="campaign_error", error=repr(e))
            return self._finish("FAILED", 1)

    def _ids(self, jd: Path) -> set[str]:
        m = jd / "manifest.jsonl"
        return {json.loads(x)["article_id"] for x in m.read_text(encoding="utf-8").splitlines() if x.strip()} if m.exists() else set()

    @staticmethod
    def _aggregate(jobs: list[str]) -> dict:
        from vckg.graph import aggregate as ag
        before = ag.OUT / "summary_before_6f.json"
        if not before.exists() and (ag.OUT / "summary.json").exists():
            before.write_text((ag.OUT / "summary.json").read_text(encoding="utf-8"), encoding="utf-8")  # snapshot of the pre-6F aggregate
        return ag.run_all(ag.OUT, ag.PIPE, jobs=[{"job_id": j} for j in jobs], register_defaults=True)


def parse_plan(s: str) -> list[tuple[str, int]]:
    out = []
    for part in s.split(","):
        name, n = part.split(":")
        out.append((name.strip(), int(n)))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scaleup")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--campaign-id", default="scale-campaign")
    r.add_argument("--plan", default=",".join(f"{a}:{b}" for a, b in DEFAULT_PLAN))
    r.add_argument("--budget", type=int, default=QWEN_BUDGET)
    r.add_argument("--min-delay", type=float, default=2.5)
    a = ap.parse_args(argv)
    if os.environ.get("VCKG_ALLOW_LARGE_BATCH"):
        print("VCKG_ALLOW_LARGE_BATCH is ignored by the scale-up campaign", file=sys.stderr)
    return Campaign(a.campaign_id, parse_plan(a.plan), a.budget, a.min_delay).run()


if __name__ == "__main__":
    sys.exit(main())
