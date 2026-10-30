"""Human edge review (Phase 5 / Task E). Local, SQLite-backed, append-only history, CSV round-trip.

Principles
 * A human decision never replaces evidence: ACCEPT/CORRECT only promote an edge when it has >=1 valid press evidence record
   (url + article + text that matches the stored article when a staging DB is supplied) and non-negated status.
 * HUMAN_VERIFIED means "a reviewer agreed that the press evidence supports the relation as stated"; it is NOT proof of the
   real-world event, and it cannot hide an identity problem: ACCEPT is refused while an endpoint is PROVISIONAL/AMBIGUOUS
   (use CORRECT to supply a resolved entity id, or leave it pending).
 * Actions are idempotent: re-importing the same action is a no-op; every change keeps reviewer, timestamp, original and
   revised values and a note.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from vckg.metrics import edge_event_key
from vckg.models import Edge, EvidenceRecord, FactualStatus, ReviewStatus

ACTIONS = {"ACCEPT", "REJECT", "CORRECT", "UNSURE", "DUPLICATE"}
OFFICIAL_OK = {"FACT", "HISTORICAL", "ENDED"}
IDENTITY_OK = {"VERIFIED", "ARTICLE_GROUNDED"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS review_items(
  item_id TEXT PRIMARY KEY, run TEXT, origin TEXT, priority INTEGER, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review_actions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL, ts TEXT NOT NULL, reviewer TEXT NOT NULL, action TEXT NOT NULL,
  original TEXT NOT NULL, revised TEXT NOT NULL, note TEXT, sig TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_actions_item ON review_actions(item_id);
"""
CSV_COLUMNS = [
    "item_id", "priority", "origin", "run", "subject_id", "subject_name", "subject_surfaces", "subject_identity", "predicate",
    "object_id", "object_name", "object_surfaces", "object_identity", "factual_status", "qwen_valid", "qwen_status", "reasons",
    "evidence_count", "source_url", "evidence_text",
    "action", "reviewer", "note", "corrected_subject_id", "corrected_predicate", "corrected_object_id", "corrected_status",
]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def edge_id(subject: str, predicate: str, obj: str) -> str:
    return hashlib.sha1(f"{subject}|{predicate}|{obj}".encode()).hexdigest()[:16]


def _read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


