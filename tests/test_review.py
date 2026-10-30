"""Review workflow tests: idempotency, history, identity guard, evidence guard, correction, candidate isolation."""
import csv
import json

import pytest

from vckg.review import CSV_COLUMNS, ReviewStore

EV = {"article_id": "a1", "source_url": "https://e.com/a1", "evidence_text": "Ông A là Chủ tịch Công ty B.", "evidence_start": 0,
      "evidence_end": 28, "published_at": None, "extraction_method": "t", "relation_score": None, "score_available": False,
      "validation_status": "CANDIDATE:ENDPOINT_NOT_VERIFIED", "review_status": "NEEDS_REVIEW", "factual_status": "FACT",
      "valid_from": None, "valid_to": None, "model": "m", "prompt_version": "v"}


def edge(s, p, o, ev=None):
    return {"subject_id": s, "predicate": p, "object_id": o, "evidence": [ev or EV]}


def make_run(tmp_path, cands, officials=(), outcomes=()):
    d = tmp_path / "run"
    d.mkdir()
    (d / "relations_candidate.jsonl").write_text("\n".join(json.dumps(e) for e in cands), encoding="utf-8")
    (d / "relations_official.jsonl").write_text("\n".join(json.dumps(e) for e in officials), encoding="utf-8")
    return d


def make_registry(tmp_path, rows):
    import sqlite3
    p = tmp_path / "reg.sqlite"
    db = sqlite3.connect(p)
    db.execute("CREATE TABLE entities(entity_id TEXT, canonical_name TEXT, resolution_status TEXT)")
    db.executemany("INSERT INTO entities VALUES(?,?,?)", rows)
    db.commit()
    db.close()
    return p


@pytest.fixture()
def rs(tmp_path):
    reg = make_registry(tmp_path, [("p:a", "Ông A", "ARTICLE_GROUNDED"), ("org:b", "Công ty B", "ARTICLE_GROUNDED"), ("org:c", "Công ty C", "PROVISIONAL"),
                                   ("p:d", "Ông D", "ARTICLE_GROUNDED")])
    run = make_run(tmp_path, [edge("p:a", "CHAIR_OF", "org:b"), edge("p:a", "CEO_OF", "org:c"),
                              edge("p:d", "CHAIR_OF", "org:b", {**EV, "factual_status": "PLANNED", "validation_status": "CANDIDATE:NON_FACTUAL_RELATION"})],
                   officials=[edge("p:d", "BOARD_MEMBER_OF", "org:b", {**EV, "validation_status": "ACCEPTED", "review_status": "AUTO_ACCEPTED"})])
    s = ReviewStore(tmp_path / "r.sqlite")
    s.build_queue([run], reg, include_official=True)
    s.reg = reg
    return s


def ids(rs):
    return {(i["subject_id"], i["predicate"], i["object_id"]): i["item_id"] for i in rs.queue(False)}


def test_queue_priorities_and_official_audit_class(rs):
    q = {(i["subject_id"], i["predicate"], i["object_id"]): i for i in rs.queue(False)}
    assert q[("p:a", "CHAIR_OF", "org:b")]["priority"] == 1  # complete evidence, both endpoints clear
    assert q[("p:a", "CEO_OF", "org:c")]["priority"] == 4 or q[("p:a", "CEO_OF", "org:c")]["priority"] in (2, 3, 4)
    assert q[("p:d", "CHAIR_OF", "org:b")]["priority"] == 4  # modality doubt
    assert q[("p:d", "BOARD_MEMBER_OF", "org:b")]["priority"] == 5 and q[("p:d", "BOARD_MEMBER_OF", "org:b")]["origin"] == "official"
    assert [i["priority"] for i in rs.queue(False)] == sorted(i["priority"] for i in rs.queue(False))


def test_accept_requires_evidence_identity_and_official_status(rs):
    m = ids(rs)
    assert rs.act(m[("p:a", "CHAIR_OF", "org:b")], "ACCEPT", "rev1", "ok")["applied"]
    r = rs.act(m[("p:a", "CEO_OF", "org:c")], "ACCEPT", "rev1")
    assert not r["applied"] and "identity" in r["reason"]  # human label cannot hide an identity problem
    r = rs.act(m[("p:d", "CHAIR_OF", "org:b")], "ACCEPT", "rev1")
    assert not r["applied"] and "PLANNED" in r["reason"]
    assert rs.state(m[("p:a", "CEO_OF", "org:c")]) == "PENDING"


