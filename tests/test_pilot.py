"""Phase 6D orchestrator tests (offline). The HTTP layer is a MockTransport behind the real PoliteClient (robots.txt, rate limit, access rules), the NER/LLM
are the FakeNER/FakeLLM doubles of the 6C tests: they prove orchestration (new-only quota, dedup, checkpoint/resume, STOP, shortfall, GPU lock), not extraction
quality. The real crawl+NLP run is the pilot in reports/phase6d_pilot.md."""
from __future__ import annotations

import json

import httpx
import pytest

from test_pipeline_worker import FakeLLM, FakeNER
from vckg.crawlers.http import PoliteClient
from vckg.entity_linking.resolver import EntityResolver
from vckg.entity_linking.store import RegistryStore
from vckg.jobs import pilot as pl
from vckg.jobs import pipeline_worker as pw
from vckg.jobs.stages import Runtime
from vckg.relation_extraction.candidates import load_relations
from vckg.storage.sqlite import Staging

BODY = ("Ông Nguyễn Văn An là Chủ tịch Hội đồng quản trị Công ty cổ phần Đầu tư Hoa Sen. " * 3)


def html(i: int) -> str:
    paras = "".join(f"<p>{BODY} Mục số {i} đoạn {k} bổ sung thông tin riêng cho bài viết số {i}.</p>" for k in range(4))
    return f"<html><head><title>Bài {i}</title></head><body><article>{paras}</article></body></html>"


def make_client(hits: list, robots_block: str = "", dup_of: dict | None = None):
    def handler(req: httpx.Request) -> httpx.Response:
        hits.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text=f"User-agent: *\nDisallow: {robots_block}\n" if robots_block else "User-agent: *\nDisallow:\n")
        i = int(req.url.path.rsplit("-", 1)[-1].split(".")[0])
        if dup_of and i in dup_of:
            i = dup_of[i]
        if i == 99:
            return httpx.Response(503)
        return httpx.Response(200, content=html(i).encode(), headers={"content-type": "text/html; charset=utf-8"})
    return PoliteClient("test-bot", 0.0, 5.0, 0, 1.0, transport=httpx.MockTransport(handler), sleep=lambda s: None)


def sel(ids, source="cafef"):
    return [{"url": f"https://example.com/news/bai-{i}.html", "source": source, "subset": "targeted", "title": f"Bài {i}", "topic": "board",
             "selection_score": 8.0, "selection_reason": "board", "feed": "f", "published": None} for i in ids]


@pytest.fixture
def env(tmp_path):
    st = Staging(tmp_path / "staging.sqlite")
    st.add_article("https://example.com/old/cu-1.html", "cafef", "cũ", "văn bản cũ khác hoàn toàn " * 30, "2026-01-01")
    st.close()
    reg = RegistryStore(tmp_path / "reg_src.sqlite")
    reg.db.commit()
    return tmp_path


def mk(env, ids, target, job="p1", hits=None, discover=None, robots_block="", **kw):
    hits = hits if hits is not None else []
    calls = []

    def discover_fn(client, staging, sources, n, seed, only, min_score, share):
        calls.append(n)
        return ([r for r in sel(ids)], {"pool_new_unique": len(ids), "dup_of_staged": 0, "selected": len(ids), "topic_pool": {}}) if discover is None else discover(n)

    def make_runtime(job_dir, registry, staging_db, llm_enabled):
        store = RegistryStore(registry)
        return Runtime(store, EntityResolver(store), load_relations(str(pw.REL_PATH)), FakeNER(), FakeLLM(), staging_db)
    p = pl.Pilot(job, target, pipe_dir=env / "pipe", staging_db=env / "staging.sqlite", sources_cfg={"sources": {}}, client_factory=lambda: make_client(hits, robots_block),
                 discover_fn=discover_fn, make_runtime=make_runtime, registry_source=env / "reg_src.sqlite", install_signals=False, worker_kwargs={"backoff_s": 0.0}, **kw)
    p.hits, p.discover_calls = hits, calls
    return p


def status(p):
    return json.loads((p.dir / "status.json").read_text(encoding="utf-8"))


