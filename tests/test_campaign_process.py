"""Mass campaign: chunked NLP processor and supervisor (offline; FakeNER/FakeLLM doubles from the 6C tests prove orchestration, budget, deferral, isolation, resume and
supervision - not extraction quality)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from test_pipeline_worker import TEXTS, FakeLLM, FakeNER
from vckg.campaign import process as prc
from vckg.campaign import supervisor as sup
from vckg.campaign.queue import Queue
from vckg.entity_linking.resolver import EntityResolver
from vckg.entity_linking.store import RegistryStore
from vckg.jobs.stages import Runtime
from vckg.relation_extraction.candidates import load_relations
from vckg.storage.sqlite import Staging

REL = Path(__file__).resolve().parents[1] / "config/relations.yaml"


def build(tmp_path: Path, n: int, score=lambda i: 10 - i * 0.01):
    master = Staging(tmp_path / "master.sqlite")
    camp = tmp_path / "camp"
    q = Queue(camp / "queue.sqlite")
    texts = list(TEXTS.values())
    for i in range(n):
        url = f"https://cafef.vn/bai-{i}-188260000{i:05d}.chn"
        _, art = master.add_article(url, "cafef", f"Bài {i}", texts[i % 3] + f" Bài số {i} có nội dung riêng biệt để không trùng.", None)
        q.add_discovered([{"url": url, "source": "cafef", "slug": "x", "score": score(i), "topic": "board", "via": "t"}])
        q.mark_crawl(url, "fetched", http_status=200)
        q.mark_parse(url, "ok", article_id=art.article_id, content_hash=art.content_hash, chars=100)
    seed = RegistryStore(tmp_path / "seed.sqlite")
    seed.db.commit()
    (camp / "acquire_status.json").write_text(json.dumps({"state": "COMPLETED", "pid": 1}), encoding="utf-8")
    return q


def processor(tmp_path, ner=None, llm=None, **kw):
    ner = ner or FakeNER()

    def mk(job_dir, registry, staging_db, llm_enabled):
        store = RegistryStore(registry)
        return Runtime(store, EntityResolver(store), load_relations(str(REL)), ner, llm or FakeLLM(), staging_db)
    calls = []
    kw.setdefault("aggregate_fn", lambda chunks, n: calls.append((list(chunks), n)) or {"content_hash": "h"})
    p = prc.Processor(tmp_path / "camp", chunk_size=kw.pop("chunk_size", 2), pipe_dir=tmp_path / "pipe", master_staging=tmp_path / "master.sqlite", seed_registry=tmp_path / "seed.sqlite",
                      make_runtime=mk, idle_sleep=0.05, install_signals=False, min_chunk=1, worker_kwargs={"backoff_s": 0.0}, error_sleep=0.05, **kw)
    p.agg_calls = calls
    return p


def pstatus(tmp_path):
    return json.loads((tmp_path / "camp" / "process_status.json").read_text(encoding="utf-8"))


def test_chunks_are_bounded_ordered_by_score_aggregated_and_registry_is_chained(tmp_path):
    q = build(tmp_path, 5)
    p = processor(tmp_path)
    assert p.run() == 0
    s = pstatus(tmp_path)
    assert s["state"] == "COMPLETED" and s["articles_done"] == 5 and s["articles_failed"] == 0 and s["backlog"] == 0
    assert [c for c, _ in p.agg_calls] == [["camp-c00001"], ["camp-c00002"], ["camp-c00003"]]
    q2 = Queue(tmp_path / "camp" / "queue.sqlite")
    assert q2.counts()["nlp"] == {"done": 5} and q2.db.execute("SELECT COUNT(*) FROM chunks WHERE status='finished'").fetchone()[0] == 3
    first = [r["url"] for r in q2.chunk_rows("camp-c00001")]
    assert first == [f"https://cafef.vn/bai-{i}-188260000{i:05d}.chn" for i in (0, 1)]  # highest score first
    import sqlite3
    cs = sqlite3.connect(tmp_path / "pipe" / "camp-c00001" / "staging.sqlite")
    assert cs.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 2  # the chunk only sees its own rows
    assert (tmp_path / "camp" / "registry_cumulative.sqlite").exists() and (tmp_path / "pipe" / "camp-c00003" / "registry.sqlite").exists()
    assert q.counts()["nlp"] == {"done": 5}


def test_batch_ceiling_of_the_worker_is_raised_only_to_the_chunk_size(tmp_path):
    build(tmp_path, 25)
    p = processor(tmp_path, chunk_size=25)
    assert p.run() == 0 and pstatus(tmp_path)["articles_done"] == 25
    with pytest.raises(SystemExit):
        prc.Processor(tmp_path / "camp", chunk_size=501)
    with pytest.raises(SystemExit):
        prc.Processor(tmp_path / "camp", qwen_budget=90001)


def test_rerun_does_not_reprocess_done_articles(tmp_path):
    build(tmp_path, 4)
    ner = FakeNER()
    p = processor(tmp_path, ner=ner)
    p.run()
    n = ner.calls
    p2 = processor(tmp_path, ner=ner)
    assert p2.run() == 0 and ner.calls == n and p2.agg_calls == []


def test_failed_article_is_isolated_and_the_run_is_reported_incomplete(tmp_path):
    q = build(tmp_path, 4)
    p = processor(tmp_path, ner=FakeNER(fail_for="Bài số 2 "))
    assert p.run() == 0
    s = pstatus(tmp_path)
    nlp = Queue(tmp_path / "camp" / "queue.sqlite").counts()["nlp"]
    assert s["state"] == "INCOMPLETE" and nlp == {"done": 3, "failed": 1}
    assert q.db.execute("SELECT nlp_error FROM urls WHERE nlp_status='failed'").fetchone()[0].startswith("RuntimeError")


def test_qwen_budget_exhaustion_defers_unfinished_work_and_never_marks_it_done(tmp_path):
    build(tmp_path, 6)
    p = processor(tmp_path, qwen_budget=2)
    assert p.run() == 3
    s = pstatus(tmp_path)
    nlp = Queue(tmp_path / "camp" / "queue.sqlite").counts()["nlp"]
    assert s["state"] == "INCOMPLETE" and s["stop_reason"] == "BUDGET_EXHAUSTED"
    assert nlp.get("done", 0) <= 2 and nlp["deferred"] == 6 - nlp.get("done", 0) and "pending" not in nlp and "chunked" not in nlp
    assert s["qwen_used"] <= 2  # the cap is exact across the whole campaign


def test_open_chunk_is_resumed_not_recreated_and_stop_ends_stopped(tmp_path):
    q = build(tmp_path, 4)
    q.take_chunk("camp-c00001", 2)  # a chunk that was reserved before a crash
    p = processor(tmp_path)
    assert p.run() == 0
    assert q.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 2 and next(c for c, _ in p.agg_calls) == ["camp-c00001"]
    q2 = build(tmp_path / "t2", 3)
    (tmp_path / "t2" / "camp" / "STOP").write_text("x")
    (tmp_path / "t2" / "camp" / "acquire_status.json").write_text(json.dumps({"state": "RUNNING", "pid": os.getpid()}))
    p2 = processor(tmp_path / "t2")
    assert p2.run() == 0 and pstatus(tmp_path / "t2")["state"] == "STOPPED" and q2.counts()["nlp"] == {"pending": 3}


def test_processor_waits_for_acquisition_when_the_queue_is_empty_and_lock_is_exclusive(tmp_path):
    build(tmp_path, 0)
    (tmp_path / "camp" / "acquire_status.json").write_text(json.dumps({"state": "RUNNING", "pid": os.getpid()}))
    p = processor(tmp_path)
    p.idle_sleep = 0.05
    import threading
    threading.Timer(0.5, lambda: (tmp_path / "camp" / "STOP").write_text("x")).start()
    assert p.run() == 0 and pstatus(tmp_path)["state"] == "STOPPED"
    (tmp_path / "camp" / "process.lock").write_text(json.dumps({"pid": os.getpid()}))
    assert processor(tmp_path).run() == 5


# ------------------------------------------------------------------------------------------------ supervisor
def write_child(camp: Path, which: str, **kw):
    base = {"state": "RUNNING", "pid": os.getpid(), "heartbeat_at": time.strftime("%Y-%m-%dT%H:%M:%S") + "+07:00"}
    from datetime import datetime
    base["heartbeat_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    (camp / f"{which}_status.json").write_text(json.dumps({**base, **kw}), encoding="utf-8")


def make_sup(tmp_path, **kw):
    launched, olla = [], []
    ollama_ok = kw.pop("ollama", True)
    s = sup.Supervisor(tmp_path / "camp", launch=lambda name, cmd: launched.append((name, cmd)) or True, ollama_check=lambda: ollama_ok, ollama_start=lambda: olla.append(1),
                       pipe_dir=tmp_path / "pipe", agg_dir=tmp_path / "agg", report_dir=tmp_path / "rep", final_report=tmp_path / "final.md", tick=0.05, install_signals=False,
                       finalize_fn=lambda: None, neo4j_fn=kw.pop("neo4j_fn", lambda: {"idempotent": True}), watchdog_remove=lambda: olla.append("wd"), **kw)
    s.launched, s.olla = launched, olla
    return s


def test_supervisor_launches_children_once_restarts_dead_ones_and_respects_limits(tmp_path):
    (tmp_path / "camp").mkdir(parents=True)
    s = make_sup(tmp_path)
    assert s.ensure("acquire", True) == "launched" and s.ensure("acquire", True) == "backoff"
    assert "vckg.campaign.acquire run" in s.launched[0][1] and "--max-new 30000" in s.launched[0][1] and s.launched[0][0] == "mass-acquire"
    write_child(tmp_path / "camp", "acquire")
    assert s.ensure("acquire", True) == "ok"  # healthy
    write_child(tmp_path / "camp", "acquire", pid=999999)  # died without a terminal state
    s.last_launch["acquire"] = 0
    assert s.ensure("acquire", True) == "launched"
    write_child(tmp_path / "camp", "acquire", state="COMPLETED", pid=999999)
    assert s.ensure("acquire", True) == "ok"  # finished work is not restarted
    write_child(tmp_path / "camp", "acquire", state="STOPPED", pid=999999)  # stopped without a STOP request (console closed)
    s.last_launch["acquire"] = 0
    assert s.ensure("acquire", True) == "relaunched"
    write_child(tmp_path / "camp", "acquire", state="FAILED", pid=999999, last_error="HTTP spacing violations: 3")
    s.last_launch["acquire"] = 0
    assert s.ensure("acquire", True) == "ok"  # a rate-limit breach is never retried automatically
    write_child(tmp_path / "camp", "process", state="FAILED", pid=999999, last_error="x")
    s.last_launch["process"] = 0
    assert s.ensure("process", True) == "relaunched"
    s2 = make_sup(tmp_path / "o", ollama=False)
    assert s2.ensure("process", True) == "waiting_ollama" and not s2.launched  # the NLP worker is never started while Ollama is down
    assert s.ensure("process", False) in ("ok", "waiting")


def test_supervisor_final_state_is_incomplete_when_work_is_unfinished_and_completed_only_when_clean(tmp_path):
    camp = tmp_path / "camp"
    q = build(tmp_path, 3)
    for i in range(3):
        q.db.execute("UPDATE urls SET nlp_status='done' WHERE rowid=?", (i + 1,))
    q.db.execute("UPDATE urls SET nlp_status='deferred' WHERE rowid=3")
    q.db.commit()
    write_child(camp, "acquire", state="COMPLETED", pid=999999, shortfall=29997)
    write_child(camp, "process", state="INCOMPLETE", pid=999999, stop_reason="BUDGET_EXHAUSTED")
    s = make_sup(tmp_path)
    assert s.run() == 3
    st = json.loads((camp / "status.json").read_text(encoding="utf-8"))
    assert st["state"] == "INCOMPLETE" and any("deferred" in r for r in st["incomplete_reasons"]) and st["shortfall"] == 29997
    assert (tmp_path / "final.md").exists() and "INCOMPLETE" in (tmp_path / "final.md").read_text(encoding="utf-8") and "wd" in s.olla  # watchdog task removed at the end
    # clean run
    t2 = tmp_path / "t2"
    q2 = build(t2, 2)
    q2.db.execute("UPDATE urls SET nlp_status='done'")
    q2.db.commit()
    write_child(t2 / "camp", "acquire", state="COMPLETED", pid=999999, shortfall=0)
    write_child(t2 / "camp", "process", state="COMPLETED", pid=999999)
    s2 = make_sup(t2)
    assert s2.run() == 0 and json.loads((t2 / "camp" / "status.json").read_text(encoding="utf-8"))["state"] == "COMPLETED"


def test_supervisor_writes_kpis_periodic_summaries_and_handles_neo4j_blocker(tmp_path):
    camp = tmp_path / "camp"
    q = build(tmp_path, 4)
    q.db.execute("UPDATE urls SET nlp_status='done'")
    q.db.commit()
    write_child(camp, "acquire", state="COMPLETED", pid=999999, shortfall=0)
    write_child(camp, "process", state="COMPLETED", pid=999999)

    def blocked():
        raise RuntimeError("BLOCKED: backup could not be verified")
    s = make_sup(tmp_path, summary_every=2, neo4j_fn=blocked)
    assert s.run() == 0
    st = json.loads((camp / "status.json").read_text(encoding="utf-8"))
    for k in ("articles_discovered", "articles_downloaded", "articles_parsed", "articles_processed", "articles_deferred", "articles_failed", "by_publisher", "by_topic", "chunk_totals", "disk", "ollama_up", "acquire", "process"):
        assert k in st
    assert (tmp_path / "rep" / "summary_000004.json").exists() or (tmp_path / "rep" / "summary_000002.json").exists()
    assert (tmp_path / "rep" / "summary_final.md").exists() and "NOT precision" in (tmp_path / "rep" / "summary_final.md").read_text(encoding="utf-8")
    assert "BLOCKED" in (st.get("neo4j_blocker") or "") and st["state"] == "COMPLETED"  # a Neo4j blocker never stops the accumulation of the SQLite/GraphML graph


def test_budget_exhaustion_stops_acquisition_and_stop_file_ends_the_campaign(tmp_path):
    camp = tmp_path / "camp"
    build(tmp_path, 2)
    write_child(camp, "acquire", state="RUNNING")
    write_child(camp, "process", state="INCOMPLETE", pid=999999, stop_reason="BUDGET_EXHAUSTED")
    s = make_sup(tmp_path)
    s.tick = 0.05
    import threading

    def later():
        time.sleep(2.0)
        write_child(camp, "acquire", state="STOPPED", pid=999999)
    threading.Thread(target=later).start()
    (camp / "STOP").write_text("x")
    assert s.run() in (0, 3)
    assert (camp / "acquire.STOP").exists()
    assert json.loads((camp / "status.json").read_text(encoding="utf-8"))["state"] in ("STOPPED", "INCOMPLETE")


def test_supervisor_enforces_hard_limits_and_single_instance(tmp_path):
    with pytest.raises(SystemExit):
        sup.Supervisor(tmp_path / "c", max_articles=30001)
    with pytest.raises(SystemExit):
        sup.Supervisor(tmp_path / "c", qwen_budget=90001)
    s = make_sup(tmp_path)
    (tmp_path / "camp" / "supervisor.lock").write_text(json.dumps({"pid": os.getpid()}))
    assert s.run() == 5

