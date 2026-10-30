"""Neo4j sync: offline logic tests + integration tests against the project Neo4j (SKIPPED when it is not running)."""
import json

import pytest

from vckg.graph import neo4j_sync as ns

EV = {"article_id": "a1", "source_url": "https://e.com/a1", "evidence_text": "Ong A la Chu tich B.", "evidence_start": 0, "evidence_end": 20,
      "published_at": None, "extraction_method": "t", "relation_score": None, "score_available": False, "validation_status": "ACCEPTED",
      "review_status": "AUTO_ACCEPTED", "factual_status": "FACT", "valid_from": None, "valid_to": None, "model": "m", "prompt_version": "v"}
INFO = {"person:a@art:1": {"name": "Nguyen Van A", "type": "PERSON", "status": "ARTICLE_GROUNDED"},
        "person:a@art:2": {"name": "Nguyễn Văn A", "type": "PERSON", "status": "ARTICLE_GROUNDED"},
        "person:a@art:3": {"name": "Nguyen Van A", "type": "PERSON", "status": "ARTICLE_GROUNDED"},
        "org:b": {"name": "Cong ty B", "type": "ORGANIZATION", "status": "ARTICLE_GROUNDED"},
        "org:c": {"name": "Cong ty C", "type": "ORGANIZATION", "status": "ARTICLE_GROUNDED"}}


def E(s, p, o, **kw):
    return {"subject_id": s, "predicate": p, "object_id": o, "evidence": [{**EV, **kw}]}


def test_edge_id_stable_and_window_sensitive():
    a = E("p", "CHAIR_OF", "o")
    assert ns.edge_id(a) == ns.edge_id(json.loads(json.dumps(a)))
    assert ns.edge_id(a) != ns.edge_id(E("p", "CHAIR_OF", "o", valid_from="2020"))
    assert ns.edge_id(a) != ns.edge_id(E("p", "CEO_OF", "o"))


def test_cross_run_person_merge_needs_same_name_and_shared_org():
    off = [E("person:a@art:1", "CHAIR_OF", "org:b"), E("person:a@art:2", "CEO_OF", "org:b", article_id="a2"), E("person:a@art:3", "CHAIR_OF", "org:c", article_id="a3")]
    o2, _, merges = ns.consolidate_persons_across_runs(off, [], INFO)
    ids = {e["subject_id"] for e in o2}
    assert "person:a@art:1" in ids and "person:a@art:2" not in ids  # same name + same org -> merged
    assert "person:a@art:3" in ids  # same name, different org only -> stays separate
    assert merges == [{"keep": "person:a@art:1", "drop": "person:a@art:2", "name_key": "nguyen van a", "shared_orgs": ["org:b"]}]


def test_collect_dedupes_and_candidate_isolation(tmp_path):
    d = tmp_path / "run"
    d.mkdir()
    off = E("person:a@art:1", "CHAIR_OF", "org:b")
    cand_dup = E("person:a@art:1", "CHAIR_OF", "org:b", review_status="NEEDS_REVIEW")  # same edge also listed as candidate
    cand = E("person:a@art:1", "CEO_OF", "org:c", review_status="NEEDS_REVIEW", validation_status="CANDIDATE:ENDPOINT_NOT_VERIFIED")
    (d / "relations_official.jsonl").write_text(json.dumps(off) + "\n" + json.dumps(E("person:a@art:1", "CHAIR_OF", "org:b", article_id="a9")), encoding="utf-8")
    (d / "relations_candidate.jsonl").write_text(json.dumps(cand_dup) + "\n" + json.dumps(cand), encoding="utf-8")
    o, c, _, arts = ns.collect([d], [None])
    assert len(o) == 1 and len(o[0]["evidence"]) == 2  # 2 sources, ONE edge
    assert [(e["predicate"]) for e in c] == ["CEO_OF"]  # a candidate that is also official is not a candidate
    assert set(arts) == {"a1", "a9"}


def test_projection_export_labels_derived(tmp_path):
    off = [E("person:a@art:1", "CHAIR_OF", "org:b"), E("person:z", "CEO_OF", "org:b")]
    res = ns.export_projections(off, tmp_path, INFO)
    assert res["person_person"] == {"nodes": 2, "edges": 1}
    assert "True" in (tmp_path / "person_person_edges.csv").read_text()


def _neo():
    try:
        d = ns.connect()
        d.verify_connectivity()
        return d
    except Exception:  # noqa: BLE001
        return None


@pytest.mark.integration
def test_neo4j_idempotent_import_and_candidate_isolation():
    d = _neo()
    if d is None:
        pytest.skip("project Neo4j not running (scripts/start-neo4j.ps1)")
    db_check = d.session().run("MATCH (n:Entity) WHERE n.entity_id STARTS WITH 'zz-test:' RETURN count(n) AS c").single()["c"]
    assert db_check == 0
    info = {"zz-test:p": {"name": "ZZ P", "type": "PERSON", "status": "ARTICLE_GROUNDED"}, "zz-test:o": {"name": "ZZ O", "type": "ORGANIZATION", "status": "ARTICLE_GROUNDED"},
            "zz-test:c": {"name": "ZZ C", "type": "ORGANIZATION", "status": "PROVISIONAL"}}
    off = [E("zz-test:p", "CHAIR_OF", "zz-test:o", article_id="zz-a")]
    cand = [E("zz-test:p", "CEO_OF", "zz-test:c", article_id="zz-a", review_status="NEEDS_REVIEW", validation_status="CANDIDATE:ENDPOINT_NOT_VERIFIED")]
    arts = {"zz-a": {"article_id": "zz-a", "url": "https://e.com/zz", "published_at": ""}}
    try:
        before = ns.stats(d)
        s1 = ns.sync(d, off, cand, info, arts)
        s2 = ns.sync(d, off, cand, info, arts)
        assert s1 == s2  # re-import changes nothing
        assert s2["domain_entity_nodes"] == before["domain_entity_nodes"] + 2 and s2["official_edges"] == before["official_edges"] + 1
        assert s2["candidate_edges"] == before["candidate_edges"] + 1
        with d.session() as s:
            assert s.run("MATCH (n:Entity {entity_id:'zz-test:c'}) RETURN count(n) AS c").single()["c"] == 0  # candidate endpoint is not a domain entity
            assert s.run("MATCH (:Entity {entity_id:'zz-test:p'})-[r:CEO_OF]->() RETURN count(r) AS c").single()["c"] == 0
            assert s.run("MATCH (e:Evidence {edge_id:$i})-[:FROM]->(:Article {article_id:'zz-a'}) RETURN count(e) AS c", i=ns.edge_id(off[0])).single()["c"] == 1
        # promotion: candidate becomes official -> leaves candidate namespace
        info["zz-test:c"]["status"] = "ARTICLE_GROUNDED"
        ns.sync(d, [*off, E("zz-test:p", "CEO_OF", "zz-test:c", article_id="zz-a")], [], info, arts)
        with d.session() as s:
            assert s.run("MATCH ()-[r:CANDIDATE]->() WHERE r.predicate='CEO_OF' AND r.edge_id=$i RETURN count(r) AS c",
                         i=ns.edge_id(cand[0])).single()["c"] == 0
    finally:
        with d.session() as s:
            s.run("MATCH (n) WHERE n.entity_id STARTS WITH 'zz-test:' DETACH DELETE n")
            s.run("MATCH (e:Evidence) WHERE e.edge_id IN $ids DETACH DELETE e", ids=[ns.edge_id(off[0]), ns.edge_id(cand[0])])
            s.run("MATCH (a:Article {article_id:'zz-a'}) DETACH DELETE a")