def test_no_evidence_blocks_accept(tmp_path):
    run = make_run(tmp_path, [{"subject_id": "p:a", "predicate": "CHAIR_OF", "object_id": "org:b", "evidence": []}])
    reg = make_registry(tmp_path, [("p:a", "A", "ARTICLE_GROUNDED"), ("org:b", "B", "ARTICLE_GROUNDED")])
    s = ReviewStore(":memory:")
    s.build_queue([run], reg)
    assert "evidence" in s.act(s.queue(False)[0]["item_id"], "ACCEPT", "r")["reason"]


def test_actions_idempotent_history_and_state(rs):
    iid = ids(rs)[("p:a", "CHAIR_OF", "org:b")]
    assert rs.act(iid, "UNSURE", "r1", "check")["applied"]
    assert rs.state(iid) == "UNSURE" and iid in {i["item_id"] for i in rs.queue(True)}  # unsure stays in queue
    assert rs.act(iid, "ACCEPT", "r1", "now sure")["applied"]
    again = rs.act(iid, "ACCEPT", "r1", "now sure")
    assert not again["applied"] and "idempotent" in again["reason"]
    h = rs.history(iid)
    assert [x["action"] for x in h] == ["UNSURE", "ACCEPT"] and all(x["reviewer"] == "r1" and x["ts"] and x["original"] for x in h)
    assert rs.act(iid, "REJECT", "r1", "changed mind")["applied"]  # history kept, latest wins
    assert len(rs.history(iid)) == 3 and rs.state(iid) == "REJECTED"
    assert iid not in {i["item_id"] for i in rs.queue(True)}


def test_correct_swap_replace_and_registry_guard(rs):
    iid = ids(rs)[("p:a", "CEO_OF", "org:c")]
    assert not rs.act(iid, "CORRECT", "r", "x", {})["applied"]
    bad = rs.act(iid, "CORRECT", "r", "x", {"object_id": "org:c"}, registry_statuses={"org:c": "PROVISIONAL"})
    assert not bad["applied"] and "not a VERIFIED/ARTICLE_GROUNDED" in bad["reason"]
    ok = rs.act(iid, "CORRECT", "r", "company is B", {"object_id": "org:b", "predicate": "CHAIR_OF"}, registry_statuses={"org:b": "ARTICLE_GROUNDED"})
    assert ok["applied"]
    edges = {e.key: e for e in rs.human_edges()}
    e = edges[("p:a", "CHAIR_OF", "org:b")]
    assert e.evidence[0].review_status.value == "HUMAN_VERIFIED" and e.evidence[0].source_url == EV["source_url"]
    h = rs.history(iid)[-1]
    assert h["original"]["object_id"] == "org:c" and h["revised"]["object_id"] == "org:b"
    swapped = rs.act(ids(rs)[("p:a", "CHAIR_OF", "org:b")], "CORRECT", "r2", "direction", {"direction": "SWAP"})
    assert swapped["applied"] and ("org:b", "CHAIR_OF", "p:a") in {e.key for e in rs.human_edges()}


def test_unreviewed_candidates_never_become_human_or_official(rs):
    assert rs.human_edges() == []
    rs.act(ids(rs)[("p:a", "CHAIR_OF", "org:b")], "UNSURE", "r")
    rs.act(ids(rs)[("p:d", "CHAIR_OF", "org:b")], "REJECT", "r")
    assert rs.human_edges() == [] and rs.stats()["human_verified_unique_edges"] == 0


def test_csv_roundtrip_is_idempotent(rs, tmp_path):
    out = tmp_path / "q.csv"
    n = rs.export_csv(out, only_pending=True)
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
    assert n == len(rows) and list(rows[0].keys()) == CSV_COLUMNS and all(r["action"] == "" for r in rows)
    for r in rows:
        if r["subject_id"] == "p:a" and r["predicate"] == "CHAIR_OF":
            r["action"], r["reviewer"], r["note"] = "ACCEPT", "alice", "looks right"
        if r["subject_id"] == "p:a" and r["predicate"] == "CEO_OF":
            r["action"], r["reviewer"] = "ACCEPT", "alice"  # will be refused: identity
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    r1 = rs.import_csv(out, registry_db=rs.reg)
    r2 = rs.import_csv(out, registry_db=rs.reg)
    assert r1["applied"] == 1 and len(r1["refused"]) == 1 and "identity" in r1["refused"][0]["reason"]
    assert r2["applied"] == 0  # re-import: nothing duplicated
    assert rs.stats()["actions_logged"] == 1 and rs.stats()["human_verified_unique_edges"] == 1


def test_rebuild_queue_keeps_actions(rs):
    iid = ids(rs)[("p:a", "CHAIR_OF", "org:b")]
    rs.act(iid, "ACCEPT", "r")
    before = rs.stats()["actions_logged"]
    rs.build_queue([], None)
    assert rs.stats()["actions_logged"] == before and rs.state(iid) == "ACCEPTED"
