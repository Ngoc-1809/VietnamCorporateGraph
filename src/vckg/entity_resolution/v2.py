"""Global Entity Resolution v2 - pipeline (Candidate Generation -> Evidence Retrieval -> Identity Verification -> Canonical Mapping -> Graph V2).

  python -m vckg.entity_resolution.v2 run --snapshot data/graph_preview/20261102-143350 [--out data/entity_resolution/v2] [--qwen-budget 1000] [--no-qwen]
  python -m vckg.entity_resolution.v2 status [--out ...]        (STOP = file <out>/STOP; resume = run again: finished stages are skipped, --force-stage X redoes X onwards)

Read-only over: the snapshot copy of the aggregate, the cumulative registry, the master staging DB (article text). Writes ONLY under <out>. QA tiers are never changed: the V2 graph is
rebuilt from src_edges/src_evidence with an entity mapping applied at each endpoint; edges are de-duplicated per (tier, subject, predicate, object, status, window) and all evidence is
kept. Mapping rows carry decision, reason, method, evidence, confidence METADATA (rule scores, never probabilities), conflicts, version and a watermark."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import httpx

from vckg.entity_resolution.core import (
    ORG_TYPES,
    RELATED_PREDS,
    STATUS_RANK,
    UF,
    VALIDATED,
    VERSION,
    Verdict,
    World,
    article_date,
    best_date,
    birth_conflict,
    class_conflict,
    fold1,
    fold_name,
    is_agency_name,
    is_generic_org,
    json_dumps,
    left_chain,
    legal_conflict,
    load_world,
    mk_tokens,
    person_context,
    person_key,
    person_key_org,
    person_name_ok,
    prior_map,
    role_family,
)
from vckg.jobs.pipeline_worker import Status, now

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/entity_resolution/v2"
REGISTRY = ROOT / "data/campaign/mass/registry_cumulative.sqlite"
STAGING = ROOT / "data/staging/staging.sqlite"
STAGES = ["corpus", "org", "person", "qwen", "ut", "build"]
KEYWORDS = r"(?:co phieu|ma ck|ma chung khoan|ma|hose|hnx|upcom|cp)"
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS stages(name TEXT PRIMARY KEY, status TEXT, started_at TEXT, finished_at TEXT, stats TEXT);
CREATE TABLE IF NOT EXISTS org_pairs(a TEXT, b TEXT, decision TEXT, reason TEXT, evidence TEXT, meta TEXT, conflicts TEXT, PRIMARY KEY(a,b));
CREATE TABLE IF NOT EXISTS person_pairs(a TEXT, b TEXT, decision TEXT, reason TEXT, evidence TEXT, meta TEXT, conflicts TEXT, llm INTEGER DEFAULT 0, PRIMARY KEY(a,b));
CREATE TABLE IF NOT EXISTS person_facts(key TEXT PRIMARY KEY, article_id TEXT, pub TEXT, found INTEGER, gender TEXT, birth INTEGER, relative INTEGER, snippet TEXT);
CREATE TABLE IF NOT EXISTS ut_links(key TEXT PRIMARY KEY, decision TEXT, reason TEXT, target TEXT, evidence TEXT, meta TEXT);
CREATE TABLE IF NOT EXISTS entity_map(original_key TEXT PRIMARY KEY, canonical_id TEXT NOT NULL, kind TEXT, decision TEXT, reason TEXT, method TEXT, evidence TEXT, confidence_meta TEXT,
  conflicts TEXT, version TEXT, watermark TEXT);
CREATE TABLE IF NOT EXISTS merge_clusters(canonical_id TEXT PRIMARY KEY, kind TEXT, n_members INTEGER, members TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS llm_cache(key TEXT PRIMARY KEY, response TEXT, seconds REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS llm_log(pair_a TEXT, pair_b TEXT, verdict TEXT, accepted TEXT, reason TEXT, live INTEGER, seconds REAL);
"""


class Stop(Exception):
    pass


