"""SQLite Entity Registry: canonical entities, aliases, mentions (separate), merge/alias history.

Rules enforced here:
 - entities are never merged because names look similar; merges are explicit, logged, idempotent;
 - identity-provider rows carry provider/source_url/fetched_at/identity_only=1 and are never edge sources;
 - mention rows are kept apart from entities and are upserted by a stable mention_id (rerun-safe)."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rapidfuzz import fuzz, process

from vckg.entity_linking.normalize import normalize_name, slugify
from vckg.models import EntityType, Mention, ResolutionStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities(
  entity_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, entity_type TEXT NOT NULL, name_key TEXT NOT NULL,
  ticker TEXT, tax_code TEXT, parent_entity_id TEXT, resolution_status TEXT NOT NULL,
  merged_into TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_entities_key ON entities(name_key);
CREATE TABLE IF NOT EXISTS aliases(
  entity_id TEXT NOT NULL, alias_text TEXT NOT NULL, alias_key TEXT NOT NULL, kind TEXT NOT NULL,
  source_type TEXT NOT NULL, provider TEXT, source_url TEXT, fetched_at TEXT, identity_only INTEGER NOT NULL DEFAULT 0,
  valid_from TEXT, valid_to TEXT, created_at TEXT NOT NULL,
  PRIMARY KEY(entity_id, alias_key, kind));
CREATE INDEX IF NOT EXISTS ix_alias_key ON aliases(alias_key);
CREATE TABLE IF NOT EXISTS identity_sources(
  entity_id TEXT NOT NULL, provider TEXT NOT NULL, source_url TEXT NOT NULL, fetched_at TEXT NOT NULL,
  identity_only INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(entity_id, provider, source_url));
CREATE TABLE IF NOT EXISTS mentions(
  mention_id TEXT PRIMARY KEY, article_id TEXT NOT NULL, span_start INTEGER NOT NULL, span_end INTEGER NOT NULL,
  surface_text TEXT NOT NULL, detected_type TEXT NOT NULL, candidate_entity_ids TEXT NOT NULL,
  entity_id TEXT, linking_method TEXT, linking_score REAL, ner_score REAL, resolution_status TEXT NOT NULL,
  updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_mentions_article ON mentions(article_id);
CREATE TABLE IF NOT EXISTS person_context(
  entity_id TEXT NOT NULL, org_entity_id TEXT NOT NULL, article_id TEXT NOT NULL,
  PRIMARY KEY(entity_id, org_entity_id, article_id));
CREATE TABLE IF NOT EXISTS history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, op TEXT NOT NULL, entity_id TEXT, other_entity_id TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS merge_rejections(
  entity_a TEXT NOT NULL, entity_b TEXT NOT NULL, reason TEXT, ts TEXT NOT NULL, PRIMARY KEY(entity_a, entity_b));
"""

ORG_TYPES = {EntityType.ORGANIZATION, EntityType.BANK, EntityType.REGULATOR, EntityType.GOVERNMENT_AGENCY}


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    method: str  # exact_canonical | alias | ticker | fuzzy
    score: float | None  # rapidfuzz ratio for fuzzy only
    alias_kind: str = ""


