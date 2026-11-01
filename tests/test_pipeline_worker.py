"""Phase 6C worker tests (offline). Backends are test doubles (FakeNER / FakeLLM): they prove the ORCHESTRATION (checkpoint, resume, isolation, budget,
locking, status, idempotent staging), NOT GLiNER/Qwen quality. The real-model run is the smoke test in reports/phase6c_report.md."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import pytest

from vckg.entity_linking.resolver import EntityResolver
from vckg.entity_linking.store import RegistryStore
from vckg.jobs import pipeline_worker as pw
from vckg.jobs.stages import CachedNER, Runtime
from vckg.models import EntityType, Mention
from vckg.relation_extraction.candidates import load_relations
from vckg.relation_extraction.llm_discovery import BudgetExceeded, DiscoveryStats
from vckg.storage.sqlite import Staging

TEXTS = {
    "a1": "Ông Nguyễn Văn An là Chủ tịch Hội đồng quản trị Công ty cổ phần Đầu tư Hoa Sen. Công ty cổ phần Đầu tư Hoa Sen công bố kết quả kinh doanh quý ba.",
    "a2": "Bà Trần Thị Bình giữ chức Tổng giám đốc Công ty cổ phần Thép Phương Nam từ năm 2020. Công ty cổ phần Thép Phương Nam tăng vốn điều lệ.",
    "a3": "Ngân hàng Nhà nước yêu cầu Công ty cổ phần Vận tải Biển Đông báo cáo. Công ty cổ phần Vận tải Biển Đông cho biết sẽ hoàn thành sớm.",
}
SPEC = {"Nguyễn Văn An": EntityType.PERSON, "Trần Thị Bình": EntityType.PERSON, "Công ty cổ phần Đầu tư Hoa Sen": EntityType.ORGANIZATION,
        "Công ty cổ phần Thép Phương Nam": EntityType.ORGANIZATION, "Công ty cổ phần Vận tải Biển Đông": EntityType.ORGANIZATION}


class FakeNER:
    def __init__(self, fail_for: str | None = None, flaky: dict | None = None):
        self.calls, self.fail_for, self.flaky = 0, fail_for, flaky if flaky is not None else {}

    def extract_sentences(self, text, sentences):
        self.calls += 1
        if self.fail_for and self.fail_for in text:
            raise RuntimeError("boom (injected)")
        for k in list(self.flaky):
            if k in text and self.flaky[k] > 0:
                self.flaky[k] -= 1
                raise RuntimeError("transient (injected)")
        out = []
        for surface, label in SPEC.items():
            i = text.find(surface)
            while i != -1:
                out.append(Mention(text=surface, start=i, end=i + len(surface), label=label, ner_score=0.9, method="test_double"))
                i = text.find(surface, i + 1)
        return sorted(out, key=lambda m: (m.start, -m.end))


class FakeLLM:
    model, prompt_version = "fake-qwen", "fake"

    def __init__(self, fail: bool = False):
        self.stats, self.max_live, self.fail = DiscoveryStats(), 10**6, fail

    def discover(self, title, passage, mentions):
        if self.stats.calls >= self.max_live:
            raise BudgetExceeded("cap")
        self.stats.calls += 1
        if self.fail:
            self.stats.failures += 1
            return None
        return {"parsed": {"relations": []}, "cached": False, "usage": {}}


@pytest.fixture
def env(tmp_path):
    st = Staging(tmp_path / "staging.sqlite")
    ids = {}
    for k, t in TEXTS.items():
        _, a = st.add_article(f"https://example.com/{k}", "test", k, t, "2026-01-01")
        ids[k] = a.article_id
    st.close()
    return tmp_path, ids


def make_worker(env, ids, keys=("a1", "a2", "a3"), job="j1", ner=None, llm="default", **kw):
    tmp, _ = env
    manifest = [{"article_id": ids[k], "url": f"https://example.com/{k}", "source": "test", "subset": "targeted"} for k in keys]
    jd = tmp / "pipe" / job
    jd.mkdir(parents=True, exist_ok=True)
    store = RegistryStore(jd / "registry.sqlite")
    ner = ner or FakeNER()
    llm = FakeLLM() if llm == "default" else llm
    rt = Runtime(store, EntityResolver(store), load_relations(str(pw.REL_PATH)), ner, llm, tmp / "staging.sqlite")
    kw.setdefault("backoff_s", 0.0)
    w = Worker_(job, manifest, rt, tmp, **kw)
    w.ner, w.llm_obj = ner, llm
    return w


def Worker_(job, manifest, rt, tmp, **kw):
    return pw.Worker(job, manifest, rt=rt, pipe_dir=tmp / "pipe", staging_db=tmp / "staging.sqlite", install_signals=False, **kw)


def events(w, name):
    p = w.dir / "events.jsonl"
    return [e for e in (json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()) if e["event"] == name] if p.exists() else []


def status(w):
    return json.loads((w.dir / "status.json").read_text(encoding="utf-8"))


def test_batch_completes_and_status_is_machine_readable(env):
    w = make_worker(env, env[1])
    assert w.run() == 0
    s = status(w)
    assert s["state"] == "COMPLETED" and s["pid"] == os.getpid()
    assert (s["total_articles"], s["processed_articles"], s["succeeded_articles"], s["failed_articles"]) == (3, 3, 3, 0)
    for k in pw.Status.FIELDS:
        assert k in s
    assert s["started_at"] and s["finished_at"] and s["heartbeat_at"]
    assert (w.dir / "summary.json").exists() and not (w.dir / "worker.lock").exists()


def test_rerun_is_idempotent_no_reprocessing_no_duplicates(env):
    w = make_worker(env, env[1])
    assert w.run() == 0
    n_ner = w.ner.calls
    db = pw.JobStore(w.dir / "pipeline.sqlite")
    snap = (db.db.execute("SELECT COUNT(*) FROM staging_edges").fetchone()[0], db.db.execute("SELECT COUNT(*) FROM staging_evidence").fetchone()[0],
            RegistryStore(w.dir / "registry.sqlite").stats()["entities_active"])
    w2 = make_worker(env, env[1])
    assert w2.run() == 0
    assert w2.ner.calls == 0 and n_ner > 0  # nothing re-processed
    assert len(events(w2, "article_done")) == len(events(w, "article_done")) == 3 and events(w2, "pending")[-1]["n"] == 0
    db2 = pw.JobStore(w.dir / "pipeline.sqlite")
    assert snap == (db2.db.execute("SELECT COUNT(*) FROM staging_edges").fetchone()[0], db2.db.execute("SELECT COUNT(*) FROM staging_evidence").fetchone()[0],
                    RegistryStore(w.dir / "registry.sqlite").stats()["entities_active"])
    assert db2.db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 3


def test_one_failing_article_never_fails_silently_and_never_aborts_batch(env):
    w = make_worker(env, env[1], ner=FakeNER(fail_for="Biển Đông"), max_attempts=2)
    assert w.run() == 4
    s = status(w)
    assert s["state"] == "FAILED" and s["succeeded_articles"] == 2 and s["failed_articles"] == 1 and "boom" in s["last_error"]
    db = pw.JobStore(w.dir / "pipeline.sqlite")
    bad = db.db.execute("SELECT status, attempts, error FROM articles WHERE status='FAILED'").fetchone()
    assert bad["attempts"] == 2 and "boom" in bad["error"]
    assert db.counts()["done"] == 2


def test_missing_article_is_isolated_and_not_retried(env):
    w = make_worker(env, env[1])
    w.manifest.append({"article_id": "deadbeefdeadbeef", "source": "test"})
    assert w.run() == 4
    s = status(w)
    assert s["succeeded_articles"] == 3 and s["failed_articles"] == 1 and "ARTICLE_NOT_FOUND" in s["last_error"]


def test_transient_error_is_retried_within_limit(env):
    w = make_worker(env, env[1], ner=FakeNER(flaky={"Biển Đông": 1}), max_attempts=3)
    assert w.run() == 0
    assert status(w)["succeeded_articles"] == 3
    assert any(e["event"] == "article_failed" and not e["final"] for e in map(json.loads, (w.dir / "events.jsonl").read_text(encoding="utf-8").splitlines()))


def test_stop_file_stops_gracefully_then_resume_finishes_without_repeats(env):
    w = make_worker(env, env[1])
    orig = w.stop_requested
    seen = []

    def stop_after_first():
        if len(events(w, "article_done")) >= 1 and not (w.dir / "STOP").exists():
            (w.dir / "STOP").write_text("x")
        seen.append(1)
        return orig()
    w.stop_requested = stop_after_first
    assert w.run() == 0
    assert status(w)["state"] == "STOPPED" and status(w)["succeeded_articles"] == 1
    w2 = make_worker(env, env[1])
    assert w2.run() == 0
    assert status(w2)["succeeded_articles"] == 3
    done_ids = [e["article_id"] for e in events(w2, "article_done")]
    assert len(done_ids) == 3 and len(set(done_ids)) == 3 and w2.ner.calls == 2  # only the 2 remaining articles were processed


def test_qwen_budget_stops_cleanly_and_resumes_with_higher_cap(env):
    w = make_worker(env, env[1], max_qwen_calls=0)
    assert w.run() == 3
    assert status(w)["state"] == "STOPPED" and status(w)["stop_reason"] == "BUDGET" and status(w)["succeeded_articles"] == 0
    db = pw.JobStore(w.dir / "pipeline.sqlite")
    assert db.counts()["pending"] == 3 and db.counts()["failed"] == 0
    w2 = make_worker(env, env[1], max_qwen_calls=50)
    assert w2.run() == 0 and status(w2)["succeeded_articles"] == 3 and status(w2)["llm_calls"] >= 1


def test_failed_qwen_window_marks_article_failed_not_done(env):
    w = make_worker(env, env[1], keys=("a1",), llm=FakeLLM(fail=True), max_attempts=1)
    assert w.run() == 4
    s = status(w)
    assert s["succeeded_articles"] == 0 and s["failed_articles"] == 1 and "LLMCallFailed" in s["last_error"]


def test_config_change_triggers_reprocessing(env):
    w = make_worker(env, env[1], keys=("a1",))
    assert w.run() == 0
    w2 = make_worker(env, env[1], keys=("a1",), fingerprint_extra={"x": 1})
    assert w2.run() == 0 and w2.ner.calls == 1


def test_lock_blocks_second_worker_and_stale_lock_is_taken_over(env):
    w = make_worker(env, env[1], keys=("a1",))
    (w.dir / "worker.lock").write_text(json.dumps({"pid": os.getpid()}))  # alive pid
    assert w.run() == 5
    (w.dir / "worker.lock").write_text(json.dumps({"pid": 999999}))  # dead pid
    assert w.run() == 0


def test_status_liveness_never_claims_running_without_heartbeat(env):
    jd = env[0] / "pipe" / "live"
    jd.mkdir(parents=True)

    def put(**kw):
        base = {"state": "RUNNING", "pid": os.getpid(), "heartbeat_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        (jd / "status.json").write_text(json.dumps({**base, **kw}), encoding="utf-8")
        return pw.read_status(jd)["liveness"]
    assert put() == "RUNNING_OK"
    assert put(heartbeat_at=(datetime.now().astimezone() - timedelta(seconds=600)).isoformat(timespec="seconds")) == "STALE"
    assert put(pid=999999) == "DEAD"
    assert put(state="COMPLETED", pid=999999) == "FINISHED"
    assert pw.read_status(env[0] / "pipe" / "nothing")["liveness"] == "NO_STATUS"


def test_official_sync_and_large_batches_are_refused(env):
    with pytest.raises(SystemExit):
        pw.Worker("x", [], mode="official-sync", pipe_dir=env[0] / "pipe")
    with pytest.raises(SystemExit):
        pw.Worker("x", [{"article_id": str(i)} for i in range(21)], pipe_dir=env[0] / "pipe")


def _row(s, o, st, decision, cls=None):
    return {"key": [s, "CHAIR_OF", o, st], "subject": s, "object": o, "predicate": "CHAIR_OF", "discovery_method": "RULE",
            "hybrid": {"decision": decision, "quarantine_class": cls, "agreement": "AGREE"},
            "evidence_all": [{"article_id": "a", "evidence_start": 0, "evidence_end": 5, "evidence_text": "xxxxx", "method": "RULE"}]}


def test_staging_graph_import_is_repeatable_and_semantic_only_clean_is_not_validated(tmp_path):
    store = pw.JobStore(tmp_path / "p.sqlite")
    rows = [_row("p1", "o1", "FACT", "PASS"), _row("p2", "o1", "FACT", "QUARANTINE", "SEMANTIC_ONLY_CLEAN"), _row("p3", "o2", "FACT", "REJECT"),
            _row("p1", "o1", "PLANNED", "QUARANTINE", "NON_OFFICIAL_STATUS")]
    g1 = pw.build_staging(store, rows, {}, {"a": "https://x"})
    g2 = pw.build_staging(store, rows + rows[:1], {}, {"a": "https://x"})  # same data again (+ a duplicate key)
    assert g1["edges_total"] == g2["edges_total"] == 4 and g1["edges_validated"] == 1 and g2["duplicate_edge_keys_dropped"] == 1
    assert g2["official_edges"] == 0 and g2["entities_validated"] == 2 and g2["evidence_rows"] == 4
    with pytest.raises(Exception):  # noqa: B017  (CHECK official = 0)
        store.db.execute("UPDATE staging_edges SET official=1")
    out = pw.export_staging(store, tmp_path / "x")
    assert out == {"validated": 1, "quarantine": 2, "rejected": 1}
    rels = (tmp_path / "x/neo4j_staging_rels.csv").read_text(encoding="utf-8-sig").strip().splitlines()
    assert len(rels) == 2 and rels[1].endswith(",false")


def test_ner_cache_is_versioned_and_avoids_second_inference(tmp_path):
    calls = []

    class N:
        def extract_sentences(self, text, sentences):
            calls.append(1)
            return [Mention(text="X", start=0, end=1, label=EntityType.ORGANIZATION, method="test_double")]
    c = CachedNER(tmp_path / "c.sqlite", N)
    assert len(c.extract_sentences("X abc", [])) == 1 and len(c.extract_sentences("X abc", [])) == 1
    assert len(calls) == 1 and (c.hits, c.live) == (1, 1)
    c2 = CachedNER(tmp_path / "c.sqlite", N, model_id="other-model")  # a different model never reuses the entry
    c2.extract_sentences("X abc", [])
    assert len(calls) == 2


def test_select_from_manifest_is_deterministic(tmp_path):
    src = tmp_path / "m.jsonl"
    src.write_text("\n".join(json.dumps({"article_id": f"t{i}", "subset": "targeted"}) for i in range(6)) + "\n"
                   + "\n".join(json.dumps({"article_id": f"c{i}", "subset": "control"}) for i in range(3)), encoding="utf-8")
    a = pw.select_from(src, 6, tmp_path / "o1.jsonl")
    b = pw.select_from(src, 6, tmp_path / "o2.jsonl")
    assert [r["article_id"] for r in a] == [r["article_id"] for r in b] == ["t0", "t1", "c0", "t2", "t3", "c1"]


def test_qwen_accounting_is_persisted_per_call_even_for_failed_articles(env):
    w = make_worker(env, env[1], keys=("a1",), llm=FakeLLM(fail=True), max_attempts=1)
    w.run()
    db = pw.JobStore(w.dir / "pipeline.sqlite")
    t = db.meta("qwen_totals")
    assert t["live"] >= 1 and t["failed"] == t["live"]


def test_poison_article_that_keeps_crashing_the_worker_is_isolated_after_three_crashes(env):
    w = make_worker(env, env[1], keys=("a1", "a2"))
    store = pw.JobStore(w.dir / "pipeline.sqlite")
    store.add_manifest(w.manifest)
    bad = env[1]["a1"]
    store.mark_running(bad)  # a previous worker died while processing it
    store.set_meta("crashes", {bad: 2})
    store.db.close()
    assert w.run() == 4
    db = pw.JobStore(w.dir / "pipeline.sqlite")
    r = db.db.execute("SELECT status, error FROM articles WHERE article_id=?", (bad,)).fetchone()
    assert r["status"] == "FAILED" and "CRASHED_WORKER" in r["error"]
    assert db.counts()["done"] == 1  # the other article was processed normally