class ReviewStore:
    def __init__(self, path: str | Path = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ------------------------------------------------------------------ queue
    def build_queue(self, run_dirs: list[Path], registry_db: str | Path | None = None, include_official: bool = False) -> dict:
        names, statuses = {}, {}
        if registry_db and Path(registry_db).exists():
            r = sqlite3.connect(str(registry_db))
            for eid, name, st in r.execute("SELECT entity_id, canonical_name, resolution_status FROM entities"):
                names[eid], statuses[eid] = name, st
            r.close()
        items: dict[str, dict] = {}
        for d in run_dirs:
            surf: dict[str, set] = {}
            outcomes: dict[tuple, dict] = {}
            oc = d / "candidate_outcomes.csv"
            if oc.exists():
                for row in csv.DictReader(oc.open(encoding="utf-8-sig")):
                    for side in ("subject", "object"):
                        if row[f"{side}_entity"]:
                            surf.setdefault(row[f"{side}_entity"], set()).add(row[f"{side}_text"])
                    outcomes.setdefault((row["subject_entity"], row["predicate"], row["object_entity"]), row)
                    outcomes.setdefault((row["object_entity"], row["predicate"], row["subject_entity"]), row)
            files = [("candidate", "relations_candidate.jsonl")] + ([("official", "relations_official.jsonl")] if include_official else [])
            for origin, fname in files:
                for e in _read(d / fname):
                    k = (e["subject_id"], e["predicate"], e["object_id"])
                    row = outcomes.get(k, {})
                    ev = e["evidence"]
                    reasons = sorted({x for r in ev for x in r.get("validation_status", "").replace("CANDIDATE:", "").split(";")[0].split(",") if x and x != "ACCEPTED"})
                    it = items.setdefault(edge_id(*k), {
                        "origin": origin, "run": d.name, "subject_id": k[0], "predicate": k[1], "object_id": k[2],
                        "subject_name": names.get(k[0], k[0]), "object_name": names.get(k[2], k[2]),
                        "subject_identity": statuses.get(k[0], ""), "object_identity": statuses.get(k[2], ""),
                        "subject_surfaces": sorted(surf.get(k[0], []))[:4], "object_surfaces": sorted(surf.get(k[2], []))[:4],
                        "factual_status": ev[0]["factual_status"] if ev else "", "qwen_valid": row.get("llm_valid", ""),
                        "qwen_status": row.get("llm_status", ""), "reasons": reasons, "evidence": ev})
                    if it["origin"] == "official" and origin == "candidate":
                        continue
        # priority classes (first match): 1 complete+clear endpoints, 2 only external identity missing, 3 repeated entity, 4 doubt
        cnt: dict[str, int] = {}
        for it in items.values():
            for s in (it["subject_id"], it["object_id"]):
                cnt[s] = cnt.get(s, 0) + 1
        doubt = {"COREF_REVIEW", "INVALID_DIRECTION", "NON_FACTUAL_RELATION", "SPAN_BOUNDARY_SUSPECT", "NOT_VERIFIED"}
        n_new = 0
        for iid, it in items.items():
            rs = set(it["reasons"])
            if it["origin"] == "official":
                pri = 5  # audit sample of already-official edges
            elif it["subject_identity"] in IDENTITY_OK and it["object_identity"] in IDENTITY_OK and not (rs & doubt):
                pri = 1
            elif rs == {"ENDPOINT_NOT_VERIFIED"}:
                pri = 2
            elif max(cnt[it["subject_id"]], cnt[it["object_id"]]) >= 2 and not (rs & doubt):
                pri = 3
            else:
                pri = 4
            cur = self.db.execute("SELECT 1 FROM review_items WHERE item_id=?", (iid,)).fetchone()
            payload = json.dumps(it, ensure_ascii=False)
            if cur is None:
                self.db.execute("INSERT INTO review_items VALUES(?,?,?,?,?,?)", (iid, it["run"], it["origin"], pri, payload, _now()))
                n_new += 1
            else:  # refresh payload/priority only; actions are never touched
                self.db.execute("UPDATE review_items SET payload=?, priority=? WHERE item_id=?", (payload, pri, iid))
        self.db.commit()
        return {"items_total": self.db.execute("SELECT COUNT(*) FROM review_items").fetchone()[0], "new": n_new,
                "by_priority": {r[0]: r[1] for r in self.db.execute("SELECT priority, COUNT(*) FROM review_items GROUP BY 1 ORDER BY 1")}}

    def item(self, item_id: str) -> dict:
        r = self.db.execute("SELECT * FROM review_items WHERE item_id=?", (item_id,)).fetchone()
        if r is None:
            raise KeyError(item_id)
        return {**json.loads(r["payload"]), "item_id": item_id, "priority": r["priority"]}

    def queue(self, only_pending: bool = True, limit: int | None = None) -> list[dict]:
        out = []
        for r in self.db.execute("SELECT item_id FROM review_items ORDER BY priority, item_id"):
            st = self.state(r[0])
            if only_pending and st not in ("PENDING", "UNSURE"):
                continue
            out.append(self.item(r[0]))
        out.sort(key=lambda x: (x["priority"], -len(x["evidence"]), x["item_id"]))
        return out[:limit] if limit else out

    # ------------------------------------------------------------------ actions
    def history(self, item_id: str) -> list[dict]:
        return [{**dict(r), "original": json.loads(r["original"]), "revised": json.loads(r["revised"])}
                for r in self.db.execute("SELECT * FROM review_actions WHERE item_id=? ORDER BY id", (item_id,))]

    def state(self, item_id: str) -> str:
        h = self.history(item_id)
        return {"ACCEPT": "ACCEPTED", "REJECT": "REJECTED", "CORRECT": "CORRECTED", "UNSURE": "UNSURE", "DUPLICATE": "DUPLICATE"}[h[-1]["action"]] if h else "PENDING"

    def act(self, item_id: str, action: str, reviewer: str, note: str = "", revised: dict | None = None,
            staging=None, registry_statuses: dict | None = None) -> dict:
        """Apply one review action. Returns {'applied': bool, 'reason': str}. Refusals never raise (CSV import continues)."""
        action = action.upper().strip()
        if action not in ACTIONS:
            return {"applied": False, "reason": f"unknown action {action}"}
        if not reviewer.strip():
            return {"applied": False, "reason": "reviewer required"}
        it = self.item(item_id)
        revised = {k: v for k, v in (revised or {}).items() if v not in (None, "")}
        original = {k: it[k] for k in ("subject_id", "predicate", "object_id", "factual_status")}
        if action in ("ACCEPT", "CORRECT"):
            bad = self._evidence_problem(it, staging)
            if bad:
                return {"applied": False, "reason": bad}
            status = revised.get("factual_status", it["factual_status"])
            if status not in OFFICIAL_OK:
                return {"applied": False, "reason": f"status {status} cannot become official (planned/alleged/denied stays candidate)"}
        if action == "ACCEPT":
            for side in ("subject", "object"):
                if it[f"{side}_identity"] not in IDENTITY_OK:
                    return {"applied": False, "reason": f"{side} identity is {it[f'{side}_identity'] or 'unknown'}: review cannot override identity; use CORRECT with a resolved entity id"}
        if action == "CORRECT":
            if not revised:
                return {"applied": False, "reason": "CORRECT needs at least one corrected field"}
            for fld in ("subject_id", "object_id"):
                if fld in revised and registry_statuses is not None and registry_statuses.get(revised[fld]) not in IDENTITY_OK:
                    return {"applied": False, "reason": f"{fld} {revised[fld]} is not a VERIFIED/ARTICLE_GROUNDED registry entity"}
        sig = hashlib.sha1(json.dumps([item_id, reviewer, action, original, revised, note], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        last = self.db.execute("SELECT sig FROM review_actions WHERE item_id=? AND reviewer=? ORDER BY id DESC LIMIT 1", (item_id, reviewer)).fetchone()
        if last and last["sig"] == sig:
            return {"applied": False, "reason": "duplicate (idempotent no-op)"}
        self.db.execute("INSERT INTO review_actions(item_id,ts,reviewer,action,original,revised,note,sig) VALUES(?,?,?,?,?,?,?,?)",
                        (item_id, _now(), reviewer, action, json.dumps(original, ensure_ascii=False), json.dumps(revised, ensure_ascii=False), note, sig))
        self.db.commit()
        return {"applied": True, "reason": ""}

    @staticmethod
    def _evidence_problem(it: dict, staging) -> str:
        ev = it["evidence"]
        if not ev:
            return "no evidence record"
        ok = False
        for r in ev:
            if not (r.get("source_url") and r.get("article_id") and r.get("evidence_text")):
                continue
            if staging is not None:
                arts = {a.article_id: a for a in staging.get_articles()} if not hasattr(staging, "_cache") else staging._cache
                staging._cache = arts
                from vckg.preprocessing.text import normalize_text
                a = arts.get(r["article_id"])
                if a is None or normalize_text(a.text)[r["evidence_start"]:r["evidence_end"]] != r["evidence_text"]:
                    continue
            ok = True
        return "" if ok else "no valid press evidence (url/article/text mismatch)"

    # ------------------------------------------------------------------ outputs
    def human_edges(self) -> list[Edge]:
        """Effective HUMAN_VERIFIED edges (ACCEPT or CORRECT as latest action). Corrections swap/replace fields; evidence is kept
        unchanged so provenance stays traceable to the press text."""
        out: dict[tuple, Edge] = {}
        for r in self.db.execute("SELECT item_id FROM review_items"):
            h = self.history(r[0])
            if not h or h[-1]["action"] not in ("ACCEPT", "CORRECT"):
                continue
            it, last = self.item(r[0]), h[-1]
            rev = last["revised"]
            s, p, o = rev.get("subject_id", it["subject_id"]), rev.get("predicate", it["predicate"]), rev.get("object_id", it["object_id"])
            if rev.get("direction") == "SWAP":
                s, o = o, s
            status = FactualStatus(rev.get("factual_status", it["factual_status"]))
            ev = []
            for e in it["evidence"]:
                d = dict(e)
                d.update(review_status=ReviewStatus.HUMAN_VERIFIED.value, factual_status=status.value,
                         validation_status=f"HUMAN:{last['action']}:{last['reviewer']}")
                ev.append(EvidenceRecord.model_validate(d))
            edge = out.setdefault((s, p, o), Edge(subject_id=s, predicate=p, object_id=o))
            edge.evidence += [x for x in ev if (x.article_id, x.evidence_start, x.evidence_end) not in {(y.article_id, y.evidence_start, y.evidence_end) for y in edge.evidence}]
        return list(out.values())

    def stats(self) -> dict:
        states: dict[str, int] = {}
        for r in self.db.execute("SELECT item_id FROM review_items"):
            st = self.state(r[0])
            states[st] = states.get(st, 0) + 1
        return {"items": sum(states.values()), "by_state": states, "actions_logged": self.db.execute("SELECT COUNT(*) FROM review_actions").fetchone()[0],
                "human_verified_unique_edges": len(self.human_edges())}

    # ------------------------------------------------------------------ CSV round-trip
    def export_csv(self, path: str | Path, only_pending: bool = True, limit: int | None = None) -> int:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        rows = self.queue(only_pending, limit)
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            w.writeheader()
            for it in rows:
                ev0 = it["evidence"][0] if it["evidence"] else {}
                w.writerow({"item_id": it["item_id"], "priority": it["priority"], "origin": it["origin"], "run": it["run"],
                            "subject_id": it["subject_id"], "subject_name": it["subject_name"], "subject_surfaces": " | ".join(it["subject_surfaces"]),
                            "subject_identity": it["subject_identity"], "predicate": it["predicate"], "object_id": it["object_id"],
                            "object_name": it["object_name"], "object_surfaces": " | ".join(it["object_surfaces"]), "object_identity": it["object_identity"],
                            "factual_status": it["factual_status"], "qwen_valid": it["qwen_valid"], "qwen_status": it["qwen_status"],
                            "reasons": ",".join(it["reasons"]), "evidence_count": len(it["evidence"]), "source_url": ev0.get("source_url", ""),
                            "evidence_text": ev0.get("evidence_text", "")})
        return len(rows)

    def import_csv(self, path: str | Path, default_reviewer: str = "", staging=None, registry_db: str | Path | None = None) -> dict:
        reg = None
        if registry_db and Path(registry_db).exists():
            r = sqlite3.connect(str(registry_db))
            reg = {a: b for a, b in r.execute("SELECT entity_id, resolution_status FROM entities")}
            r.close()
        res = {"applied": 0, "skipped": 0, "refused": []}
        with Path(path).open(encoding="utf-8-sig") as fh:
            rows_in = list(csv.DictReader(fh))
        for row in rows_in:
            if not row.get("action", "").strip():
                res["skipped"] += 1
                continue
            revised = {"subject_id": row.get("corrected_subject_id", "").strip(), "predicate": row.get("corrected_predicate", "").strip(),
                       "object_id": row.get("corrected_object_id", "").strip(), "factual_status": row.get("corrected_status", "").strip().upper()}
            out = self.act(row["item_id"], row["action"], row.get("reviewer", "").strip() or default_reviewer, row.get("note", ""), revised, staging, reg)
            if out["applied"]:
                res["applied"] += 1
            elif "idempotent" in out["reason"]:
                res["skipped"] += 1
            else:
                res["refused"].append({"item_id": row["item_id"], "reason": out["reason"]})
        return res


def edge_unique_key(e: dict) -> tuple:
    return edge_event_key(e)
