"""Phase 6E.1 aggregation tests (offline, synthetic jobs written with the real JobStore/build_staging; baseline `collect` is replaced by a fixture).
They prove dedup/tiering/idempotence/no-merge behaviour of the aggregator, not extraction quality."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from vckg.graph import aggregate as ag
from vckg.jobs import pipeline_worker as pw

INFO = {
    "org:a": {"name": "Công ty cổ phần Alpha", "type": "ORGANIZATION", "status": "VERIFIED"},
    "org:b": {"name": "Công ty cổ phần Beta", "type": "ORGANIZATION", "status": "ARTICLE_GROUNDED"},
    "org:c": {"name": "Công ty cổ phần Gamma", "type": "ORGANIZATION", "status": "PROVISIONAL"},
    "org:alpha2": {"name": "Cong ty CP Alpha", "type": "ORGANIZATION", "status": "ARTICLE_GROUNDED"},
    "org:tc1": {"name": "Công ty cổ phần Thành Công Holdings", "type": "ORGANIZATION", "status": "ARTICLE_GROUNDED"},
    "org:tc2": {"name": "Công ty cổ phần Thành Công Holding", "type": "ORGANIZATION", "status": "ARTICLE_GROUNDED"},
    "person:nguyen-van-an@art:1": {"name": "Nguyễn Văn An", "type": "PERSON", "status": "ARTICLE_GROUNDED"},
    "person:nguyen-van-an@art:2": {"name": "Ông Nguyễn Văn An", "type": "PERSON", "status": "PROVISIONAL"},
    "person:le-thi-b@art:2": {"name": "Lê Thị B", "type": "PERSON", "status": "ARTICLE_GROUNDED"},
}


def row(s, p, o, decision="PASS", cls=None, status="FACT", art="1", span=(0, 10), method="RULE"):
    return {"key": [s, p, o, status], "subject": INFO[s]["name"], "object": INFO[o]["name"], "predicate": p, "discovery_method": method,
            "hybrid": {"decision": decision, "quarantine_class": cls, "agreement": "x"},
            "evidence_all": [{"article_id": art, "evidence_start": span[0], "evidence_end": span[1], "evidence_text": f"txt {art} {span}", "method": method}]}


def make_job(pipe: Path, job_id: str, rows: list[dict], state="COMPLETED", info=INFO):
    d = pipe / job_id
    d.mkdir(parents=True, exist_ok=True)
    store = pw.JobStore(d / "pipeline.sqlite")
    pw.build_staging(store, rows, info, {r["evidence_all"][0]["article_id"]: f"https://news.example/{r['evidence_all'][0]['article_id']}" for r in rows})
    store.db.close()
    (d / "status.json").write_text(json.dumps({"state": state, "job_id": job_id}), encoding="utf-8")
    return d


def fake_baseline(monkeypatch, official=(), candidates=(), merges=()):
    def ev(art, a=0, b=5, st="FACT"):
        return {"article_id": art, "source_url": f"https://legacy.example/{art}", "evidence_text": "legacy", "evidence_start": a, "evidence_end": b, "published_at": "2026-01-01",
                "extraction_method": "pattern+qwen", "review_status": "AUTO_ACCEPTED", "factual_status": st, "valid_from": None, "valid_to": None}
    off = [{"subject_id": s, "predicate": p, "object_id": o, "evidence": [ev(a)]} for s, p, o, a in official]
    cand = [{"subject_id": s, "predicate": p, "object_id": o, "evidence": [ev(a)]} for s, p, o, a in candidates]

    def collect(runs, regs, human=None):
        return off, cand, INFO, {}
    collect.last_merges = list(merges)
    monkeypatch.setattr(ag, "collect", collect)


@pytest.fixture
def env(tmp_path, monkeypatch):
    fake_baseline(monkeypatch, official=[("person:nguyen-van-an@art:1", "CHAIR_OF", "org:a", "L1")], candidates=[("org:a", "OWNS_SHARES_IN", "org:b", "L2")])
    return tmp_path


def go(env, jobs=None, **kw):
    return ag.run_all(env / "agg", env / "pipe", jobs=[{"job_id": j} for j in (jobs or [])], register_defaults=False, root=env, **kw) if False else _run(env, jobs)


def _run(env, jobs):
    a = ag.Agg(env / "agg" / "staging_graph.sqlite")
    a.register(ag.BASELINE_ID, "legacy_baseline", {})
    a.db.close()
    return ag.run_all(env / "agg", env / "pipe", jobs=[{"job_id": j} for j in (jobs or [])], register_defaults=False, root=env)


def test_tiers_are_separate_and_legacy_is_not_promoted_or_demoted(env):
    make_job(env / "pipe", "j1", [row("person:le-thi-b@art:2", "CEO_OF", "org:b", "PASS", art="2"), row("org:a", "OWNS_SHARES_IN", "org:c", "QUARANTINE", "HARD_BLOCK", art="3"),
                                  row("org:b", "ACQUIRED", "org:c", "REJECT", art="4")])
    m = _run(env, ["j1"])
    t = m["per_tier"]
    assert (t["LEGACY_OFFICIAL"]["unique_edges"], t["LEGACY_CANDIDATE"]["unique_edges"], t["QA_PASS"]["unique_edges"], t["QUARANTINE"]["unique_edges"], t["REJECT"]["unique_edges"]) == (1, 1, 1, 1, 1)
    assert m["unique_domain_nodes"]["validated_union(legacy_official+qa_pass)"] == 4
    assert t["QUARANTINE"]["by_class"] == {"HARD_BLOCK": 1}


def test_same_job_twice_and_rerun_do_not_inflate(env):
    make_job(env / "pipe", "j1", [row("person:le-thi-b@art:2", "CEO_OF", "org:b", art="2")])
    m1 = _run(env, ["j1"])
    m2 = _run(env, ["j1"])
    m3 = _run(env, ["j1", "j1"])
    assert m2["ingest"]["job:j1"] == "UNCHANGED"
    assert m1["content_hash"] == m2["content_hash"] == m3["content_hash"]
    assert m1["unique_edges_total_rows(edge,tier)"] == m3["unique_edges_total_rows(edge,tier)"] == 3 and m3["evidence"]["unique_rows"] == m1["evidence"]["unique_rows"]


def test_identical_content_in_two_jobs_is_deduplicated_and_counted(env):
    rows = [row("person:le-thi-b@art:2", "CEO_OF", "org:b", art="2"), row("org:a", "OWNS_SHARES_IN", "org:c", "QUARANTINE", "INSUFFICIENT_EVIDENCE", art="3")]
    make_job(env / "pipe", "j1", rows)
    base = _run(env, ["j1"])
    make_job(env / "pipe", "j2", rows)
    m = _run(env, ["j2"])
    assert m["unique_edges_total_rows(edge,tier)"] == base["unique_edges_total_rows(edge,tier)"]
    assert m["evidence"]["unique_rows"] == base["evidence"]["unique_rows"]
    assert m["duplicates_removed"]["edge_rows_across_sources"] == 2 and m["duplicates_removed"]["evidence_rows_across_sources"] == 2
    e = ag.Agg(env / "agg" / "staging_graph.sqlite").db.execute("SELECT sources FROM edges WHERE tier='QA_PASS'").fetchone()[0]
    assert json.loads(e) == ["job:j1", "job:j2"]


def test_changed_job_replaces_its_rows_instead_of_appending(env):
    d = make_job(env / "pipe", "j1", [row("person:le-thi-b@art:2", "CEO_OF", "org:b", art="2")])
    _run(env, ["j1"])
    shutil.rmtree(d)
    make_job(env / "pipe", "j1", [row("person:le-thi-b@art:2", "CEO_OF", "org:b", "QUARANTINE", "HARD_BLOCK", art="2")])
    m = _run(env, ["j1"])
    assert m["ingest"]["job:j1"] == "REPLACED"
    assert m["per_tier"]["QA_PASS"]["unique_edges"] == 0 and m["per_tier"]["QUARANTINE"]["unique_edges"] == 1


def test_same_triple_in_pass_and_quarantine_stays_in_both_tiers(env):
    make_job(env / "pipe", "j1", [row("org:a", "OWNS_SHARES_IN", "org:b", "PASS", art="5")])
    make_job(env / "pipe", "j2", [row("org:a", "OWNS_SHARES_IN", "org:b", "QUARANTINE", "SEMANTIC_ONLY_CLEAN", art="6", span=(1, 9))])
    m = _run(env, ["j1", "j2"])
    assert m["per_tier"]["QA_PASS"]["unique_edges"] == 1 and m["per_tier"]["QUARANTINE"]["unique_edges"] == 1 and m["per_tier"]["LEGACY_CANDIDATE"]["unique_edges"] == 1
    assert m["triples_present_in_several_tiers"]["QA_PASS & QUARANTINE"] == 1
    # evidence of the quarantined row is NOT attached to the PASS edge
    db = ag.Agg(env / "agg" / "staging_graph.sqlite").db
    assert db.execute("SELECT COUNT(*) FROM evidence WHERE tier='QA_PASS'").fetchone()[0] == 1


def test_same_edge_in_two_jobs_merges_evidence_and_keeps_urls(env):
    make_job(env / "pipe", "j1", [row("org:a", "OWNS_SHARES_IN", "org:b", art="5", span=(0, 5))])
    make_job(env / "pipe", "j2", [row("org:a", "OWNS_SHARES_IN", "org:b", art="6", span=(0, 5))])
    m = _run(env, ["j1", "j2"])
    db = ag.Agg(env / "agg" / "staging_graph.sqlite").db
    r = db.execute("SELECT n_evidence, n_articles FROM edges WHERE tier='QA_PASS'").fetchone()
    assert tuple(r) == (2, 2)
    urls = {x[0] for x in db.execute("SELECT source_url FROM evidence WHERE tier='QA_PASS'")}
    assert urls == {"https://news.example/5", "https://news.example/6"} and m["evidence"]["with_source_url"] == m["evidence"]["unique_rows"]


def test_same_name_persons_and_similar_orgs_are_reported_never_merged(env):
    make_job(env / "pipe", "j1", [row("person:nguyen-van-an@art:2", "CEO_OF", "org:alpha2", art="2"), row("org:tc1", "OWNS_SHARES_IN", "org:tc2", "QUARANTINE", "HARD_BLOCK", art="3")])
    m = _run(env, ["j1"])
    kinds = m["identity_collisions_unresolved"]["by_kind"]
    assert kinds["SAME_NAME_PERSONS_UNMERGED"] == 1 and kinds["SIMILAR_NAME_ORGS_UNMERGED"] == 1 and kinds["SAME_NAME_ORGS_DIFFERENT_ID"] == 1
    db = ag.Agg(env / "agg" / "staging_graph.sqlite").db
    assert db.execute("SELECT COUNT(*) FROM entities WHERE entity_id LIKE 'person:nguyen-van-an@%'").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM entities WHERE entity_id IN ('org:a','org:alpha2','org:tc1','org:tc2')").fetchone()[0] == 4
    d = json.loads(db.execute("SELECT detail FROM collisions WHERE kind='SAME_NAME_PERSONS_UNMERGED'").fetchone()[0])
    assert "PROVISIONAL" in json.dumps(d) or d["provisional_among"]


def test_same_id_with_conflicting_identity_is_kept_apart(env):
    other = {**INFO, "org:a": {"name": "Ngân hàng Hoàn Toàn Khác", "type": "BANK", "status": "VERIFIED"}}
    make_job(env / "pipe", "j1", [row("org:a", "OWNS_SHARES_IN", "org:b", art="5")], info=other)
    m = _run(env, ["j1"])
    assert m["identity_collisions_unresolved"]["by_kind"]["ID_CONFLICT"] == 1
    db = ag.Agg(env / "agg" / "staging_graph.sqlite").db
    keys = {r[0] for r in db.execute("SELECT entity_key FROM entities WHERE entity_id='org:a'")}
    assert keys == {"org:a@baseline_legacy", "org:a@job:j1"}
    assert m["per_tier"]["QA_PASS"]["unique_nodes"] == 2 and m["connected_components"]["validated_union(legacy_official+qa_pass)"]["components"] == 2


def test_entity_status_is_the_most_conservative_one(env):
    other = {**INFO, "org:a": {**INFO["org:a"], "status": "PROVISIONAL"}}
    make_job(env / "pipe", "j1", [row("org:a", "OWNS_SHARES_IN", "org:b", art="5")], info=other)
    _run(env, ["j1"])
    db = ag.Agg(env / "agg" / "staging_graph.sqlite").db
    assert db.execute("SELECT resolution_status FROM entities WHERE entity_key='org:a'").fetchone()[0] == "PROVISIONAL"


def test_smoke_rerun_and_incomplete_jobs_are_refused(env):
    make_job(env / "pipe", "smoke9", [row("org:a", "OWNS_SHARES_IN", "org:b", art="5")])
    make_job(env / "pipe", "j3", [row("org:a", "OWNS_SHARES_IN", "org:b", art="5")], state="STOPPED")
    for jid in ("smoke9", "j3"):
        a = ag.Agg(env / "agg" / "staging_graph.sqlite")
        with pytest.raises(SystemExit):
            a.ingest_job(jid, env / "pipe")
    assert ag.TEST_JOB.search("smoke-err") and ag.TEST_JOB.search("pilot-rerun") and not ag.TEST_JOB.search("pilot6d")


def test_disable_removes_source_from_aggregate_but_keeps_its_rows(env):
    make_job(env / "pipe", "j1", [row("org:a", "OWNS_SHARES_IN", "org:b", art="5")])
    _run(env, ["j1"])
    a = ag.Agg(env / "agg" / "staging_graph.sqlite")
    a.set_enabled("job:j1", False)
    a.db.close()
    m = ag.run_all(env / "agg", env / "pipe", register_defaults=False, root=env)
    assert m["per_tier"]["QA_PASS"]["unique_edges"] == 0 and m["disabled_sources"] == ["job:j1"]
    assert ag.Agg(env / "agg" / "staging_graph.sqlite").db.execute("SELECT COUNT(*) FROM src_edges WHERE source_id='job:j1'").fetchone()[0] == 1


def test_components_and_exports(env):
    make_job(env / "pipe", "j1", [row("person:le-thi-b@art:2", "CEO_OF", "org:b", art="2"), row("org:b", "OWNS_SHARES_IN", "org:c", art="2", span=(20, 30))])
    m = _run(env, ["j1"])
    c = m["connected_components"]["validated_union(legacy_official+qa_pass)"]
    assert c["nodes"] == 5 and c["components"] == 2 and c["largest"] == 3
    ex = env / "agg" / "export"
    for f in ("graph_validated.graphml", "graph_all_tiers.graphml", "nodes.csv", "edges.csv", "evidence.csv", "collisions.csv"):
        assert (ex / f).exists()
    assert "QA_PASS" in (ex / "graph_validated.graphml").read_text(encoding="utf-8") and "QUARANTINE" not in (ex / "graph_validated.graphml").read_text(encoding="utf-8")
    assert (env / "agg" / "summary.json").exists()


def test_unknown_decision_is_an_error_not_a_silent_tier(env):
    d = make_job(env / "pipe", "j1", [row("org:a", "OWNS_SHARES_IN", "org:b", art="5")])
    import sqlite3
    db = sqlite3.connect(d / "pipeline.sqlite")
    db.execute("UPDATE staging_edges SET decision='MAYBE'")
    db.commit()
    db.close()
    with pytest.raises(SystemExit):
        _run(env, ["j1"])


def test_real_pilot6d_is_idempotent_and_duplicate_copy_is_removed(tmp_path):
    src = ag.PIPE / "pilot6d"
    if not (src / "pipeline.sqlite").exists() or not (ag.ROOT / "data/outputs/phase5/new144").exists():
        pytest.skip("pilot6d / phase5 outputs not present")
    pipe = tmp_path / "pipe"
    for jid in ("pilot6d", "pilot6d_copy_x"):
        (pipe / jid).mkdir(parents=True)
        shutil.copy(src / "pipeline.sqlite", pipe / jid / "pipeline.sqlite")
        shutil.copy(src / "status.json", pipe / jid / "status.json")
    m1 = ag.run_all(tmp_path / "agg", pipe, register_defaults=True)
    assert m1["per_tier"]["LEGACY_OFFICIAL"]["unique_edges"] == 44 and m1["per_tier"]["QA_PASS"]["unique_edges"] == 4
    m2 = ag.run_all(tmp_path / "agg", pipe, jobs=[{"job_id": "pilot6d_copy_x"}], register_defaults=False)
    assert m2["per_tier"]["QA_PASS"]["unique_edges"] == 4 and m2["duplicates_removed"]["edge_rows_across_sources"] == 44
    assert m2["unique_domain_nodes"] == m1["unique_domain_nodes"] and m2["evidence"]["unique_rows"] == m1["evidence"]["unique_rows"]


# ------------------------------------------------------------------------------------------------ Phase 6G: cross-source person consolidation (evidence-based only)
INFO.update({
         "person:nguyen-van-an@art:7": {"name": "Nguyễn Văn An", "type": "PERSON", "status": "ARTICLE_GROUNDED"},
         "person:nguyen-van-an@art:8": {"name": "Nguyễn Văn An", "type": "PERSON", "status": "ARTICLE_GROUNDED"},
         "person:an@art:9": {"name": "An", "type": "PERSON", "status": "ARTICLE_GROUNDED"},
         "person:an@art:10": {"name": "An", "type": "PERSON", "status": "ARTICLE_GROUNDED"}})
PINFO = INFO


def _people(env, rows, info=PINFO):
    make_job(env / "pipe", "j1", rows, info=info)
    return _run(env, ["j1"])


def test_same_name_persons_with_a_shared_organisation_in_validated_edges_are_merged_and_logged(env):
    m = _people(env, [row("person:nguyen-van-an@art:7", "CEO_OF", "org:a", "PASS", art="7")])
    db = ag.Agg(env / "agg" / "staging_graph.sqlite").db
    merges = db.execute("SELECT kept, dropped, name_key, shared_orgs FROM person_merges").fetchall()
    assert len(merges) == 1 and merges[0][2] == "nguyen van an" and json.loads(merges[0][3]) == ["org:a"]
    keys = {r[0] for r in db.execute("SELECT entity_key FROM entities WHERE entity_type='PERSON'")}
    assert merges[0][1] not in keys and merges[0][0] in keys
    pass_edge = db.execute("SELECT subject_key FROM edges WHERE tier='QA_PASS'").fetchone()[0]
    assert pass_edge == merges[0][0] and m["identity_collisions_unresolved"]["by_kind"].get("SAME_NAME_PERSONS_UNMERGED") is None
    assert _run(env, ["j1"])["content_hash"] == m["content_hash"]  # deterministic and idempotent


def test_same_name_persons_are_not_merged_without_shared_org_or_when_provisional_or_single_token(env):
    m = _people(env, [row("person:nguyen-van-an@art:7", "CEO_OF", "org:b", "PASS", art="7"),  # other organisation than the baseline person's org:a
                      row("person:nguyen-van-an@art:2", "CEO_OF", "org:a", "PASS", art="2"),  # PROVISIONAL person, shared org:a
                      row("person:an@art:9", "CEO_OF", "org:a", "PASS", art="9"), row("person:an@art:10", "CEO_OF", "org:a", "PASS", art="10")])  # single-token names
    db = ag.Agg(env / "agg" / "staging_graph.sqlite").db
    assert db.execute("SELECT COUNT(*) FROM person_merges").fetchone()[0] == 0
    assert m["identity_collisions_unresolved"]["by_kind"]["SAME_NAME_PERSONS_UNMERGED"] >= 1


def test_quarantined_edges_are_not_evidence_for_merging_people(env):
    _people(env, [row("person:nguyen-van-an@art:7", "CEO_OF", "org:a", "QUARANTINE", "HARD_BLOCK", art="7")])
    assert ag.Agg(env / "agg" / "staging_graph.sqlite").db.execute("SELECT COUNT(*) FROM person_merges").fetchone()[0] == 0
