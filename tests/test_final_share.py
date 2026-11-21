"""The shared demo archive must restore usable SQLite, not just exported CSV."""
import json
import sqlite3
import zipfile

import pytest

from vckg.final_project.build import SCHEMA
from vckg.final_project.share import export_snapshot, install_snapshot


def _source_snapshot(folder):
    folder.mkdir()
    for name, mode in (("profile.sqlite", "passed"), ("quarantine.sqlite", "quarantine")):
        with sqlite3.connect(folder / name) as db:
            db.executescript(SCHEMA)
            if mode == "quarantine":
                db.execute("ALTER TABLE edges ADD COLUMN endpoint_quality TEXT")
            db.executemany("INSERT INTO nodes(node_id,name,entity_type,identity_status,aliases,pagerank,"
                           "degree,in_degree,out_degree,community,core_number,component) "
                           "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", [
                (key, key, "ORGANIZATION", "VERIFIED", "[]", 0.5, 1, 1, 1, 0, 1, 0)
                for key in ("a", "b")])
            db.execute("INSERT INTO edges(edge_uid,edge_id,tier,subject_id,predicate,object_id,"
                       "factual_status,evidence_count,article_count) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("ab", "ab", "QA_PASS", "a", "PARTNERS_WITH", "b", "FACT", 1, 1))
            if mode == "quarantine":
                db.execute("UPDATE edges SET endpoint_quality='ELIGIBLE'")
            db.execute("INSERT INTO evidence(evidence_id,edge_uid,article_id,source_url,publisher,"
                       "published_at,evidence_text,extraction_method) VALUES(?,?,?,?,?,?,?,?)",
                       ("ev", "ab", "article", "https://example.org/article", "Press", "2026-11-20",
                        "a cooperates with b", "RULE"))
    counts = {"node_count": 2, "edge_count": 1, "evidence_count": 1, "snapshot_id": "sample"}
    (folder / "metrics.json").write_text(json.dumps(counts), encoding="utf-8")
    (folder / "quarantine_metrics.json").write_text(json.dumps(counts), encoding="utf-8")
    (folder / "modes.json").write_text(json.dumps({"passed": "sample", "quarantine": "sample"}),
                                        encoding="utf-8")


def test_export_and_install_full_database(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source_snapshot(source)
    archive = tmp_path / "demo.zip"
    result = export_snapshot(source, archive)
    assert result["counts"]["quarantine.sqlite"] == {"nodes": 2, "edges": 1, "evidence": 1}
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == {"manifest.json", "snapshot/profile.sqlite",
                                           "snapshot/quarantine.sqlite", "snapshot/metrics.json",
                                           "snapshot/quarantine_metrics.json", "snapshot/modes.json"}
    root = tmp_path / "clean-install"
    installed = install_snapshot(archive, root)
    assert (root / "ACTIVE.txt").read_text(encoding="utf-8") == installed["snapshot"]
    monkeypatch.setenv("VCKG_FINAL_SNAPSHOT", installed["snapshot"])
    from fastapi.testclient import TestClient

    from vckg.final_project.app import app

    client = TestClient(app)
    assert client.get("/api/health").json()["modes"] == {"passed": True, "quarantine": True}
    assert client.get("/api/graph/subgraph", params={"mode": "quarantine"}).json()["counts"]["drawn_edges"] == 1
    assert install_snapshot(archive, root)["snapshot"] == installed["snapshot"]


def test_rejects_modified_archive_before_activation(tmp_path):
    source = tmp_path / "source"
    _source_snapshot(source)
    archive = tmp_path / "demo.zip"
    export_snapshot(source, archive)
    bad = tmp_path / "modified.zip"
    with zipfile.ZipFile(archive) as original, zipfile.ZipFile(bad, "w") as modified:
        for name in original.namelist():
            content = original.read(name)
            modified.writestr(name, b"not a SQLite file" if name == "snapshot/profile.sqlite" else content)
    root = tmp_path / "new-install"
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        install_snapshot(bad, root)
    assert not (root / "ACTIVE.txt").exists()
