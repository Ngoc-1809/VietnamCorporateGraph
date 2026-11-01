"""Phase 6F tests (offline): compliance gate, per-source cap, identity bonus, HTTP-spacing gate, and the sequential 3-job campaign with a fake Pilot (no network,
no GPU). They prove orchestration/limits, not extraction quality."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar

import httpx
import pytest

from test_pilot import mk, sel, status
from vckg.crawlers.http import PoliteClient
from vckg.jobs import pilot as pl
from vckg.jobs import scaleup as su
from vckg.jobs.selection import (
    IdentityIndex,
    cleared_sources,
    identity_bonus,
    load_compliance,
    pick_next,
    slug_text,
)
from vckg.storage.sqlite import Staging


def test_compliance_file_clears_only_sources_without_consent_clauses():
    c = load_compliance(pl.COMPLIANCE_FILE)
    assert cleared_sources(c) == ["cafef", "vietstock"]
    assert cleared_sources(c, ["vneconomy", "baodautu", "cafef"]) == ["cafef"]
    for k in ("vneconomy", "baodautu"):
        assert c[k]["cleared"] is False and "NOT crawled" in c[k]["basis"]
    assert all(v["robots"]["url"].endswith("/robots.txt") and v["terms"]["urls"] for v in c.values())


def test_pilot_never_plans_or_fetches_uncleared_sources(tmp_path):
    from test_pilot import env as _env  # noqa: F401
    comp = {"cafef": {"cleared": True}, "baodautu": {"cleared": False}}
    st = Staging(tmp_path / "staging.sqlite")
    st.close()
    env = tmp_path
    asked = []

    def discover(n):
        return (sel([1, 2, 3], "cafef") + sel([4, 5, 6], "baodautu"), {"pool_new_unique": 6, "dup_of_staged": 0, "selected": 6, "topic_pool": {}})
    p = mk(env, [1], 3, discover=discover, compliance=comp, only=["cafef", "baodautu"])
    orig = p.discover_fn
    p.discover_fn = lambda *a: (asked.append(a[5]), orig(*a))[1]
    p.run()
    plan = json.loads((p.dir / "crawl_plan.json").read_text(encoding="utf-8"))
    assert asked == [["cafef"]] and plan["refused_sources"] == ["baodautu"]
    assert {c["source"] for c in plan["candidates"]} == {"cafef"}
    with pytest.raises(SystemExit):
        pl.Pilot("x", 1, pipe_dir=tmp_path / "p2", staging_db=tmp_path / "staging.sqlite", compliance={"baodautu": {"cleared": False}}, only=["baodautu"],
                 client_factory=lambda: None, sources_cfg={"sources": {}}, install_signals=False).run()


def test_pick_next_applies_identity_bonus_and_source_cap_with_fallback():
    rows = [{"url": f"https://x/{i}", "source": "a" if i < 4 else "b", "selection_score": 10 - i, "identity_bonus": 0} for i in range(6)]
    rows[5]["identity_bonus"] = identity_bonus(2)  # source b, low score but identity bonus 3.0 -> 8.0 beats a's 7 (i=3)
    assert pick_next(rows, {}, 3)["url"] == "https://x/0"
    assert pick_next([r for r in rows if r["source"] == "a"], {"a": 3}, 3)["cap_lifted"] is True  # only source a left: cap lifted and recorded
    mixed = pick_next(rows, {"a": 3}, 3)
    assert mixed["source"] == "b" and "cap_lifted" not in mixed  # source a is at its cap while b still has candidates
    top = pick_next([r for r in rows if r["source"] == "b"], {"a": 0}, 3)
    assert top["url"] == "https://x/5"  # bonus lifts it above https://x/4


def test_identity_index_ignores_tickers_generic_words_and_unverified(tmp_path):
    import sqlite3
    db = sqlite3.connect(tmp_path / "r.sqlite")
    db.executescript("CREATE TABLE entities(entity_id TEXT, entity_type TEXT, resolution_status TEXT, merged_into TEXT); CREATE TABLE aliases(entity_id TEXT, alias_key TEXT);")
    db.executemany("INSERT INTO entities VALUES(?,?,?,?)", [("org:v", "ORGANIZATION", "VERIFIED", None), ("org:p", "ORGANIZATION", "PROVISIONAL", None), ("org:g", "ORGANIZATION", "VERIFIED", None)])
    db.executemany("INSERT INTO aliases VALUES(?,?)", [("org:v", "vinhomes"), ("org:v", "vic"), ("org:p", "alphabet"), ("org:g", "viet nam"), ("org:g", "hoa phat")])
    db.commit()
    db.close()
    ix = IdentityIndex(tmp_path / "r.sqlite")
    assert ix.matches("Vinhomes phát hành trái phiếu, VIC tăng giá") == ["vinhomes"]
    assert ix.matches("Alphabet và Việt Nam") == []
    assert ix.matches("Hòa Phát mua lại") == ["hoa phat"]
    assert slug_text("https://cafef.vn/becamex-bo-nhiem-ceo-18826102414452399.chn") == "becamex bo nhiem ceo"


def test_spacing_violation_fails_the_job_before_processing(tmp_path):
    env = tmp_path
    Staging(env / "staging.sqlite").close()
    p = mk(env, [1, 2], 2, compliance=None, min_delay=2.0)

    from test_pilot import html

    def handler2(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:\n")
        i = int(req.url.path.rsplit("-", 1)[-1].split(".")[0])
        return httpx.Response(200, content=html(i).encode(), headers={"content-type": "text/html; charset=utf-8"})
    p.client_factory = lambda: PoliteClient("bot", 0.0, 5.0, 0, 1.0, transport=httpx.MockTransport(handler2), sleep=lambda s: None, request_log=p.dir / "http_requests.jsonl")
    code = p.run()
    s = status(p)
    assert code == 6 and s["state"] == "FAILED" and s["http_spacing_ok"] is False and "spacing" in s["last_error"]
    assert s.get("succeeded_articles") in (None, 0)  # NLP never started


# ------------------------------------------------------------------------------------------------ campaign
class FakePilot:
    log: ClassVar[list] = []
    qwen_per_job: ClassVar[int] = 30
    behave: ClassVar[dict] = {}

    def __init__(self, pipe: Path, job, target, left):
        self.pipe, self.job, self.target, self.left = pipe, job, target, left

    def run(self):
        FakePilot.log.append((self.job, self.target, self.left))
        d = self.pipe / self.job
        d.mkdir(parents=True, exist_ok=True)
        b = FakePilot.behave.get(self.job, {})
        ids = [f"{self.job}-{i}" for i in range(self.target)] if "overlap" not in b else ["scale01-0"]
        (d / "manifest.jsonl").write_text("\n".join(json.dumps({"article_id": i}) for i in ids), encoding="utf-8")
        st = {"state": b.get("state", "COMPLETED"), "fetched_ok": len(ids), "total_articles": len(ids), "succeeded_articles": len(ids) - b.get("failed", 0), "failed_articles": b.get("failed", 0),
              "llm_calls": min(self.qwen_per_job, self.left), "http_spacing_ok": True, "qa_pass": 1, "qa_quarantine": 2, "qa_reject": 0, "stop_reason": b.get("stop_reason")}
        (d / "status.json").write_text(json.dumps(st), encoding="utf-8")
        return 0


def camp(tmp_path, **kw):
    FakePilot.log, FakePilot.behave, FakePilot.qwen_per_job = [], {}, 30
    called = []
    c = su.Campaign("camp", pipe_dir=tmp_path, pilot_factory=lambda j, n, left: FakePilot(tmp_path, j, n, left), aggregate_fn=lambda jobs: called.append(list(jobs)) or {"content_hash": "h"},
                    install_signals=False, **kw)
    c.called = called
    return c


def cstatus(c):
    return json.loads((c.dir / "status.json").read_text(encoding="utf-8"))


def test_campaign_limits_are_hard():
    for plan in ([("a", 21)], [("a", 20), ("b", 20), ("c", 11)], [("a", 0)]):
        with pytest.raises(SystemExit):
            su.Campaign("x", plan=plan)
    with pytest.raises(SystemExit):
        su.Campaign("x", budget=161)


def test_three_jobs_run_sequentially_with_shrinking_budget_then_aggregate(tmp_path):
    c = camp(tmp_path)
    assert c.run() == 0
    assert FakePilot.log == [("scale01", 20, 160), ("scale02", 20, 130), ("scale03", 10, 100)]
    s = cstatus(c)
    assert s["state"] == "COMPLETED" and s["qwen_used"] == 90 and s["llm_calls"] == 90 and c.called == [["scale01", "scale02", "scale03"]] and s["completed_jobs"] == ["scale01", "scale02", "scale03"]
    assert not (c.dir / "worker.lock").exists()


def test_failed_job_stops_the_campaign_and_later_jobs_never_start(tmp_path):
    c = camp(tmp_path)
    FakePilot.behave = {"scale02": {"failed": 1}}
    assert c.run() == 4
    s = cstatus(c)
    assert s["state"] == "FAILED" and [x[0] for x in FakePilot.log] == ["scale01", "scale02"] and "failed" in s["last_error"] and c.called == []  # serious data error: nothing is aggregated automatically
    assert s["failed_job"] == "scale02"


def test_budget_exhaustion_stops_safely_and_keeps_completed_work(tmp_path):
    c = camp(tmp_path, budget=50)
    FakePilot.qwen_per_job = 30
    FakePilot.behave = {"scale02": {"state": "STOPPED", "stop_reason": "BUDGET"}}
    assert c.run() == 3
    s = cstatus(c)
    assert s["state"] == "STOPPED" and s["stop_reason"] == "BUDGET" and [x[0] for x in FakePilot.log] == ["scale01", "scale02"] and c.called == [["scale01"]]
    assert FakePilot.log[1][2] == 20  # 50 - 30 passed on as the remaining budget


def test_resume_skips_completed_jobs_and_overlap_with_earlier_job_is_a_data_error(tmp_path):
    c = camp(tmp_path)
    c.run()
    FakePilot.log.clear()
    c2 = camp(tmp_path)
    FakePilot.log.clear()
    assert c2.run() == 0 and FakePilot.log == []  # nothing re-run
    assert cstatus(c2)["jobs"]["scale02"]["skipped_already_completed"] is True
    d = tmp_path / "t2"
    c3 = camp(d)
    FakePilot.behave = {"scale02": {"overlap": True}}
    assert c3.run() == 4 and "overlap" in cstatus(c3)["last_error"]


def test_stop_file_propagates_to_the_running_job_and_prevents_next_jobs(tmp_path):
    c = camp(tmp_path)
    orig = FakePilot.run

    def run_and_stop(self):
        c._request_stop("STOP_FILE")  # what the mirror thread does when the campaign STOP file appears
        assert (tmp_path / self.job / "STOP").exists()
        FakePilot.behave[self.job] = {"state": "STOPPED", "stop_reason": "STOP_FILE"}
        return orig(self)
    FakePilot.run = run_and_stop
    try:
        assert c.run() == 0
    finally:
        FakePilot.run = orig
    assert cstatus(c)["state"] == "STOPPED" and [x[0] for x in FakePilot.log] == ["scale01"]


def test_campaign_lock_blocks_duplicate_campaign(tmp_path):
    c = camp(tmp_path)
    c.dir.mkdir(parents=True)
    (c.dir / "worker.lock").write_text(json.dumps({"pid": os.getpid()}))
    assert c.run() == 5 and FakePilot.log == []