class RegistryStore:
    def __init__(self, path: str | Path = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self._fuzzy_keys: list[str] | None = None
        self.version = 0  # bumped whenever aliases/entities change (cache invalidation for scanners)

    # ---------- helpers ----------
    def _log(self, op: str, entity_id: str | None = None, other: str | None = None, **detail) -> None:
        self.db.execute("INSERT INTO history(ts,op,entity_id,other_entity_id,detail) VALUES(?,?,?,?,?)",
                        (now(), op, entity_id, other, json.dumps(detail, ensure_ascii=False)))

    @staticmethod
    def _is_person(t: EntityType) -> bool:
        return t == EntityType.PERSON

    def canonical_id(self, entity_id: str) -> str:
        seen = set()
        while entity_id not in seen:
            seen.add(entity_id)
            r = self.db.execute("SELECT merged_into FROM entities WHERE entity_id=?", (entity_id,)).fetchone()
            if not r or not r["merged_into"]:
                break
            entity_id = r["merged_into"]
        return entity_id

    def get_entity(self, entity_id: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM entities WHERE entity_id=?", (self.canonical_id(entity_id),)).fetchone()

    def count_entities(self, status: str | None = None, etype: str | None = None) -> int:
        q, a = "SELECT COUNT(*) FROM entities WHERE merged_into IS NULL", []
        if status:
            q += " AND resolution_status=?"
            a.append(status)
        if etype:
            q += " AND entity_type=?"
            a.append(etype)
        return self.db.execute(q, a).fetchone()[0]

    # ---------- write API ----------
    def add_entity(self, canonical_name: str, etype: EntityType, *, entity_id: str | None = None,
                   ticker: str | None = None, status: ResolutionStatus = ResolutionStatus.PROVISIONAL,
                   tax_code: str | None = None, parent_entity_id: str | None = None,
                   provider: str | None = None, source_url: str | None = None, fetched_at: str | None = None,
                   identity_only: bool = False, source_type: str = "article") -> tuple[str, bool]:
        """Idempotent. Organizations: same normalized canonical key (or same ticker) => same entity.
        Persons: only an explicit entity_id (identity cluster) is ever reused - never the bare name."""
        is_p = self._is_person(etype)
        key = normalize_name(canonical_name, is_person=is_p)
        if not key:
            raise ValueError("empty name key")
        if entity_id is None:
            if is_p:
                raise ValueError("person entities need an explicit identity-cluster entity_id")
            entity_id = f"org:{slugify(key)}"
        existing = self.db.execute("SELECT * FROM entities WHERE entity_id=?", (entity_id,)).fetchone()
        if (existing is not None and not is_p and ticker and existing["ticker"] and existing["ticker"] != ticker.upper()
                and existing["name_key"] == key):
            # same normalized name but a DIFFERENT verified ticker => different company; never merge by name
            entity_id = f"{entity_id}~{ticker.lower()}"
            existing = self.db.execute("SELECT * FROM entities WHERE entity_id=?", (entity_id,)).fetchone()
        if existing is None and not is_p and ticker:
            existing = self.db.execute("SELECT * FROM entities WHERE ticker=? AND merged_into IS NULL AND entity_type!='PERSON'",
                                       (ticker.upper(),)).fetchone()
        if existing is not None:
            eid = self.canonical_id(existing["entity_id"])
            self.add_alias(eid, canonical_name, "canonical", source_type=source_type, provider=provider,
                           source_url=source_url, fetched_at=fetched_at, identity_only=identity_only)
            if ticker:
                self.add_alias(eid, ticker.upper(), "ticker", source_type=source_type, provider=provider,
                               source_url=source_url, fetched_at=fetched_at, identity_only=identity_only)
                self.db.execute("UPDATE entities SET ticker=COALESCE(ticker,?) WHERE entity_id=?", (ticker.upper(), eid))
            if status == ResolutionStatus.VERIFIED and existing["resolution_status"] == "PROVISIONAL":
                self.db.execute("UPDATE entities SET resolution_status='VERIFIED', updated_at=? WHERE entity_id=?", (now(), eid))
                self._log("promote_verified", eid, provider=provider)
            self._record_identity(eid, provider, source_url, fetched_at, identity_only)
            self.db.commit()
            return eid, False
        t = now()
        self.db.execute("INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (entity_id, canonical_name, etype.value, key, ticker.upper() if ticker else None, tax_code,
                         parent_entity_id, status.value, None, t, t))
        self.add_alias(entity_id, canonical_name, "canonical", source_type=source_type, provider=provider,
                       source_url=source_url, fetched_at=fetched_at, identity_only=identity_only)
        if ticker:
            self.add_alias(entity_id, ticker.upper(), "ticker", source_type=source_type, provider=provider,
                           source_url=source_url, fetched_at=fetched_at, identity_only=identity_only)
        self._record_identity(entity_id, provider, source_url, fetched_at, identity_only)
        self._log("add_entity", entity_id, status=status.value, type=etype.value, source_type=source_type)
        self.db.commit()
        return entity_id, True

    def _record_identity(self, eid, provider, source_url, fetched_at, identity_only) -> None:
        if provider and source_url:
            self.db.execute("INSERT OR IGNORE INTO identity_sources VALUES(?,?,?,?,?)",
                            (eid, provider, source_url, fetched_at or now(), 1 if identity_only else 0))

    def add_alias(self, entity_id: str, alias: str, kind: str = "alias", *, source_type: str = "article",
                  provider: str | None = None, source_url: str | None = None, fetched_at: str | None = None,
                  identity_only: bool = False, valid_from: str | None = None, valid_to: str | None = None) -> bool:
        eid = self.canonical_id(entity_id)
        row = self.db.execute("SELECT entity_type FROM entities WHERE entity_id=?", (eid,)).fetchone()
        if row is None:
            raise KeyError(entity_id)
        is_p = row["entity_type"] == "PERSON"
        key = alias.upper() if kind == "ticker" else normalize_name(alias, is_person=is_p)
        if not key:
            return False
        cur = self.db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                              (eid, alias, key, kind, source_type, provider, source_url, fetched_at,
                               1 if identity_only else 0, valid_from, valid_to, now()))
        if cur.rowcount:
            self._fuzzy_keys = None
            self.version += 1
            self._log("add_alias", eid, alias=alias, kind=kind, source_type=source_type)
        self.db.commit()
        return bool(cur.rowcount)

    def record_mention(self, m: Mention, resolution_status: str | None = None) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO mentions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (m.mention_id, m.article_id, m.start, m.end, m.text, m.label.value, json.dumps(m.candidate_entity_ids),
             m.entity_id, m.linking_method, m.link_score, m.ner_score, resolution_status or m.link_status, now()))
        self.db.commit()

    def add_person_context(self, entity_id: str, org_entity_id: str, article_id: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO person_context VALUES(?,?,?)", (entity_id, org_entity_id, article_id))
        self.db.commit()

    # ---------- merge ----------
    def reject_merge(self, a: str, b: str, reason: str = "") -> None:
        a, b = sorted((self.canonical_id(a), self.canonical_id(b)))
        self.db.execute("INSERT OR IGNORE INTO merge_rejections VALUES(?,?,?,?)", (a, b, reason, now()))
        self._log("reject_merge", a, b, reason=reason)
        self.db.commit()

    def merge_rejected(self, a: str, b: str) -> bool:
        a, b = sorted((a, b))
        return self.db.execute("SELECT 1 FROM merge_rejections WHERE entity_a=? AND entity_b=?", (a, b)).fetchone() is not None

    def merge_entities(self, keep_id: str, drop_id: str, reason: str) -> bool:
        """Idempotent. Returns False when nothing changed (already merged / same / rejected / type clash)."""
        keep, drop = self.canonical_id(keep_id), self.canonical_id(drop_id)
        if keep == drop:
            return False
        if self.merge_rejected(keep, drop):
            return False
        k, d = self.get_entity(keep), self.get_entity(drop)
        if k is None or d is None or (k["entity_type"] == "PERSON") != (d["entity_type"] == "PERSON"):
            return False
        self.db.execute("UPDATE entities SET merged_into=?, updated_at=? WHERE entity_id=?", (keep, now(), drop))
        for r in self.db.execute("SELECT * FROM aliases WHERE entity_id=?", (drop,)).fetchall():
            self.db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (keep, r["alias_text"], r["alias_key"], r["kind"], r["source_type"], r["provider"], r["source_url"],
                             r["fetched_at"], r["identity_only"], r["valid_from"], r["valid_to"], r["created_at"]))
        self.db.execute("UPDATE mentions SET entity_id=? WHERE entity_id=?", (keep, drop))
        self.db.execute("INSERT OR IGNORE INTO person_context SELECT ?,org_entity_id,article_id FROM person_context WHERE entity_id=?", (keep, drop))
        self.db.execute("INSERT OR IGNORE INTO identity_sources SELECT ?,provider,source_url,fetched_at,identity_only FROM identity_sources WHERE entity_id=?", (keep, drop))
        order = {"REJECTED": -1, "AMBIGUOUS": 0, "PROVISIONAL": 1, "ARTICLE_GROUNDED": 2, "VERIFIED": 3}
        if order[d["resolution_status"]] > order[k["resolution_status"]]:
            self.db.execute("UPDATE entities SET resolution_status=? WHERE entity_id=?", (d["resolution_status"], keep))
        self._fuzzy_keys = None
        self.version += 1
        self._log("merge", keep, drop, reason=reason)
        self.db.commit()
        return True

    def set_status(self, entity_id: str, status: ResolutionStatus, reason: str) -> bool:
        """Upgrade only: PROVISIONAL -> ARTICLE_GROUNDED/VERIFIED, ARTICLE_GROUNDED -> VERIFIED. Never downgrades. Logged."""
        order = {"REJECTED": -1, "AMBIGUOUS": 0, "PROVISIONAL": 1, "ARTICLE_GROUNDED": 2, "VERIFIED": 3}
        eid = self.canonical_id(entity_id)
        cur = self.db.execute("SELECT resolution_status FROM entities WHERE entity_id=?", (eid,)).fetchone()
        if cur is None or order[status.value] <= order[cur[0]]:
            return False
        self.db.execute("UPDATE entities SET resolution_status=?, updated_at=? WHERE entity_id=?", (status.value, now(), eid))
        self._log("set_status", eid, old=cur[0], new=status.value, reason=reason)
        self.db.commit()
        return True

    def get_resolution_history(self, entity_id: str) -> list[dict]:
        rows = self.db.execute("SELECT ts,op,entity_id,other_entity_id,detail FROM history WHERE entity_id=? OR other_entity_id=? ORDER BY id",
                               (entity_id, entity_id)).fetchall()
        return [{**dict(r), "detail": json.loads(r["detail"] or "{}")} for r in rows]

    # ---------- candidate search ----------
    def _compatible(self, etype: EntityType, row_type: str) -> bool:
        t = EntityType(row_type)
        return t == etype or (t in ORG_TYPES and etype in ORG_TYPES)

    def find_candidates(self, surface: str, etype: EntityType, *, fuzzy_min: float = 93.0,
                        allow_ticker: bool = False) -> list[Candidate]:
        """All plausible entities for a surface, strongest method first. Never decides: resolver does."""
        is_p = self._is_person(etype)
        key = normalize_name(surface, is_person=is_p)
        out: dict[str, Candidate] = {}
        if key:
            for r in self.db.execute(
                "SELECT a.entity_id, a.kind, e.entity_type FROM aliases a JOIN entities e ON e.entity_id=a.entity_id "
                "WHERE a.alias_key=? AND e.merged_into IS NULL AND a.kind!='ticker' AND e.resolution_status!='REJECTED'", (key,)):
                if self._compatible(etype, r["entity_type"]):
                    m = "exact_canonical" if r["kind"] in ("canonical", "legal") else "alias"
                    out.setdefault(r["entity_id"], Candidate(r["entity_id"], m, None, r["kind"]))
        if allow_ticker and not is_p:
            for r in self.db.execute(
                "SELECT a.entity_id, e.entity_type FROM aliases a JOIN entities e ON e.entity_id=a.entity_id "
                "WHERE a.kind='ticker' AND a.alias_key=? AND e.merged_into IS NULL", (surface.strip().upper(),)):
                if self._compatible(etype, r["entity_type"]):
                    out.setdefault(r["entity_id"], Candidate(r["entity_id"], "ticker", None, "ticker"))
        if not out and not is_p and key and len(key) >= 5 and fuzzy_min < 100:
            for eid, score in self._fuzzy(key, etype, fuzzy_min):
                out.setdefault(eid, Candidate(eid, "fuzzy", float(score), "alias"))
        return sorted(out.values(), key=lambda c: (c.method != "exact_canonical", c.method != "alias",
                                                   -(c.score or 0), c.entity_id))

    def _fuzzy(self, key: str, etype: EntityType, minimum: float) -> list[tuple[str, float]]:
        if self._fuzzy_keys is None:
            self._fuzzy_keys = [r[0] for r in self.db.execute(
                "SELECT DISTINCT a.alias_key FROM aliases a JOIN entities e ON e.entity_id=a.entity_id "
                "WHERE a.kind!='ticker' AND e.entity_type!='PERSON' AND e.merged_into IS NULL")]
        res = process.extract(key, self._fuzzy_keys, scorer=fuzz.token_sort_ratio, limit=5, score_cutoff=minimum)
        out: list[tuple[str, float]] = []
        for k, score, _ in res:
            for r in self.db.execute("SELECT e.entity_id, e.entity_type FROM aliases a JOIN entities e ON e.entity_id=a.entity_id "
                                     "WHERE a.alias_key=? AND e.merged_into IS NULL", (k,)):
                if self._compatible(etype, r["entity_type"]):
                    out.append((r["entity_id"], score))
        return out

    def stats(self) -> dict:
        q = lambda s: self.db.execute(s).fetchone()[0]
        return {
            "entities_active": q("SELECT COUNT(*) FROM entities WHERE merged_into IS NULL"),
            "by_status": {r[0]: r[1] for r in self.db.execute("SELECT resolution_status,COUNT(*) FROM entities WHERE merged_into IS NULL GROUP BY 1")},
            "by_type": {r[0]: r[1] for r in self.db.execute("SELECT entity_type,COUNT(*) FROM entities WHERE merged_into IS NULL GROUP BY 1")},
            "aliases": q("SELECT COUNT(*) FROM aliases"),
            "identity_only_aliases": q("SELECT COUNT(*) FROM aliases WHERE identity_only=1"),
            "mentions": q("SELECT COUNT(*) FROM mentions"),
            "merges": q("SELECT COUNT(*) FROM history WHERE op='merge'"),
        }

    def close(self) -> None:
        self.db.close()