class Run:
    def __init__(self, snapshot: Path, out: Path = OUT, qwen_budget: int = 1000, use_qwen: bool = True, registry: Path = REGISTRY, staging: Path = STAGING, install_status: bool = True):
        self.snapshot, self.out = Path(snapshot), Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.registry, self.staging = Path(registry), Path(staging)
        self.qwen_budget, self.use_qwen = qwen_budget, use_qwen
        self.db = sqlite3.connect(str(self.out / "er_v2.sqlite"), timeout=60)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.status = Status(self.out / "status.json", "er-v2") if install_status else None
        self.world: World | None = None
        self.reg = None
        self.snap_db = self.snapshot / "snapshot" / "staging_graph.sqlite"
        self.org_uf, self.person_uf = UF(), UF()
        self.t0 = time.time()

    # ------------------------------------------------------------------ infra
    def stop_requested(self) -> bool:
        return (self.out / "STOP").exists()

    def check(self) -> None:
        if self.stop_requested():
            raise Stop()

    def meta(self, k: str, default=None):
        r = self.db.execute("SELECT value FROM meta WHERE key=?", (k,)).fetchone()
        return json.loads(r[0]) if r else default

    def set_meta(self, k: str, v) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, json.dumps(v, ensure_ascii=False)))

    def upd(self, **kw) -> None:
        if self.status:
            self.status.update(**kw)

    def stage_done(self, name: str) -> bool:
        r = self.db.execute("SELECT status FROM stages WHERE name=?", (name,)).fetchone()
        return bool(r and r[0] == "DONE")

    def mark_stage(self, name: str, status: str, stats: dict | None = None) -> None:
        with self.db:
            if status == "RUNNING":
                self.db.execute("INSERT OR REPLACE INTO stages VALUES(?,?,?,NULL,NULL)", (name, status, now()))
            else:
                self.db.execute("UPDATE stages SET status=?, finished_at=?, stats=? WHERE name=?", (status, now(), json_dumps(stats or {}), name))

    def watermark(self) -> dict:
        w = self.load()
        srcs = sorted({e["source_id"] for e in w.edges})
        h = hashlib.sha1(json.dumps([srcs, len(w.edges)]).encode()).hexdigest()[:12]
        meta = json.loads((self.snapshot / "snapshot.json").read_text(encoding="utf-8")) if (self.snapshot / "snapshot.json").exists() else {}
        return {"snapshot_id": meta.get("snapshot_id", self.snapshot.name), "taken_at": meta.get("taken_at"), "articles_nlp_processed": meta.get("articles_nlp_processed"),
                "chunk_sources": [s for s in srcs if s.startswith("job:camp-c")][-1] if any(s.startswith("job:camp-c") for s in srcs) else None, "n_sources": len(srcs), "n_src_edges": len(w.edges), "sources_hash": h}

    def load(self) -> World:
        if self.world is None:
            self.world = load_world(self.snap_db)
            r = sqlite3.connect(f"file:{self.registry.as_posix()}?mode=ro", uri=True, timeout=60)
            r.row_factory = sqlite3.Row
            self.reg = r
        return self.world

    # ------------------------------------------------------------------ stage: corpus FTS
    def stage_corpus(self) -> dict:
        path = self.out / "corpus_fts.sqlite"
        c = sqlite3.connect(str(path))
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(text, tokenize='unicode61')")
        c.execute("CREATE TABLE IF NOT EXISTS docmap(rowid INTEGER PRIMARY KEY, article_id TEXT UNIQUE, url TEXT, pub TEXT)")
        have = c.execute("SELECT COUNT(*) FROM docmap").fetchone()[0]
        s = sqlite3.connect(f"file:{self.staging.as_posix()}?mode=ro", uri=True, timeout=60)
        total = s.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        n = 0
        if have < total:
            known = {r[0] for r in c.execute("SELECT article_id FROM docmap")}
            batch = []
            for aid, url, text, pub in s.execute("SELECT article_id, url, text, published_at FROM articles ORDER BY article_id"):
                if aid in known:
                    continue
                batch.append((aid, url, fold1(text), pub))
                if len(batch) >= 500:
                    n += self._fts_flush(c, batch)
                    batch = []
                    self.check()
                    self.upd(stage="corpus", indexed=have + n)
            n += self._fts_flush(c, batch)
        cnt = c.execute("SELECT COUNT(*) FROM docmap").fetchone()[0]
        c.commit()
        c.close()
        s.close()
        return {"articles_indexed": cnt, "added_now": n, "fts": str(path)}

    @staticmethod
    def _fts_flush(c, batch) -> int:
        for aid, url, ftext, pub in batch:
            cur = c.execute("INSERT INTO docs(text) VALUES(?)", (ftext,))
            c.execute("INSERT INTO docmap(rowid, article_id, url, pub) VALUES(?,?,?,?)", (cur.lastrowid, aid, url, pub))
        c.commit()
        return len(batch)

    def fts(self):
        if not hasattr(self, "_fts"):
            self._fts = sqlite3.connect(f"file:{(self.out / 'corpus_fts.sqlite').as_posix()}?mode=ro", uri=True)
        return self._fts

    def fts_articles(self, *phrases: str, limit: int = 400) -> list[tuple[int, str, str]]:
        q = " AND ".join('"' + p.replace('"', "") + '"' for p in phrases if p)
        if not q:
            return []
        try:
            rows = self.fts().execute("SELECT d.rowid, m.article_id, d.text FROM docs d JOIN docmap m ON m.rowid=d.rowid WHERE docs MATCH ? LIMIT ?", (q, limit)).fetchall()
        except sqlite3.OperationalError:
            return []
        return rows

    def original_text(self, article_id: str) -> str:
        if not hasattr(self, "_stg"):
            self._stg = sqlite3.connect(f"file:{self.staging.as_posix()}?mode=ro", uri=True, timeout=60)
        r = self._stg.execute("SELECT text FROM articles WHERE article_id=?", (article_id,)).fetchone()
        return r[0] if r else ""

    # ------------------------------------------------------------------ registry helpers
    def reg_info(self, ids: list[str]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            ph = ",".join("?" * len(part))
            for r in self.reg.execute(f"SELECT entity_id, canonical_name, entity_type, name_key, ticker, resolution_status, merged_into FROM entities WHERE entity_id IN ({ph})", part):
                out[r["entity_id"]] = {**dict(r), "aliases": []}
            for r in self.reg.execute(f"SELECT entity_id, alias_key, kind, source_type FROM aliases WHERE entity_id IN ({ph})", part):
                if r["entity_id"] in out:
                    out[r["entity_id"]]["aliases"].append((r["alias_key"], r["kind"], r["source_type"]))
        return out

    # ------------------------------------------------------------------ stage: organisations
    def org_keys(self) -> list[str]:
        w = self.load()
        return sorted(k for k, e in w.ents.items() if e.etype in ORG_TYPES)

    def org_universe(self):
        """(keys, base, info): graph organisations plus ALIAS-LINKED registry entities that are not graph nodes (VERIFIED / ARTICLE_GROUNDED only; added as degree-0 virtual entities so that
        short names can be tied to the registry's legal identity). Deterministic; cached."""
        if getattr(self, "_org_univ", None):
            return self._org_univ
        from vckg.entity_resolution.core import Ent
        w = self.load()
        keys = self.org_keys()
        base = {k: k.split("@")[0] for k in keys}
        info = self.reg_info(sorted(set(base.values())))
        own = set()
        for k in keys:
            ri = info.get(base[k])
            own |= {fold_name(w.ents[k].name)} | ({ri["name_key"], fold_name(ri["canonical_name"])} if ri else set())
        own = sorted(x for x in own if x and not is_generic_org(x))
        ext: dict[str, dict] = {}
        for i in range(0, len(own), 400):
            part = own[i:i + 400]
            ph = ",".join("?" * len(part))
            for r in self.reg.execute(f"SELECT DISTINCT e.entity_id, e.canonical_name, e.entity_type, e.name_key, e.ticker, e.resolution_status, e.merged_into FROM aliases a JOIN entities e ON e.entity_id=a.entity_id "
                                      f"WHERE a.alias_key IN ({ph}) AND e.merged_into IS NULL AND e.resolution_status IN ('VERIFIED','EXTERNAL_VERIFIED','ARTICLE_GROUNDED')", part):
                if r["entity_id"] not in w.ents and r["entity_type"] in ORG_TYPES:
                    ext[r["entity_id"]] = dict(r)
        extra = self.reg_info(sorted(ext))
        for eid in sorted(ext):
            r = ext[eid]
            w.ents.setdefault(eid, Ent(eid, r["canonical_name"], r["entity_type"], r["resolution_status"]))
            keys.append(eid)
            base[eid] = eid
            info[eid] = extra.get(eid, {**r, "aliases": []})
        self._org_univ = (keys, base, info)
        return self._org_univ

    def related_between(self, a: str, b: str) -> list[str]:
        w = self.load()
        out = set()
        for i in w.adj.get(a, ()):
            e = w.edges[i]
            if {e["s_key"], e["o_key"]} == {a, b} and e["predicate"] in RELATED_PREDS:
                out.add(e["predicate"])
        return sorted(out)

    def stage_org(self) -> dict:
        w = self.load()
        keys, base, info = self.org_universe()
        idx: dict[str, set[str]] = defaultdict(set)
        for k in keys:
            ri = info.get(base[k])
            names = {fold_name(w.ents[k].name)}
            if ri:
                names |= {ri["name_key"], fold_name(ri["canonical_name"])} | {a[0] for a in ri["aliases"]}
            for n in names:
                if n:
                    idx[n].add(k)
        cand: dict[tuple, set] = defaultdict(set)
        for k in keys:
            ri = info.get(base[k])
            own = {fold_name(w.ents[k].name)} | ({ri["name_key"], fold_name(ri["canonical_name"])} if ri else set())
            for n in own:
                if not n or is_generic_org(n):
                    continue
                for o in idx.get(n, ()):
                    if o != k:
                        cand[tuple(sorted((k, o)))].add("name_or_alias")
        # exact normalised-name groups
        byname: dict[str, list[str]] = defaultdict(list)
        for k in keys:
            ri = info.get(base[k])
            if ri and ri["name_key"] and not is_generic_org(ri["name_key"]):
                byname[ri["name_key"]].append(k)
        for ks in byname.values():
            for a, b in combinations(sorted(ks), 2):
                cand[(a, b)].add("same_name_key")
        self.upd(stage="org", org_candidates=len(cand))
        pairs = sorted(cand)
        decisions: dict[tuple, Verdict] = {}
        for n, (a, b) in enumerate(pairs):
            if n % 25 == 0:
                self.check()
                self.upd(stage="org", org_pairs_done=n, org_pairs_total=len(pairs))
            decisions[(a, b)] = self.verify_org_pair(a, b, info, base, cand[(a, b)])
        # competing: a short entity with verified partners that are both VERIFIED identities
        partners: dict[str, list[tuple]] = defaultdict(list)
        for (a, b), v in decisions.items():
            if v.decision == "VERIFIED_MERGE":
                for x, y in ((a, b), (b, a)):
                    partners[x].append((x, y))
        for x, lst in partners.items():
            ver = [p for p in lst if info.get(base[p[1]], {}).get("resolution_status") in ("VERIFIED", "EXTERNAL_VERIFIED")]
            if len(ver) > 1:
                for p in lst:
                    k = tuple(sorted(p))
                    v = decisions[k]
                    if v.decision == "VERIFIED_MERGE":
                        decisions[k] = Verdict("AMBIGUOUS", "COMPETING_VERIFIED_IDENTITIES", v.evidence, v.meta, v.conflicts + [f"{x} has verified evidence for {len(ver)} different VERIFIED identities"])
        # cluster
        uf = UF()
        order = sorted((k for k, v in decisions.items() if v.decision == "VERIFIED_MERGE"), key=lambda k: (-decisions[k].meta.get("articles", 0), k))
        distinct = {k for k, v in decisions.items() if v.decision == "DISTINCT"}
        rejected = 0
        for a, b in order:
            ra, rb = uf.find(a), uf.find(b)
            if ra == rb:
                continue
            ma = [m for m, r in ((m, uf.find(m)) for m in set(uf.p) | set(uf.p.values()) | {a}) if r == ra] or [a]
            mb = [m for m, r in ((m, uf.find(m)) for m in set(uf.p) | set(uf.p.values()) | {b}) if r == rb] or [b]
            bad = [x for x in ma for y in mb if tuple(sorted((x, y))) in distinct]
            nver = {base[m] for m in ma + mb if info.get(base[m], {}).get("resolution_status") in ("VERIFIED", "EXTERNAL_VERIFIED")}
            related = [(x, y) for x in ma for y in mb if self.related_between(x, y)]
            if related:
                bad = bad or related
            if bad or len(nver) > 1:
                rejected += 1
                v = decisions[(a, b)]
                decisions[(a, b)] = Verdict("AMBIGUOUS", "CLUSTER_CONSTRAINT", v.evidence, v.meta, v.conflicts + ["cluster would contain a DISTINCT pair, two VERIFIED identities, or a parent/child/counterparty pair joined through other members"])
                continue
            uf.union(a, b, self.pick_rep(ma + mb, info, base))
        with self.db:
            self.db.execute("DELETE FROM org_pairs")
            for (a, b), v in decisions.items():
                self.db.execute("INSERT INTO org_pairs VALUES(?,?,?,?,?,?,?)", (a, b, v.decision, v.reason, json_dumps(v.evidence[:4]), json_dumps(v.meta), json_dumps(v.conflicts)))
        self.org_uf = uf
        c = Counter(v.decision for v in decisions.values())
        cl = uf.members()
        return {"candidates": len(pairs), "decisions": dict(c), "reasons": {f"{d}/{r}": n for (d, r), n in Counter((v.decision, v.reason) for v in decisions.values()).most_common(25)}, "org_clusters": len(cl),
                "orgs_merged_away": sum(len(m) - 1 for m in cl.values()), "cluster_constraint_rejections": rejected}

    def pick_rep(self, members: list[str], info: dict, base: dict) -> str:
        w = self.load()
        return min(set(members), key=lambda m: (-STATUS_RANK.get(info.get(base[m], {}).get("resolution_status", "UNKNOWN"), 0), -w.ents[m].validated_degree, -w.ents[m].degree, m))

    def verify_org_pair(self, a: str, b: str, info: dict, base: dict, kinds: set) -> Verdict:
        w = self.load()
        ea, eb = w.ents[a], w.ents[b]
        ia, ib = info.get(base[a]), info.get(base[b])
        meta = {"candidate_kinds": sorted(kinds), "status": [ea.status, eb.status]}
        conf = []
        if is_agency_name(ea.name) or is_agency_name(eb.name) or ea.etype in ("GOVERNMENT_AGENCY", "REGULATOR") or eb.etype in ("GOVERNMENT_AGENCY", "REGULATOR"):
            return Verdict("AMBIGUOUS", "GOVERNMENT_AGENCY_NOT_AUTO_MERGED", meta=meta, conflicts=["agency names usually carry their parent body in parentheses; kept for manual review"])
        va = ia and ia["resolution_status"] in ("VERIFIED", "EXTERNAL_VERIFIED")
        vb = ib and ib["resolution_status"] in ("VERIFIED", "EXTERNAL_VERIFIED")
        ta, tb = (ia or {}).get("ticker"), (ib or {}).get("ticker")
        if va and vb:
            return Verdict("DISTINCT", "TWO_VERIFIED_IDENTITIES", meta={**meta, "tickers": [ta, tb]}, conflicts=[f"both VERIFIED registry identities (tickers {ta}/{tb}): kept as two legal entities by project rule"])
        if {ea.etype, eb.etype} - {"ORGANIZATION", "BANK"} and ea.etype != eb.etype:
            return Verdict("DISTINCT", "TYPE_INCOMPATIBLE", meta=meta, conflicts=[f"{ea.etype} vs {eb.etype}"])
        rel = self.related_between(a, b)
        if rel:
            return Verdict("DISTINCT", "RELATED_ENTITIES_PARENT_CHILD_OR_PARTNER", meta={**meta, "relations": rel}, conflicts=[f"graph has {rel} between them: parent/child or counterparties are never merged"])
        if legal_conflict(ea.name, eb.name) or (ia and ib and legal_conflict(ia["canonical_name"], ib["canonical_name"])):
            return Verdict("DISTINCT", "LEGAL_FORM_CONFLICT", meta=meta, conflicts=["different legal forms (CP vs TNHH)"])
        # evidence retrieval: definition patterns "<long name> (<short>)" / "<short> (<long name>)" and ticker context
        ev, arts = [], set()
        pairs_forms = []
        for s_e, s_i, l_i in ((ea, ia, ib), (eb, ib, ia)):
            if not l_i:
                continue
            lcore = l_i["name_key"]
            # only the entity's OWN names and identity-provider aliases (canonical name, ticker); article-derived parenthetical aliases are untrusted and never serve as proof
            s_forms = {fold_name(s_e.name)} | ({fold_name(s_i["canonical_name"]), s_i["name_key"]} | {a2[0] for a2 in s_i["aliases"] if a2[2] == "identity_provider"} if s_i else set())
            for sf in sorted(s_forms):
                if sf and sf != lcore and not is_generic_org(sf) and not is_generic_org(lcore) and len(lcore.split()) >= 1 and len(lcore) >= 4:
                    pairs_forms.append((sf, lcore, s_i, l_i, s_e))
        p1_forms = []
        seen_forms = set()
        for sf, lcore, s_i2, l_i2, s_e2 in pairs_forms:
            if (sf, lcore) in seen_forms:
                continue
            seen_forms.add((sf, lcore))
            for rowid, aid, ftext in self.fts_articles(sf, lcore, limit=80):
                m = None
                for rx, left_is_long in ((r"(?<!\w)" + mk_tokens(lcore) + r"\s*\(\s*(?:[^()]{0,30}?:\s*)?" + mk_tokens(sf) + r"\s*\)", True),
                                         (r"(?<!\w)" + mk_tokens(sf) + r"\s*\(\s*(?:[^()]{0,30}?:\s*)?" + mk_tokens(lcore) + r"[^()]{0,6}\)", False)):
                    for cm in re.finditer(rx, ftext):
                        ok, chain = left_chain(ftext, cm.start())
                        canon_left = (l_i2["canonical_name"] if (left_is_long and l_i2) else (s_i2["canonical_name"] if s_i2 else s_e2.name))
                        if ok and not class_conflict(chain, canon_left):
                            m = cm
                            break
                    if m:
                        break
                if m and aid not in arts:
                    arts.add(aid)
                    p1_forms.append((sf, lcore))
                    if len(ev) < 3:
                        ev.append({"type": "definition_pattern", "article_id": aid, "short": sf, "long": lcore, "snippet": self.original_text(aid)[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")})
        tick_hits = 0
        for t_e, other, t_i in ((ea, eb, ib), (eb, ea, ia)):
            if t_i and t_i.get("ticker") and fold_name(other.name) == t_i["ticker"].lower() and len(t_i["ticker"]) >= 3:
                tk = t_i["ticker"].lower()
                for rowid, aid, ftext in self.fts_articles(tk, limit=300):
                    if aid in arts:
                        continue
                    if re.search(KEYWORDS + r"\s*:?\s*(?:\(\s*)?" + re.escape(tk) + r"(?!\w)", ftext):
                        tick_hits += 1
                        if tick_hits <= 2 and len(ev) < 4:
                            ev.append({"type": "ticker_context", "ticker": t_i["ticker"], "article_id": aid})
        meta.update({"articles": len(arts), "ticker_context_articles": tick_hits, "tickers": [ta, tb]})
        if (len(arts) >= 2 and (va or vb or len(arts) >= 3)) or (len(arts) >= 1 and tick_hits >= 3 and (va or vb)):
            if is_generic_org(ea.name) or is_generic_org(eb.name):
                return Verdict("AMBIGUOUS", "GENERIC_NAME", ev, meta, ["generic name"])
            return Verdict("VERIFIED_MERGE", "DEFINITION_PATTERN_EVIDENCE" if len(arts) >= 1 else "TICKER_CONTEXT_EVIDENCE", ev, meta, conf)
        if "same_name_key" in kinds and not (va or vb) and ea.status == eb.status == "PROVISIONAL":
            return Verdict("AMBIGUOUS", "NAME_ONLY_PROVISIONAL", ev, meta, ["identical normalised name but PROVISIONAL identities across articles are never merged without evidence"])
        if len(arts) == 1 or tick_hits >= 1:
            return Verdict("AMBIGUOUS", "WEAK_EVIDENCE", ev, meta, conf)
        return Verdict("AMBIGUOUS", "NO_EVIDENCE_FOUND", ev, meta, conf)

    # ------------------------------------------------------------------ stage: persons
    def canon_org(self, k: str) -> str:
        return self.org_uf.find(k) if k in self.org_uf.p or k in self.org_uf.p.values() else k

    def stage_person(self) -> dict:
        w = self.load()
        persons = {k: e for k, e in w.ents.items() if e.etype == "PERSON"}
        groups: dict[str, list[str]] = defaultdict(list)
        for k, e in persons.items():
            nk = person_key(e.name)
            if person_name_ok(e.name, nk):
                groups[nk].append(k)
        multi = {nk: sorted(v) for nk, v in groups.items() if len(v) > 1}
        want = sorted({k for v in multi.values() for k in v})
        s = sqlite3.connect(f"file:{self.staging.as_posix()}?mode=ro", uri=True, timeout=60)
        facts: dict[str, dict] = {}
        for n, k in enumerate(want):
            if n % 200 == 0:
                self.check()
                self.upd(stage="person", persons_facts=n, persons_total=len(want))
            aid = k.split("@art:")[-1]
            row = s.execute("SELECT text, published_at, url FROM articles WHERE article_id=?", (aid,)).fetchone()
            pub = best_date(row[1], row[2]) if row else None
            f = person_context(row[0], persons[k].name, pub) if row else {"found": False, "gender": None, "relative": False, "birth": None, "snippet": ""}
            f.update(article_id=aid, pub=pub.isoformat() if pub else None)
            facts[k] = f
        s.close()
        with self.db:
            self.db.execute("DELETE FROM person_facts")
            for k, f in facts.items():
                self.db.execute("INSERT INTO person_facts VALUES(?,?,?,?,?,?,?,?)", (k, f["article_id"], f["pub"], int(f["found"]), f["gender"], f["birth"], int(f["relative"]), f["snippet"]))
        # org links (canonical orgs after org resolution)
        links: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"s": 0, "preds": set(), "status": set()}))
        for k in want:
            for i in w.adj[k]:
                e = w.edges[i]
                if e["s_key"] != k or e["o_key"] not in w.ents or w.ents[e["o_key"]].etype not in ORG_TYPES:
                    continue
                L = links[k][self.canon_org(e["o_key"])]
                L["s"] = max(L["s"], 2 if e["tier"] in VALIDATED else 1)
                L["preds"].add(e["predicate"])
                L["status"].add(e["factual_status"])
        prior = prior_map(w.prior_person_merges)
        decisions: dict[tuple, Verdict] = {}
        n = 0
        for nk, ks in multi.items():
            for a, b in combinations(ks, 2):
                n += 1
                if n % 200 == 0:
                    self.check()
                    self.upd(stage="person", person_pairs_done=n)
                v = self.verify_person_pair(a, b, facts, links, nk, (prior.get(a, a) == prior.get(b, b)))
                decisions[(a, b)] = v
        with self.db:
            self.db.execute("DELETE FROM person_pairs")
            for (a, b), v in decisions.items():
                self.db.execute("INSERT INTO person_pairs VALUES(?,?,?,?,?,?,?,?)", (a, b, v.decision, v.reason, json_dumps(v.evidence[:3]), json_dumps(v.meta), json_dumps(v.conflicts), int(v.meta.get("llm_candidate", False))))
        c = Counter(v.decision for v in decisions.values())
        return {"person_entities": len(persons), "eligible_name_groups": len(groups), "groups_with_duplicates": len(multi), "entities_in_duplicate_groups": len(want), "pairs": n,
                "decisions": dict(c), "reasons": {f"{d}/{r}": n for (d, r), n in Counter((v.decision, v.reason) for v in decisions.values()).most_common(20)}, "llm_candidates": sum(1 for v in decisions.values() if v.meta.get("llm_candidate"))}

    def verify_person_pair(self, a: str, b: str, facts: dict, links: dict, nk: str, was_prior: bool) -> Verdict:
        fa, fb = facts[a], facts[b]
        la, lb = links.get(a, {}), links.get(b, {})
        shared = sorted(set(la) & set(lb))
        meta = {"name_key": nk, "tokens": len(nk.split()), "prior_merge": was_prior, "shared_orgs": shared[:5], "birth": [fa["birth"], fb["birth"]], "gender": [fa["gender"], fb["gender"]],
                "dates": [fa["pub"], fb["pub"]]}
        if fa["gender"] and fb["gender"] and fa["gender"] != fb["gender"]:
            return Verdict("DISTINCT", "GENDER_CONFLICT", meta=meta, conflicts=[f"{fa['gender']} vs {fb['gender']} (ong/ba before the name)"])
        if birth_conflict(fa["birth"], fb["birth"]):
            return Verdict("DISTINCT", "BIRTH_YEAR_CONFLICT", meta=meta, conflicts=[f"birth {fa['birth']} vs {fb['birth']}"])
        if not fa["found"] or not fb["found"]:
            return Verdict("AMBIGUOUS", "MENTION_NOT_LOCATED", meta=meta, conflicts=["name span not re-found in article text"])
        if fa["relative"] or fb["relative"]:
            return Verdict("AMBIGUOUS", "RELATIVE_CONTEXT", meta=meta, conflicts=["mention is introduced as a relative of someone"])
        if not shared:
            return Verdict("AMBIGUOUS", "NAME_ONLY_NO_SHARED_ORG", meta=meta)
        # evidence of the roles
        roles_a = {p for o in shared for p in la[o]["preds"]}
        roles_b = {p for o in shared for p in lb[o]["preds"]}
        strong = any(la[o]["s"] == 2 or lb[o]["s"] == 2 for o in shared) and all(min(la[o]["s"], lb[o]["s"]) >= 1 for o in shared)
        same_role = bool(roles_a & roles_b)
        fam_ok = bool({role_family(r) for r in roles_a} & {role_family(r) for r in roles_b})
        da, db_ = article_date(fa["pub"]), article_date(fb["pub"])
        gap = abs((da - db_).days) if da and db_ else None
        hist = any(s in ("HISTORICAL", "ENDED") for o in shared for s in la[o]["status"] | lb[o]["status"])
        meta.update({"roles": [sorted(roles_a), sorted(roles_b)], "date_gap_days": gap, "strong_link": strong, "same_role": same_role, "historical_cue": hist})
        corro = (fa["birth"] is not None and fa["birth"] == fb["birth"]) or len(shared) >= 2
        ev = [{"type": "person_mention", "article_id": fa["article_id"], "snippet": fa["snippet"]}, {"type": "person_mention", "article_id": fb["article_id"], "snippet": fb["snippet"]}]
        if gap is not None and (gap > 12 * 365 or (gap > 5 * 365 and not (same_role and meta["tokens"] >= 3) and not hist)):
            meta["llm_candidate"] = False  # temporal compatibility is a deterministic constraint the model cannot waive
            return Verdict("AMBIGUOUS", "TIME_GAP", ev, meta, ["articles more than 5 years apart without the same role at the shared organisation (or more than 12 years apart)"])
        if not strong:
            meta["llm_candidate"] = False
            return Verdict("AMBIGUOUS", "ORG_LINK_WEAK", ev, meta, ["shared organisation supported only by QUARANTINE links"])
        if not (same_role or fam_ok):
            meta["llm_candidate"] = True
            return Verdict("AMBIGUOUS", "ROLE_MISMATCH", ev, meta, ["roles at the shared organisation differ"])
        if meta["tokens"] < 3 and not corro:
            meta["llm_candidate"] = True
            return Verdict("AMBIGUOUS", "SHORT_NAME_NO_CORROBORATION", ev, meta, ["two-token name needs a matching birth year or a second shared organisation"])
        return Verdict("VERIFIED_MERGE", "NAME_ORG_ROLE_TIME_CONSISTENT", ev, meta, [])

    # ------------------------------------------------------------------ stage: qwen (optional; the deterministic verifier decides)
    def stage_qwen(self) -> dict:
        if not self.use_qwen or self.qwen_budget <= 0:
            return {"skipped": True, "reason": "disabled or zero budget"}
        try:
            ok = any(m["name"] == "qwen3.5:9b" for m in httpx.get("http://127.0.0.1:11434/api/tags", timeout=5).json().get("models", []))
        except (httpx.HTTPError, ValueError):
            ok = False
        if not ok:
            return {"skipped": True, "reason": "Ollama/qwen3.5:9b not reachable (no budget consumed)"}
        rows = self.db.execute("SELECT * FROM person_pairs WHERE llm=1 AND decision='AMBIGUOUS' ORDER BY a, b").fetchall()
        w = self.load()
        fails = 0
        facts = {r["key"]: dict(r) for r in self.db.execute("SELECT * FROM person_facts")}
        rows = sorted(rows, key=lambda r: -(w.ents[r["a"]].degree + w.ents[r["b"]].degree))
        used = int(self.meta("qwen_live_calls", 0) or 0)
        live = acc = dis = uns = rejected = 0
        t0 = time.time()
        for n, r in enumerate(rows):
            self.check()
            if used + live >= self.qwen_budget:
                break
            fa, fb = facts[r["a"]], facts[r["b"]]
            meta = json.loads(r["meta"])
            res = self.ask_qwen(w.ents[r["a"]].name, meta, fa, fb)
            if res is None:
                fails += 1
                if fails >= 3:
                    break  # service trouble: stop instead of burning the budget
                continue
            ans, was_live = res
            live += was_live
            v = self.check_llm(ans, fa, fb, meta)
            with self.db:
                self.db.execute("INSERT INTO llm_log VALUES(?,?,?,?,?,?,?)", (r["a"], r["b"], ans.get("verdict"), v[0], v[1], was_live, 0.0))
                if v[0] == "SAME_ACCEPTED":
                    ev = json.loads(r["evidence"]) + [{"type": "qwen_quotes", "quote_a": ans.get("quote_a"), "quote_b": ans.get("quote_b"), "note": "advisory; deterministic verifier re-checked"}]
                    self.db.execute("UPDATE person_pairs SET decision='VERIFIED_MERGE', reason='LLM_ADVISORY_PLUS_DETERMINISTIC_CHECKS', evidence=? WHERE a=? AND b=?", (json_dumps(ev), r["a"], r["b"]))
                    acc += 1
                elif v[0] == "DIFFERENT_ACCEPTED":
                    self.db.execute("UPDATE person_pairs SET decision='DISTINCT', reason='LLM_CITED_VERIFIED_CONFLICT' WHERE a=? AND b=?", (r["a"], r["b"]))
                    dis += 1
                elif v[0] == "REJECTED":
                    rejected += 1
                else:
                    uns += 1
            self.set_meta("qwen_live_calls", used + live)
            self.upd(stage="qwen", qwen_live_calls=used + live, qwen_pairs_done=n + 1, qwen_pairs_total=len(rows))
        return {"pairs_considered": len(rows), "live_calls_this_run": live, "live_calls_total": used + live, "budget": self.qwen_budget, "same_accepted": acc, "different_accepted": dis,
                "unsure": uns, "answers_rejected_by_verifier": rejected, "seconds": round(time.time() - t0, 1)}

    def ask_qwen(self, name: str, meta: dict, fa: dict, fb: dict):
        prompt = (f"Name: {name}\nShared organisation(s): {', '.join(meta.get('shared_orgs', []))}\nRoles: {meta.get('roles')}\n\nMention A (article date {fa['pub']}):\n{fa['snippet']}\n\n"
                  f"Mention B (article date {fb['pub']}):\n{fb['snippet']}\n\nDo A and B refer to the SAME real person? Use only the two texts. Answer JSON: verdict SAME|DIFFERENT|UNSURE; "
                  "quote_a and quote_b = exact substrings copied from A and from B that support your verdict; reason = one short sentence.")
        key = hashlib.sha256(("v2|" + prompt).encode()).hexdigest()
        hit = self.db.execute("SELECT response FROM llm_cache WHERE key=?", (key,)).fetchone()
        if hit:
            return json.loads(hit[0]), 0
        schema = {"type": "object", "required": ["verdict", "quote_a", "quote_b", "reason"], "properties": {"verdict": {"type": "string", "enum": ["SAME", "DIFFERENT", "UNSURE"]},
                  "quote_a": {"type": "string"}, "quote_b": {"type": "string"}, "reason": {"type": "string", "maxLength": 200}}}
        payload = {"model": "qwen3.5:9b", "stream": False, "think": False, "format": schema, "keep_alive": "10m", "options": {"temperature": 0, "seed": 7, "num_ctx": 4096},
                   "messages": [{"role": "system", "content": "You compare two mentions of a person name in Vietnamese financial news and decide only from the given texts whether they are the same individual. Never assume; answer UNSURE when the texts do not settle it."},
                                {"role": "user", "content": prompt}]}
        t = time.time()
        try:
            r = httpx.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=180)
            r.raise_for_status()
            ans = json.loads(r.json()["message"]["content"])
        except (httpx.HTTPError, ValueError, KeyError):
            self.set_meta("qwen_live_calls", int(self.meta("qwen_live_calls", 0) or 0) + 1)  # a failed live attempt still counts
            return None
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO llm_cache VALUES(?,?,?,datetime('now'))", (key, json.dumps(ans, ensure_ascii=False), time.time() - t))
        return ans, 1

    @staticmethod
    def check_llm(ans: dict, fa: dict, fb: dict, meta: dict) -> tuple[str, str]:
        """Deterministic verification of an LLM answer: quotes must be verbatim substrings of the respective snippets, and SAME is only accepted when the hard constraints already hold
        (no birth/gender conflict, a strong shared-organisation link, no relative context). The LLM never creates a merge on its own."""
        qa, qb = (ans.get("quote_a") or "").strip(), (ans.get("quote_b") or "").strip()
        if len(qa) < 12 or len(qb) < 12 or qa not in fa["snippet"] or qb not in fb["snippet"]:
            return "REJECTED", "quotes are not verbatim substrings of the provided snippets"
        last = (meta.get("name_key") or "").split()[-1:] or [""]
        if last[0] and not (last[0] in fold_name(qa) and last[0] in fold_name(qb)):
            return "REJECTED", "quotes do not contain the person's name in both texts"
        if ans.get("verdict") == "SAME":
            if meta.get("strong_link") and not birth_conflict(fa["birth"], fb["birth"]) and not fa["relative"] and not fb["relative"] and meta.get("tokens", 0) >= 2:
                return "SAME_ACCEPTED", "quotes verified, constraints hold"
            return "REJECTED", "SAME but deterministic constraints do not hold"
        if ans.get("verdict") == "DIFFERENT":
            blob = (qa + " " + qb).lower()
            if re.search(r"sinh\s*(?:năm)?\s*(19|20)\d{2}|\d{2}\s*tuổi|con trai|con gái|vợ|chồng|anh trai|em trai", blob):
                return "DIFFERENT_ACCEPTED", "quotes contain an age/birth/relative cue"
            return "REJECTED", "DIFFERENT without a verifiable discriminating cue"
        return "UNSURE", "model unsure"

    # ------------------------------------------------------------------ stage: unresolved text
    def stage_ut(self) -> dict:
        w = self.load()
        uts = sorted(k for k, e in w.ents.items() if e.etype is None and k.startswith("text:"))
        cand_ids: set[str] = set()
        rows_by_key: dict[str, list] = {}
        for i, k in enumerate(uts):
            _, art, _name = k.split(":", 2)
            ms = [m for m in self.reg.execute("SELECT surface_text, detected_type, entity_id, linking_method, resolution_status, candidate_entity_ids FROM mentions WHERE article_id=?", (art,))
                  if fold_name(m["surface_text"]) == fold_name(w.ents[k].name)]
            rows_by_key[k] = ms
            for m in ms:
                try:
                    cand_ids |= set(json.loads(m["candidate_entity_ids"] or "[]"))
                except ValueError:
                    pass
        info = self.reg_info(sorted(cand_ids))
        res: dict[str, Verdict] = {}
        for i, k in enumerate(uts):
            if i % 100 == 0:
                self.check()
                self.upd(stage="ut", ut_done=i, ut_total=len(uts))
            res[k] = self.verify_ut(k, rows_by_key[k], info)
        with self.db:
            self.db.execute("DELETE FROM ut_links")
            for k, v in res.items():
                self.db.execute("INSERT INTO ut_links VALUES(?,?,?,?,?,?)", (k, v.decision, v.reason, v.meta.get("target"), json_dumps(v.evidence[:3]), json_dumps({**v.meta, "conflicts": v.conflicts})))
        c = Counter(v.decision for v in res.values())
        return {"unresolved_text_nodes": len(uts), "decisions": dict(c), "reasons": {f"{d}/{r}": n for (d, r), n in Counter((v.decision, v.reason) for v in res.values()).most_common(25)}}

    def verify_ut(self, k: str, ms: list, info: dict) -> Verdict:
        w = self.load()
        _, art, _n = k.split(":", 2)
        name = w.ents[k].name
        fname = fold_name(name)
        if not ms:
            return Verdict("UNRESOLVED", "NO_MENTION_ROW", meta={})
        methods = Counter(m["linking_method"] for m in ms)
        if any(str(m["linking_method"]).startswith(("out_of_scope", "person_", "bad_span")) for m in ms) or is_generic_org(name):
            return Verdict("UNRESOLVED", "OUT_OF_SCOPE_OR_GENERIC", meta={"methods": dict(methods)})
        types = Counter(m["detected_type"] for m in ms)
        cands: set[str] = set()
        for m in ms:
            try:
                cands |= set(json.loads(m["candidate_entity_ids"] or "[]"))
            except ValueError:
                pass
        fam = lambda t: "ORG" if t in ("ORGANIZATION", "BANK") else t
        dt = {fam(t) for t in types}
        cands = {c for c in cands if info.get(c) and info[c]["entity_type"] in ORG_TYPES and not info[c]["merged_into"] and fam(info[c]["entity_type"]) in dt
                 and not fold_name(info[c]["canonical_name"]).startswith(("hdqt", "hoi dong"))}
        if not cands:
            return Verdict("UNRESOLVED", "NO_CANDIDATE", meta={"methods": dict(methods), "types": dict(types)})
        text_f = None

        def canon(cid: str) -> str:
            return self.canon_org(cid) if cid in w.ents else cid
        clusters: dict[str, list[str]] = defaultdict(list)
        for c in cands:
            clusters[canon(c)].append(c)
        resident = {m["entity_id"] for m in self.reg.execute("SELECT entity_id FROM mentions WHERE article_id=? AND entity_id IS NOT NULL", (art,))}
        resident_cl = {canon(x) for x in resident if x in info or x in w.ents}
        meta = {"methods": dict(methods), "types": dict(types), "candidates": sorted(cands), "clusters": len(clusters)}
        in_art = [r for r in clusters if r in resident_cl]
        pick, why = None, ""
        ticker_ctx = False
        if "ticker_without_context" in methods:
            text_f = fold1(self.original_text(art))
            ticker_ctx = bool(re.search(KEYWORDS + r"\s*:?\s*(?:\(\s*)?" + re.escape(fname) + r"(?!\w)", text_f))
            meta["ticker_context_in_article"] = ticker_ctx
        nname = person_key_org(name)
        exact_cl = {r for r, mem in clusters.items() if any(person_key_org(w.ents[c].name) == nname for c in mem if c in w.ents)
                    or any(info[c]["name_key"] == nname or fold_name(info[c]["canonical_name"]) == fname for c in mem if c in info)}
        holders = {r for r, mem in clusters.items() if any((info.get(c) or {}).get("ticker") and info[c]["ticker"].lower() == fname for c in mem)}
        meta["exact_clusters"], meta["ticker_holder_clusters"] = len(exact_cl), len(holders)
        tickerlike = name.isupper() and len(name) <= 5
        if "ticker_without_context" in methods and not ticker_ctx and (holders or tickerlike) and not (exact_cl and len(clusters) == 1 and in_art):
            return Verdict("AMBIGUOUS", "TICKER_WITHOUT_CONTEXT", meta=meta, conflicts=["bare ticker/acronym without a context keyword in the article"])
        if len(exact_cl) == 1:
            pick, why = next(iter(exact_cl)), ("ALIAS_COLLISION_RESOLVED_BY_ORG_CLUSTER" if len(clusters) == 1 and len(next(iter(clusters.values()))) > 1 else "EXACT_NAME_UNIQUE_CLUSTER")
        elif len(exact_cl) > 1:
            both = [r for r in exact_cl if r in in_art]
            if len(both) == 1:
                pick, why = both[0], "EXACT_NAME_AND_ARTICLE_COREFERENCE"
            else:
                return Verdict("AMBIGUOUS", "MULTIPLE_EXACT_NAME_IDENTITIES", meta=meta, conflicts=[f"{len(exact_cl)} distinct canonical entities carry this exact name"])
        elif len(holders) == 1 and ticker_ctx:
            pick, why = next(iter(holders)), "TICKER_WITH_CONTEXT"
        elif len(in_art) == 1 and not tickerlike:
            pick, why = in_art[0], "ARTICLE_COREFERENCE" if len(clusters) == 1 else "ARTICLE_COREFERENCE_AMONG_COMPETING_CANDIDATES"
        elif len(clusters) == 1 and in_art:
            pick, why = in_art[0], "ARTICLE_COREFERENCE"
        else:
            return Verdict("AMBIGUOUS", "MULTIPLE_CANDIDATE_IDENTITIES" if len(clusters) > 1 else "SINGLE_CANDIDATE_WITHOUT_SUPPORT", meta=meta,
                           conflicts=[f"{len(clusters)} distinct canonical candidates, {len(in_art)} present in the article, {len(exact_cl)} exact-name"])
        meta["target"] = pick
        ev = [{"type": "registry_mention", "article_id": art, "surface": name, "linking_method": dict(methods), "candidate_ids": sorted(cands)[:6]}]
        return Verdict("VERIFIED_MERGE", why, ev, meta)

    # ------------------------------------------------------------------ stage: build mapping + graph V2
    def stage_build(self) -> dict:
        from vckg.entity_resolution.export import build_v2
        return build_v2(self)

    def load_decisions(self):
        self.person_uf = UF()
        w = self.load()
        facts = {r["key"]: dict(r) for r in self.db.execute("SELECT * FROM person_facts")}
        rows = self.db.execute("SELECT * FROM person_pairs ORDER BY a,b").fetchall()
        distinct = {(r["a"], r["b"]) for r in rows if r["decision"] == "DISTINCT"} | {(r["b"], r["a"]) for r in rows if r["decision"] == "DISTINCT"}
        order = sorted((r for r in rows if r["decision"] == "VERIFIED_MERGE"), key=lambda r: (r["a"], r["b"]))
        rejected = 0
        for r in order:
            a, b = r["a"], r["b"]
            ra, rb = self.person_uf.find(a), self.person_uf.find(b)
            if ra == rb:
                continue
            mem = self.person_uf.members()
            ma, mb = mem.get(ra, [a]), mem.get(rb, [b])
            attrs = [facts.get(m) for m in ma + mb]
            births = {f["birth"] for f in attrs if f and f["birth"] is not None}
            genders = {f["gender"] for f in attrs if f and f["gender"]}
            if any((x, y) in distinct for x in ma for y in mb) or len(genders) > 1 or (len(births) > 1 and max(births) - min(births) > 1):
                rejected += 1
                continue
            rep = min(ma + mb, key=lambda m: (-w.ents[m].validated_degree, -w.ents[m].degree, m))
            self.person_uf.union(a, b, rep)
        return rejected


