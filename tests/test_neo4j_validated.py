"""Neo4j validated-layer sync (offline: a fake driver records what would be written; the live run is reported separately). Proves backup verification, dry-run,
idempotence, namespace isolation, QA_PASS-only selection and the legacy-unchanged guard."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from test_aggregate import INFO, _run, fake_baseline, make_job, row  # noqa: F401
from vckg.graph import aggregate as ag
from vckg.graph import neo4j_validated as nv

LEGACY = {"MATCH (n:Entity) RETURN count(n)": 74, "WHERE r.edge_id IS NOT NULL RETURN count(r)": 44, "count(DISTINCT type(r))": 8, "MATCH (e:Evidence) RETURN count(e)": 60,
          "MATCH (a:Article) RETURN count(a)": 59, "MATCH (n:CandEntity) RETURN count(n)": 30, "MATCH (:CandEntity)-[r:CANDIDATE]": 31}


class Res:
    def __init__(self, rows):
        self.rows = rows

    def single(self):
        return self.rows[0]

    def __iter__(self):
        return iter(self.rows)


class Sess:
    def __init__(self, d):
        self.d = d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def run(self, q, **p):
        d = self.d
        d.queries.append(q)
        if "UNWIND $rows" in q:
            rows = p["rows"]
            if "MERGE (n:VEntity" in q:
                d.nodes |= {r["entity_id"] for r in rows}
                d.labels.add(q.split("SET n:")[1].split(",")[0])
            elif "MERGE (a)-[x:" in q:
                d.edges |= {r["edge_id"] for r in rows}
            elif "MERGE (v:VEvidence" in q:
                d.ev |= {r["evidence_id"] for r in rows}
            if d.mutate_legacy:
                LEGACY_STATE["x"] = True
            return Res([])
        if "CREATE CONSTRAINT" in q or ("MERGE" in q and "SAME_REGISTRY_ID" in q):
            return Res([])
        if "RETURN n.entity_id" in q:
            return Res([(i,) for i in sorted(d.nodes)] if ":VEntity" in q else [(i,) for i in d.legacy_ids])
        if "RETURN r.edge_id" in q:
            return Res([(i,) for i in sorted(d.edges)])
        if "RETURN e.evidence_id" in q:
            return Res([(i,) for i in sorted(d.ev)])
        if "VEntity) RETURN count" in q:
            return Res([(len(d.nodes),)])
        if "layer='QA_VALIDATED' RETURN count(r)" in q:
            return Res([(len(d.edges),)])
        if "layer='QA_VALIDATED' RETURN count(DISTINCT" in q:
            return Res([(1,)])
        if "VEvidence) RETURN count" in q:
            return Res([(len(d.ev),)])
        if "VArticle) RETURN count" in q:
            return Res([(0,)])
        if "SAME_REGISTRY_ID]" in q:
            return Res([(0,)])
        for k, v in LEGACY.items():
            if k in q and ("Entity" in q or "Evidence" in q or "Article" in q or "CandEntity" in q):
                if k == "count(DISTINCT type(r))" and "Entity" not in q:
                    continue
                return Res([(v + (1 if LEGACY_STATE.get("x") and k == "MATCH (n:Entity) RETURN count(n)" else 0),)])
        raise AssertionError("unexpected query: " + q)


LEGACY_STATE: dict = {}


class FakeDriver:
    def __init__(self, mutate_legacy=False, legacy_ids=()):
        self.queries, self.nodes, self.edges, self.ev, self.labels = [], set(), set(), set(), set()
        self.mutate_legacy, self.legacy_ids = mutate_legacy, list(legacy_ids)
        LEGACY_STATE.clear()

    def session(self):
        return Sess(self)

    def verify_connectivity(self):
        return None

    def close(self):
        return None


@pytest.fixture
def agg(tmp_path, monkeypatch):
    fake_baseline(monkeypatch, official=[("person:nguyen-van-an@art:1", "CHAIR_OF", "org:a", "L1")])
    make_job(tmp_path / "pipe", "j1", [row("person:le-thi-b@art:2", "CEO_OF", "org:b", "PASS", art="2"), row("org:a", "OWNS_SHARES_IN", "org:c", "QUARANTINE", "HARD_BLOCK", art="3"),
                                       row("org:b", "ACQUIRED", "org:c", "REJECT", art="4"), row("org:a", "SUBSIDIARY_OF", "org:b", "PASS", status="HISTORICAL", art="5")])
    _run(tmp_path, ["j1"])
    return tmp_path / "agg" / "staging_graph.sqlite"


def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "neo4j_data"
    (d / "databases" / "neo4j").mkdir(parents=True)
    (d / "databases" / "neo4j" / "neostore").write_bytes(b"x" * 5000)
    (d / "dbms").mkdir()
    (d / "dbms" / "auth.ini").write_text("neo4j:secret")
    return d


def test_only_qa_pass_is_selected_and_conflicting_tiers_are_recorded(agg):
    rows = nv.build_rows(nv.collect_validated(agg))
    assert sum(len(v) for v in rows["edges"].values()) == 2 and set(rows["edges"]) == {"CEO_OF", "SUBSIDIARY_OF"}  # no QUARANTINE / REJECT / LEGACY
    assert all(lab.startswith("V") for lab in rows["nodes"]) and rows["evidence"] and all(e["url"].startswith("https://news.example/") for e in rows["evidence"])
    hist = next(e for e in rows["edges"]["SUBSIDIARY_OF"])
    assert hist["factual_status"] == "HISTORICAL" and hist["n_evidence"] == 1  # historical relations keep their status and provenance


def test_dry_run_then_merge_is_idempotent_and_legacy_labels_are_never_written(agg, tmp_path):
    drv = FakeDriver(legacy_ids=["org:a"])
    rows = nv.build_rows(nv.collect_validated(agg))
    p1 = nv.plan(drv, rows)
    assert p1["nodes_new"] == p1["nodes_total"] > 0 and p1["edges_new"] == 2 and p1["evidence_new"] == len(rows["evidence"])
    nv.apply(drv, rows)
    p2 = nv.plan(drv, rows)
    assert (p2["nodes_new"], p2["edges_new"], p2["evidence_new"]) == (0, 0, 0)
    nv.apply(drv, rows)  # a second MERGE changes nothing
    assert (len(drv.nodes), len(drv.edges)) == (p1["nodes_total"], 2)
    writes = [q for q in drv.queries if "MERGE" in q]
    assert writes and not any(":Entity" in q.replace("VEntity", "") and "SAME_REGISTRY_ID" not in q for q in writes)  # only V-labelled nodes are merged; Entity is only MATCHed for the pointer
    assert not any("DELETE" in q or "SET e." in q or "REMOVE" in q for q in drv.queries)  # nothing destructive, no legacy property written
    assert all(x.startswith("V") for x in drv.labels)


def test_backup_is_verified_file_by_file_and_requires_a_stopped_database(tmp_path):
    d = data_dir(tmp_path)
    with pytest.raises(nv.Blocked):
        nv.make_backup(tmp_path / "bk", d, running=lambda: True)
    b = nv.make_backup(tmp_path / "bk", d, running=lambda: False)
    man = json.loads((b / "manifest.json").read_text(encoding="utf-8"))
    assert man["verified"] and len(man["files"]) == 2 and nv.reverify_backup(b, man) and nv.latest_verified_backup(tmp_path / "bk")[0] == b
    (b / "data" / "databases" / "neo4j" / "neostore").write_bytes(b"tampered")
    assert not nv.reverify_backup(b, man)


def run_sync(tmp_path, agg, driver, **kw):
    state = {"up": kw.pop("up", False), "calls": []}

    def start():
        state["calls"].append("start")
        state["up"] = True
        return 0

    def stop():
        state["calls"].append("stop")
        state["up"] = False
        return 0
    res = nv.sync(agg, tmp_path / "bk", None, running=lambda: state["up"], start=start, stop=stop, connect_fn=lambda: driver, data_dir=data_dir(tmp_path) if not (tmp_path / "neo4j_data").exists() else tmp_path / "neo4j_data")
    return res, state


def test_sync_takes_backup_first_records_legacy_stats_and_leaves_neo4j_as_found(agg, tmp_path):
    res, state = run_sync(tmp_path, agg, FakeDriver(), up=False)
    assert res["backup_created"] and res["idempotent"] and res["dry_run"]["edges_new"] == 2 and res["legacy_before"] == res["legacy_after"]
    assert state["calls"] == ["start", "stop"]  # started for the sync, stopped again because it was stopped before
    man = json.loads((Path(res["backup"]) / "manifest.json").read_text(encoding="utf-8"))
    assert man["legacy_stats"]["official_edges"] == 44 and man["legacy_stats"]["entity_nodes"] == 74
    drv = FakeDriver()
    res2, state2 = run_sync(tmp_path, agg, drv, up=True)  # second run: backup exists, Neo4j was running -> not stopped
    assert "backup_created" not in res2 and state2["calls"] == []


def test_running_database_is_stopped_for_the_cold_backup_then_restarted(agg, tmp_path):
    res, state = run_sync(tmp_path, agg, FakeDriver(), up=True)
    assert state["calls"] == ["stop", "start"] and res["backup_created"]


def test_sync_blocks_when_backup_is_corrupt_or_legacy_graph_differs_or_changes(agg, tmp_path):
    res, _ = run_sync(tmp_path, agg, FakeDriver(), up=False)
    b = Path(res["backup"])
    man = json.loads((b / "manifest.json").read_text(encoding="utf-8"))
    man["legacy_stats"]["official_edges"] = 43  # legacy differs from the backup-time stats
    (b / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(nv.Blocked, match="legacy graph differs"):
        run_sync(tmp_path, agg, FakeDriver(), up=True)
    man["legacy_stats"]["official_edges"] = 44
    (b / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(nv.Blocked, match="LEGACY GRAPH CHANGED"):
        run_sync(tmp_path, agg, FakeDriver(mutate_legacy=True), up=True)
    (b / "data" / "dbms" / "auth.ini").write_text("tampered")
    with pytest.raises(nv.Blocked, match="no longer verifies"):
        run_sync(tmp_path, agg, FakeDriver(), up=True)


def test_no_write_when_no_validated_edges_exist(tmp_path, monkeypatch):
    fake_baseline(monkeypatch, official=[("person:nguyen-van-an@art:1", "CHAIR_OF", "org:a", "L1")])
    make_job(tmp_path / "pipe", "j1", [row("org:a", "OWNS_SHARES_IN", "org:c", "QUARANTINE", "HARD_BLOCK", art="3")])
    _run(tmp_path, ["j1"])
    rows = nv.build_rows(nv.collect_validated(tmp_path / "agg" / "staging_graph.sqlite"))
    assert rows["edges"] == {} and rows["nodes"] == {}
    assert ag.Agg(tmp_path / "agg" / "staging_graph.sqlite").db.execute("SELECT COUNT(*) FROM edges WHERE tier='QUARANTINE'").fetchone()[0] == 1  # stays in the separate dataset
    shutil.rmtree(tmp_path / "agg", ignore_errors=True)