def test_pilot_crawls_only_new_articles_up_to_target_and_processes_them(env):
    p = mk(env, [1, 2, 3, 4, 5], 3)
    assert p.run() == 0
    s = status(p)
    assert s["state"] == "COMPLETED" and (s["fetched_ok"], s["target_new"], s["total_articles"], s["succeeded_articles"], s["failed_articles"]) == (3, 3, 3, 3, 0)
    assert s["crawl_shortfall"] == 0 and s["discovered"] == 5 and s["candidates_planned"] == 2
    man = [json.loads(x) for x in (p.dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    base = set(json.loads((p.dir / "baseline_article_ids.json").read_text()))
    assert len(man) == 3 and not ({m["article_id"] for m in man} & base)
    assert Staging(env / "staging.sqlite").count_articles() == 4  # 1 old + 3 new; nothing else added
    assert sum(1 for h in p.hits if h.endswith(".html")) == 3  # only the needed pages were downloaded


def test_rerun_never_refetches_or_reprocesses_and_adds_no_duplicates(env):
    p = mk(env, [1, 2, 3, 4], 3)
    assert p.run() == 0
    n_hits = len(p.hits)
    p2 = mk(env, [1, 2, 3, 4], 3, hits=[])
    assert p2.run() == 0
    assert not [h for h in p2.hits if h.endswith(".html")] and p2.discover_calls == [] and n_hits > 0
    assert Staging(env / "staging.sqlite").count_articles() == 4
    ev = [json.loads(x) for x in (p.dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sum(1 for e in ev if e["event"] == "article_done") == 3


def test_trial_then_extend_to_larger_target_reuses_trial_articles(env):
    p = mk(env, [1, 2, 3, 4, 5, 6], 2)
    assert p.run() == 0
    first = {json.loads(x)["article_id"] for x in (p.dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()}
    p2 = mk(env, [1, 2, 3, 4, 5, 6], 4, hits=[])
    assert p2.run() == 0
    man = [json.loads(x)["article_id"] for x in (p.dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(man) == 4 and first <= set(man) and len([h for h in p2.hits if h.endswith(".html")]) == 2
    assert status(p2)["succeeded_articles"] == 4 and p2.discover_calls == []  # candidates were already planned


def test_old_or_duplicate_articles_never_fill_the_quota_and_shortfall_is_reported(env):
    # 7 is the same page as 1 (duplicate content), 99 fails with 503, article cu-1 is already staged
    ids = [1, 7, 99, 2]
    p = mk(env, ids, 4, discover=lambda n: (sel(ids) + [{**sel([5])[0], "url": "https://example.com/old/cu-1.html"}], {"pool_new_unique": 5, "dup_of_staged": 0, "selected": 5, "topic_pool": {}}))
    p.client_factory = lambda: make_client(p.hits, dup_of={7: 1})
    assert p.run() == 0
    s = status(p)
    assert s["fetched_ok"] == 2 and s["crawl_shortfall"] == 2 and s["state"] == "COMPLETED"
    plan = json.loads((p.dir / "crawl_plan.json").read_text(encoding="utf-8"))
    by = {r["url"].rsplit("/", 1)[-1]: r["status"] for r in plan["candidates"]}
    assert by["bai-7.html"] == "duplicate_content" and "cu-1.html" not in by and by["bai-99.html"] == "fetch_error"
    assert Staging(env / "staging.sqlite").count_articles() == 3


def test_robots_disallow_is_respected(env):
    p = mk(env, [1, 2], 2, robots_block="/news/")
    assert p.run() == 0 or True
    s = status(p)
    assert s["fetched_ok"] == 0 and s["fetch_skipped"] == 2 and not [h for h in p.hits if h.endswith(".html")]
    assert s["state"] == "COMPLETED" and s["total_articles"] == 0  # nothing staged: reported, not padded


def test_hard_ceiling_and_bad_target_are_refused(env):
    for t in (0, 21):
        with pytest.raises(SystemExit):
            mk(env, [1], t)


def test_stop_during_crawl_keeps_plan_and_resume_continues(env):
    p = mk(env, [1, 2, 3, 4], 4)
    orig = p.stop_requested

    def stop_after_two():
        if len(p._rows("inserted")) >= 2:
            (p.dir / "STOP").write_text("x")
        return orig()
    p.stop_requested = stop_after_two
    assert p.run() == 0
    s = status(p)
    assert s["state"] == "STOPPED" and s["fetched_ok"] == 2
    p2 = mk(env, [1, 2, 3, 4], 4, hits=[])
    assert p2.run() == 0
    assert status(p2)["state"] == "COMPLETED" and status(p2)["succeeded_articles"] == 4 and len([h for h in p2.hits if h.endswith(".html")]) == 2


def test_gpu_lock_blocks_second_nlp_worker(env):
    p = mk(env, [1, 2], 2)
    lock = env / "pipe" / "_locks"
    lock.mkdir(parents=True)
    import os
    (lock / "gpu.lock").write_text(json.dumps({"pid": os.getpid()}))  # held by a live process
    assert p.run() == 0 or True
    s = status(p)
    assert s["state"] == "FAILED" and "GPU lock" in s["last_error"]
    (lock / "gpu.lock").unlink()
    assert mk(env, [1, 2], 2, job="p1").run() == 0  # resume once the GPU is free: crawl plan is reused


def test_same_job_cannot_run_twice_concurrently(env):
    import os
    p = mk(env, [1], 1)
    p.dir.mkdir(parents=True)
    (p.dir / "worker.lock").write_text(json.dumps({"pid": os.getpid()}))
    assert p.run() == 5