# ------------------------------------------------------------------------------------------------ driver
def run(snapshot: Path, out: Path = OUT, qwen_budget: int = 1000, use_qwen: bool = True, force_from: str | None = None, **kw) -> dict:
    R = Run(snapshot, out, qwen_budget, use_qwen, **kw)
    if R.status:
        R.status.update(state="RUNNING", mode="entity-resolution-v2", snapshot=str(snapshot), qwen_budget=qwen_budget, version=VERSION)
        R.status.start_heartbeat()
    results = {}
    code = 0
    try:
        if force_from:
            for s in STAGES[STAGES.index(force_from):]:
                with R.db:
                    R.db.execute("DELETE FROM stages WHERE name=?", (s,))
        R.set_meta("watermark", R.watermark())
        R.set_meta("version", VERSION)
        for s in STAGES:
            if R.stage_done(s):
                results[s] = {"skipped": "already DONE (resume)"}
                continue
            R.check()
            R.mark_stage(s, "RUNNING")
            t = time.time()
            if s == "org":
                R.org_uf = UF()
            elif s in ("person", "ut", "build", "qwen") and R.stage_done("org") and not R.org_uf.p:
                R.rebuild_org_uf()
            try:
                st = getattr(R, f"stage_{s}")()
            except Stop:
                R.mark_stage(s, "STOPPED")
                raise
            st["seconds"] = round(time.time() - t, 1)
            R.mark_stage(s, "DONE", st)
            results[s] = st
            R.upd(stage_done=s)
        R.upd(state="COMPLETED", finished_at=now())
    except Stop:
        if R.status:
            R.status.update(state="STOPPED", finished_at=now())
        code = 3
        results["stopped"] = True
    except Exception as e:
        if R.status:
            R.status.update(state="FAILED", finished_at=now(), last_error=f"{type(e).__name__}: {e}"[:400])
        results["error"] = repr(e)
        code = 1
        raise
    finally:
        if R.status:
            R.status.stop_heartbeat()
    results["exit"] = code
    return results


def _rebuild_org_uf(self) -> None:
    keys, base, info = self.org_universe()
    del keys
    uf = UF()
    for r in self.db.execute("SELECT a,b FROM org_pairs WHERE decision='VERIFIED_MERGE' ORDER BY a,b"):
        a, b = r["a"], r["b"]
        ra, rb = uf.find(a), uf.find(b)
        if ra != rb:
            mem = uf.members()
            uf.union(a, b, self.pick_rep(mem.get(ra, [a]) + mem.get(rb, [b]), info, base))
    self.org_uf = uf


Run.rebuild_org_uf = _rebuild_org_uf


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="er_v2")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--snapshot", default=str(ROOT / "data/graph_preview/20261102-143350"))
    r.add_argument("--out", default=str(OUT))
    r.add_argument("--qwen-budget", type=int, default=1000)
    r.add_argument("--no-qwen", action="store_true")
    r.add_argument("--force-stage", choices=STAGES)
    s = sub.add_parser("status")
    s.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    if a.cmd == "status":
        p = Path(a.out) / "status.json"
        print(p.read_text(encoding="utf-8") if p.exists() else "no status")
        return 0
    if a.qwen_budget > 1000:
        print("qwen budget capped at 1000 for this run", file=sys.stderr)
    res = run(Path(a.snapshot), Path(a.out), min(a.qwen_budget, 1000), not a.no_qwen, a.force_stage)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str)[:6000])
    return res.get("exit", 0)


if __name__ == "__main__":
    sys.exit(main())

