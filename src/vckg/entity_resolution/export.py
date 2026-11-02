"""ER v2 - canonical mapping, Graph V2 rebuild (from src_edges/src_evidence, never from the aggregate edges), verification invariants, exports and the review sample."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from vckg.entity_resolution.core import ORG_TYPES, TIERS, VALIDATED, VERSION, has_cycle, json_dumps, prior_map
from vckg.graph import preview as pv

SEED = 20261102


def eid_of(tier: str, s: str, p: str, o: str, st: str, vf: str, vt: str) -> str:
    return hashlib.sha1("|".join([s, p, o, st, vf or "", vt or ""]).encode()).hexdigest()[:16]


def apply_mapping(w, mapping: dict[str, str]):
    """-> (edges: {(tier,s,p,o,status,vf,vt): {...}}, evidence: {(edge_key): {(article,start,end): row}}, self_loops: [(edge_key, origS, origO)])"""
    edges: dict[tuple, dict] = {}
    ev: dict[tuple, dict] = defaultdict(dict)
    loops = []
    for e in w.edges:
        s, o = mapping.get(e["s_key"], e["s_key"]), mapping.get(e["o_key"], e["o_key"])
        k = (e["tier"], s, e["predicate"], o, e["factual_status"], e["valid_from"] or "", e["valid_to"] or "")
        d = edges.setdefault(k, {"qc": set(), "dm": set(), "src": set(), "orig": set()})
        d["src"].add(e["source_id"])
        d["orig"].add((e["s_key"], e["o_key"]))
        if e["quarantine_class"]:
            d["qc"].add(e["quarantine_class"])
        if e["discovery_method"]:
            d["dm"].add(e["discovery_method"])
        for r in w.evidence.get((e["source_id"], e["edge_id"], e["tier"]), ()):
            ev[k].setdefault((r["article_id"], r["evidence_start"], r["evidence_end"]), r)
        if s == o:
            loops.append((k, e["s_key"], e["o_key"]))
    return edges, ev, loops


def build_v2(R) -> dict:
    w = R.load()
    out = R.out
    if not R.org_uf.p and R.stage_done("org"):
        R.rebuild_org_uf()
    rejected_person = R.load_decisions()
    members_org = R.org_uf.members()
    members_per = R.person_uf.members()
    ut_rows = {r["key"]: dict(r) for r in R.db.execute("SELECT * FROM ut_links")}
    org_pairs = R.db.execute("SELECT * FROM org_pairs").fetchall()
    per_pairs = R.db.execute("SELECT * FROM person_pairs").fetchall()
    # ---- mapping
    mapping: dict[str, str] = {}
    for rep, mem in members_org.items():
        for m in mem:
            mapping[m] = rep
    for rep, mem in members_per.items():
        for m in mem:
            mapping[m] = rep
    # reasons for members: strongest verified pair linking the member
    pair_reason: dict[str, tuple] = {}
    for r in list(org_pairs) + list(per_pairs):
        if r["decision"] == "VERIFIED_MERGE":
            for x in (r["a"], r["b"]):
                pair_reason.setdefault(x, (r["reason"], r["evidence"], r["meta"]))
    ut_targets = {}
    for k, r in ut_rows.items():
        if r["decision"] == "VERIFIED_MERGE" and r["target"]:
            ut_targets[k] = mapping.get(r["target"], r["target"])
    reverted_ut = {}
    while True:
        m2 = dict(mapping)
        m2.update(ut_targets)
        _e, _v, loops = apply_mapping(w, m2)
        bad = [(k, a, b) for k, a, b in loops if a != b and (a in ut_targets or b in ut_targets)]
        if not bad:
            break
        for _k, a, b in bad:
            for x in (a, b):
                if x in ut_targets:
                    reverted_ut[x] = ut_targets.pop(x)
    mapping.update(ut_targets)
    assert not has_cycle(mapping)
    chain_ok = all(mapping.get(v, v) == v for v in set(mapping.values()))
    edges, ev, loops = apply_mapping(w, mapping)
    new_loops = [(k, a, b) for k, a, b in loops if a != b]
    # ---- control replay: aggregator's existing merges only (must reproduce the snapshot numbers)
    prior = prior_map(w.prior_person_merges)
    c_edges, c_ev, _l = apply_mapping(w, prior)
    c_nodes = {x for k in c_edges for x in (k[1], k[3])}
    # ---- entity table
    reg_missing = sorted({v for v in mapping.values() if v not in w.ents} | {v for v in ut_targets.values() if v not in w.ents})
    info = R.reg_info(sorted({m.split("@")[0] for m in reg_missing}))
    canon_nodes = {x for k in edges for x in (k[1], k[3])}
    groups: dict[str, list[str]] = defaultdict(list)
    for k in {x for e in w.edges for x in (e["s_key"], e["o_key"])}:
        groups[mapping.get(k, k)].append(k)
    ents_v2: dict[str, dict] = {}
    for cid in canon_nodes:
        mem = sorted(set(groups.get(cid, [])) | {cid})
        rep = w.ents.get(cid)
        regi = info.get(cid.split("@")[0]) if rep is None else None
        names = Counter()
        for m in mem:
            if m in w.ents:
                for n, c in w.ents[m].names.items():
                    names[n] += c
        disp = [n for n, _ in names.most_common() if n != n.lower() or any(ord(ch) > 127 for ch in n)]
        etype = rep.etype if rep else (regi["entity_type"] if regi else None)
        status = rep.status if rep else (regi["resolution_status"] if regi else "UNKNOWN")
        if etype is None and cid.startswith("text:"):
            etype = None
        ents_v2[cid] = {"entity_key": cid, "entity_id": cid.split("@")[0], "name": (disp[0] if disp else (rep.name if rep else (regi["canonical_name"] if regi else cid))), "entity_type": etype,
                        "resolution_status": status, "members": mem}
    # ---- mapping table with explanations
    pairs_state: dict[str, list] = defaultdict(list)
    for r in org_pairs:
        for x in (r["a"], r["b"]):
            pairs_state[x].append((r["decision"], r["reason"]))
    for r in per_pairs:
        for x in (r["a"], r["b"]):
            pairs_state[x].append((r["decision"], r["reason"]))
    wm = R.meta("watermark")
    rows = []
    for k in sorted({x for e in w.edges for x in (e["s_key"], e["o_key"])}):
        cid = mapping.get(k, k)
        e = w.ents[k]
        if cid != k:
            kind = "UT" if k in ut_targets else ("PERSON" if e.etype == "PERSON" else "ORG")
            rs = ut_rows[k]["reason"] if k in ut_targets else pair_reason.get(k, ("CLUSTER_MEMBER", "", ""))[0]
            ev_ = ut_rows[k]["evidence"] if k in ut_targets else pair_reason.get(k, ("", "[]", "{}"))[1]
            meta = ut_rows[k]["meta"] if k in ut_targets else pair_reason.get(k, ("", "", "{}"))[2]
            rows.append((k, cid, kind, "VERIFIED_MERGE", rs, "deterministic_verifier", ev_ or "[]", meta or "{}", "[]", VERSION, json_dumps(wm)))
        else:
            if e.etype is None and k in ut_rows:
                r = ut_rows[k]
                dec = "AMBIGUOUS" if (r["decision"] == "AMBIGUOUS" or k in reverted_ut) else "UNRESOLVED"
                rows.append((k, k, "UT", dec, "SELF_LOOP_CONFLICT" if k in reverted_ut else r["reason"], "deterministic_verifier", r["evidence"], r["meta"], "[]", VERSION, json_dumps(wm)))
            else:
                st = pairs_state.get(k, [])
                decs = Counter(d for d, _ in st)
                dec = "AMBIGUOUS" if decs.get("AMBIGUOUS") else "DISTINCT"
                rs = Counter(r for d, r in st if d == dec).most_common(1)[0][0] if st and any(d == dec for d, _ in st) else "NO_COMPETING_CANDIDATE"
                rows.append((k, k, "PERSON" if e.etype == "PERSON" else ("ORG" if e.etype in ORG_TYPES else "OTHER"), dec, rs, "deterministic_verifier", "[]", "{}", "[]", VERSION, json_dumps(wm)))
    with R.db:
        R.db.execute("DELETE FROM entity_map")
        R.db.executemany("INSERT INTO entity_map VALUES(?,?,?,?,?,?,?,?,?,?,?)", rows)
        R.db.execute("DELETE FROM merge_clusters")
        for cid, mem in groups.items():
            if len(mem) > 1:
                kind = "PERSON" if ents_v2.get(cid, {}).get("entity_type") == "PERSON" else ("ORG" if ents_v2.get(cid, {}).get("entity_type") in ORG_TYPES else "UT_LINKED")
                R.db.execute("INSERT INTO merge_clusters VALUES(?,?,?,?,?)", (cid, kind, len(mem), json_dumps(sorted(mem)), ""))
    # ---- V2 graph structures in preview format
    edge_rows, evd = [], {}
    for k, d in sorted(edges.items(), key=lambda t: (t[0][0], t[0][1], t[0][2], t[0][3], t[0][4])):
        tier, s, p, o, st, vf, vt = k
        eid = eid_of(tier, s, p, o, st, vf, vt)
        rws = list(ev[k].values())
        edge_rows.append({"edge_id": eid, "tier": tier, "subject_key": s, "predicate": p, "object_key": o, "factual_status": st, "valid_from": vf, "valid_to": vt,
                          "quarantine_classes": json_dumps(sorted(d["qc"])) if tier == "QUARANTINE" else "[]", "discovery_methods": json_dumps(sorted(d["dm"])),
                          "n_evidence": len(rws), "n_articles": len({r["article_id"] for r in rws}), "sources": json_dumps(sorted(d["src"]))})
        evd[(eid, tier)] = rws
    pub: dict = {}
    gv, ge = pv.build_graph(ents_v2, edge_rows, VALIDATED), pv.build_graph(ents_v2, edge_rows, TIERS)
    comp_v, comp_e = pv.components(gv), pv.components(ge)
    com_v, com_e = pv.communities(gv), pv.communities(ge)
    sv, se = pv.stats_of(gv, comp_v, ents_v2), pv.stats_of(ge, comp_e, ents_v2)
    sv["communities"], se["communities"] = len(com_v), len(com_e)
    # ---- exports
    pv.write_graphml(gv, out / "validated_v2.graphml")
    pv.write_graphml(ge, out / "exploratory_v2.graphml")
    tmp = out / "_csv"
    tmp.mkdir(exist_ok=True)
    nn, ne = pv.export_csv(tmp, ents_v2, edge_rows, evd, pub, gv, ge, comp_v, comp_e, com_v, com_e)
    shutil.move(str(tmp / "edges.csv"), str(out / "edges_v2.csv"))
    write_nodes_csv(out / "nodes_v2.csv", tmp / "nodes.csv", ents_v2, ut_rows, mapping, reverted_ut)
    shutil.rmtree(tmp, ignore_errors=True)
    viewer = export_viewer_v2(R, out, ents_v2, edge_rows, evd, pub, gv, ge, comp_v, comp_e, com_v, com_e, w)
    # ---- verification invariants
    before_evid = {(r["tier"], r["article_id"], r["evidence_start"], r["evidence_end"]) for rs in w.evidence.values() for r in rs}
    after_evid = {(t[0], r["article_id"], r["evidence_start"], r["evidence_end"]) for kk, rr in ev.items() for r in rr.values() for t in [kk]}
    Counter(e["tier"] for e in w.edges)
    tier_orig_after = Counter()
    for k, d in edges.items():
        tier_orig_after[k[0]] += 0
    qa_ok = all(k[0] in TIERS for k in edges)
    # a merged edge never mixes tiers: tier is part of the key
    direction_ok = all(((mapping.get(a, a), mapping.get(b, b)) == (k[1], k[3])) for k, d in edges.items() for a, b in d["orig"])
    prior_nodes_base = json.loads((R.snapshot / "stats.json").read_text(encoding="utf-8"))
    base_e, base_v = prior_nodes_base["exploratory"], prior_nodes_base["validated"]
    prior_pairs = list(w.prior_person_merges)
    prior_same = sum(1 for kept, dropped in prior_pairs if mapping.get(kept, kept) == mapping.get(dropped, dropped))
    prior_reasons = Counter()
    for kept, dropped in prior_pairs:
        if mapping.get(kept, kept) != mapping.get(dropped, dropped):
            rr = [r for r in per_pairs if {r["a"], r["b"]} == {kept, dropped}]
            prior_reasons[f"{rr[0]['decision']}/{rr[0]['reason']}" if rr else "NOT_A_CANDIDATE_PAIR_UNDER_V2_RULES"] += 1
    verif = {"prior_merges_total": len(prior_pairs), "prior_merges_reconfirmed": prior_same, "prior_merges_not_reconfirmed": len(prior_pairs) - prior_same, "prior_merges_not_reconfirmed_reasons": dict(prior_reasons),
             "mapping_has_cycle": False, "mapping_depth_one": chain_ok, "evidence_set_preserved": before_evid == after_evid, "evidence_keys_before": len(before_evid), "evidence_keys_after": len(after_evid),
             "qa_tiers_only_original_three": qa_ok, "tier_in_edge_key": True, "direction_preserved_for_every_original_edge": direction_ok,
             "new_self_loops_from_merges": len(new_loops),
             "new_self_loops_detail": [{"tier": k[0], "predicate": k[2], "canonical": k[1], "original_subject": a, "original_object": b, "status": k[4]} for k, a, b in new_loops[:10]], "ut_links_reverted_for_self_loop": len(reverted_ut), "person_merges_rejected_by_cluster_constraints": rejected_person,
             "control_replay_prior_merges_only": {"nodes": len(c_nodes), "edge_rows": len(c_edges), "evidence_rows": sum(len(v) for v in c_ev.values()),
                                                   "baseline_nodes": base_e["nodes"], "baseline_edge_rows": base_e["edge_rows"], "equals_baseline": len(c_nodes) == base_e["nodes"] and len(c_edges) == base_e["edge_rows"]}}
    final_hash = hashlib.sha256(json.dumps(sorted((r[0], r[1], r[2], r[3], r[4]) for r in rows), ensure_ascii=False).encode()).hexdigest()[:16]  # decisions only (evidence snippets are not part of identity)
    stats = {"version": VERSION, "watermark": wm, "mapping_hash": final_hash, "verification": verif, "before": {"validated": base_v, "exploratory": base_e}, "after": {"validated": sv, "exploratory": se},
             "mapping": {"nodes_original": len({x for e in w.edges for x in (e["s_key"], e["o_key"])}), "canonical_nodes": len(canon_nodes), "merged_away": sum(len(m) - 1 for m in groups.values() if len(m) > 1),
                         "clusters": sum(1 for m in groups.values() if len(m) > 1), "by_kind_decision": {f"{a}/{b}": n for (a, b), n in Counter((r[2], r[3]) for r in rows).most_common()},
                         "by_reason": {f"{a}/{b}/{c}": n for (a, b, c), n in Counter((r[2], r[3], r[4]) for r in rows).most_common(40)}},
             "viewer": viewer, "csv": {"nodes_rows": nn, "edges_rows": ne}}
    (out / "stats_v2.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    sample = review_sample(R, out, w, mapping, ents_v2, groups, ut_rows, org_pairs, per_pairs)
    stats["review_sample_rows"] = sample
    (out / "report_v2.md").write_text(render_report(stats, R), encoding="utf-8")
    (out / "stats_v2.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return {"canonical_nodes": len(canon_nodes), "merged_away": stats["mapping"]["merged_away"], "validated": {k: sv[k] for k in ("nodes", "edge_rows", "unique_triples_ignoring_status_and_tier", "connected_components", "largest_component")},
            "exploratory": {k: se[k] for k in ("nodes", "edge_rows", "unique_triples_ignoring_status_and_tier", "connected_components", "largest_component")}, "verification": verif}


def write_nodes_csv(path: Path, base_csv: Path, ents, ut_rows, mapping, reverted) -> None:
    rows = list(csv.DictReader(base_csv.open(encoding="utf-8-sig")))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        cols = list(rows[0].keys()) + ["n_original_ids", "original_ids", "aliases"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            e = ents[r["node_id"]]
            mem = e["members"]
            r["n_original_ids"] = len(mem)
            r["original_ids"] = "|".join(mem[:50]) + ("|..." if len(mem) > 50 else "")
            r["aliases"] = "|".join(sorted({m for m in [x.split(":", 2)[-1] if x.startswith("text:") else "" for x in mem] if m})[:30])
            w.writerow(r)


def export_viewer_v2(R, out, ents, edge_rows, evd, pub, gv, ge, comp_v, comp_e, com_v, com_e, w) -> dict:
    meta = {"snapshot_id": R.meta("watermark")["snapshot_id"], "taken_at": R.meta("watermark")["taken_at"], "nlp_processed": R.meta("watermark")["articles_nlp_processed"], "has_aliases": True, "er_version": VERSION}
    tmpdir = out / "_viewer"
    shutil.rmtree(tmpdir, ignore_errors=True)
    tmpdir.mkdir()
    vm = pv.export_viewer(tmpdir, ents, edge_rows, evd, pub, gv, ge, comp_v, comp_e, com_v, com_e, meta)
    nodes = sorted(ge.nodes)
    names = {k: dict(w.ents[k].names) if k in w.ents else {} for e in ents.values() for k in e["members"]}
    alias, astr = {}, {}
    for i, k in enumerate(nodes):
        mem = ents[k]["members"]
        if len(mem) > 1 or any(m.startswith("text:") for m in mem):
            alias[i] = [[m, (max(names.get(m, {m: 0}), key=lambda n: names[m][n]) if names.get(m) else m), w.ents[m].status if m in w.ents else "", m.split(":")[0] if m.startswith("text:") else ""] for m in mem[:60]]
            astr[i] = " ".join(a[1] for a in alias[i])
    data = out / "viewer_v2_data"
    if data.exists():
        shutil.rmtree(data)
    shutil.copytree(tmpdir / "data", data)
    (data / "aliases.js").write_text("window.VCKG_ALIAS={};window.VCKG_ALIASSTR={};".format(json.dumps(alias, ensure_ascii=False, separators=(",", ":")), json.dumps(astr, ensure_ascii=False, separators=(",", ":"))), encoding="utf-8")
    html = (tmpdir / "viewer.html").read_text(encoding="utf-8")
    html = html.replace("VCKG exploratory graph", "VCKG exploratory graph V2 (entity resolution)").replace('src="data/', 'src="viewer_v2_data/').replace('s.src="data/evidence.js"', 's.src="viewer_v2_data/evidence.js"')
    html = html.replace('<script src="viewer_v2_data/graph.js"></script>', '<script src="viewer_v2_data/graph.js"></script><script src="viewer_v2_data/aliases.js"></script>')
    html = html.replace("N[i][0].toLowerCase().includes(q)", "(N[i][0]+\" \"+((window.VCKG_ALIASSTR&&VCKG_ALIASSTR[i])||\"\")).toLowerCase().includes(q)")
    html = html.replace("function showNode(n){sel=n;", "function aliasHtml(n){const a=window.VCKG_ALIAS&&VCKG_ALIAS[n];if(!a)return\"\";return '<div class=\"warn\"><b>Canonical node gộp '+a.length+' original ID</b> (có thể rollback bằng entity_map):<br>'+a.map(x=>'<small>'+x[1]+' <i>['+x[0]+']</i>'+(x[2]?' · '+x[2]:'')+'</small>').join('<br>')+'</div>'}\nfunction showNode(n){sel=n;window._a=aliasHtml(n);")
    html = html.replace('$("info").innerHTML=h;}\nfunction loadEv', '$("info").innerHTML=h+(window._a||"");}\nfunction loadEv')
    (out / "viewer_v2.html").write_text(html, encoding="utf-8")
    shutil.rmtree(tmpdir, ignore_errors=True)
    return {**vm, "aliases_nodes": len(alias), "html": str(out / "viewer_v2.html")}


def review_sample(R, out: Path, w, mapping, ents_v2, groups, ut_rows, org_pairs, per_pairs, n_per: int = 12) -> int:
    rng = random.Random(SEED)
    deg = Counter()
    for e in w.edges:
        deg[e["s_key"]] += 1
        deg[e["o_key"]] += 1
    rows = []

    def add(stratum, kind, members, canonical, decision, reason, evidence, impact):
        rows.append({"stratum": stratum, "kind": kind, "original_ids": "|".join(members), "original_names": "|".join(w.ents[m].name for m in members if m in w.ents), "canonical_id": canonical,
                     "decision": decision, "reason": reason, "edges_affected": impact, "evidence": (evidence or "")[:600], "human_label (CORRECT/WRONG/UNSURE)": "", "human_note": ""})
    pm = [r for r in per_pairs if r["decision"] == "VERIFIED_MERGE"]
    risky = [r for r in pm if json.loads(r["meta"]).get("tokens", 3) < 3 or json.loads(r["meta"]).get("prior_merge") is False or (json.loads(r["meta"]).get("date_gap_days") or 0) > 365]
    for stratum, pool in (("person_merge_risky", risky), ("person_merge_other", [r for r in pm if r not in risky]), ("person_merge_llm", [r for r in pm if "LLM" in r["reason"]])):
        for r in rng.sample(pool, min(n_per, len(pool))):
            add(stratum, "PERSON", [r["a"], r["b"]], mapping.get(r["a"], r["a"]), "VERIFIED_MERGE", r["reason"], r["evidence"], deg[r["a"]] + deg[r["b"]])
    om = [r for r in org_pairs if r["decision"] == "VERIFIED_MERGE"]
    for r in sorted(om, key=lambda r: -(deg[r["a"]] + deg[r["b"]]))[:n_per]:
        add("org_merge_high_impact", "ORG", [r["a"], r["b"]], mapping.get(r["a"], r["a"]), "VERIFIED_MERGE", r["reason"], r["evidence"], deg[r["a"]] + deg[r["b"]])
    for r in rng.sample(om, min(n_per, len(om))):
        add("org_merge_random", "ORG", [r["a"], r["b"]], mapping.get(r["a"], r["a"]), "VERIFIED_MERGE", r["reason"], r["evidence"], deg[r["a"]] + deg[r["b"]])
    for dec in ("AMBIGUOUS", "DISTINCT"):
        pool = [r for r in org_pairs if r["decision"] == dec]
        for r in sorted(pool, key=lambda r: -(deg[r["a"]] + deg[r["b"]]))[:6]:
            add(f"org_{dec.lower()}_high_impact", "ORG", [r["a"], r["b"]], r["a"], dec, r["reason"], r["conflicts"], deg[r["a"]] + deg[r["b"]])
    for dec in ("AMBIGUOUS", "DISTINCT"):
        pool = [r for r in per_pairs if r["decision"] == dec]
        for r in rng.sample(pool, min(8, len(pool))):
            add(f"person_{dec.lower()}", "PERSON", [r["a"], r["b"]], r["a"], dec, r["reason"], r["conflicts"], deg[r["a"]] + deg[r["b"]])
    utm = [(k, r) for k, r in ut_rows.items() if r["decision"] == "VERIFIED_MERGE" and mapping.get(k, k) != k]
    byreason: dict[str, list] = defaultdict(list)
    for k, r in utm:
        byreason[r["reason"]].append((k, r))
    for rs, lst in byreason.items():
        for k, r in rng.sample(lst, min(8, len(lst))):
            add(f"ut_link_{rs}", "UT", [k], mapping.get(k, k), "VERIFIED_MERGE", rs, r["evidence"], deg[k])
    keep = [(k, r) for k, r in ut_rows.items() if r["decision"] != "VERIFIED_MERGE"]
    for k, r in sorted(keep, key=lambda t: -deg[t[0]])[:10]:
        add("ut_unresolved_high_impact", "UT", [k], k, r["decision"], r["reason"], r["meta"], deg[k])
    path = out / "manual_review_sample.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    return len(rows)


def render_report(st: dict, R) -> str:
    b, a = st["before"], st["after"]
    L = [f"# Global Entity Resolution {st['version']} - before/after", "",
         f"Snapshot {st['watermark']['snapshot_id']} ({st['watermark']['taken_at']}), {st['watermark']['articles_nlp_processed']} NLP-processed articles, {st['watermark']['n_src_edges']} source edge rows.",
         "**No gold labels: merges below are verified by deterministic rules, not by accuracy measurement. Fewer nodes/edges is the expected direction of correct resolution. QA tiers are unchanged.**", "",
         "| metric | before (snapshot) | after V2 |", "|---|---|---|"]
    for sc in ("exploratory", "validated"):
        for k, lab in (("nodes", "nodes"), ("edge_rows", "edge-tier rows"), ("unique_triples_ignoring_status_and_tier", "unique (s,p,o) triples"), ("relation_types", "relation types"),
                       ("connected_components", "connected components"), ("largest_component", "largest component")):
            L.append(f"| {sc} {lab} | {b[sc][k]} | {a[sc][k]} |")
        L.append(f"| {sc} nodes by type | {b[sc]['nodes_by_type']} | {a[sc]['nodes_by_type']} |")
        L.append(f"| {sc} edges by tier | {b[sc]['edges_by_tier']} | {a[sc]['edges_by_tier']} |")
    db = R.db
    deg = Counter()
    w = R.load()
    for e in w.edges:
        deg[e["s_key"]] += 1
        deg[e["o_key"]] += 1

    def nm(k):
        return w.ents[k].name if k in w.ents else k
    L += ["", "## Stage runtime / Qwen"]
    for r in db.execute("SELECT name, status, finished_at, stats FROM stages"):
        sj = json.loads(r["stats"] or "{}")
        L.append(f"- {r['name']}: {r['status']} in {sj.get('seconds')} s")
    q = json.loads(db.execute("SELECT stats FROM stages WHERE name='qwen'").fetchone()[0] or "{}")
    L.append(f"- Qwen3.5-9B (advisory only, budget {q.get('budget')}): live calls total {q.get('live_calls_total')}, SAME accepted by the verifier {q.get('same_accepted')}, answers rejected by the verifier {q.get('answers_rejected_by_verifier')}, DIFFERENT accepted {q.get('different_accepted')}, unsure {q.get('unsure')}")
    L += ["", "## Notable verified ORGANISATION merges (by edges affected)"]
    for r in sorted(db.execute("SELECT a,b,reason,evidence FROM org_pairs WHERE decision='VERIFIED_MERGE'").fetchall(), key=lambda r: -(deg[r["a"]] + deg[r["b"]]))[:12]:
        ev = (json.loads(r["evidence"]) or [{}])[0]
        L.append(f"- {nm(r['a'])} <-> {nm(r['b'])} ({r['reason']}, {deg[r['a']] + deg[r['b']]} edge ends): \"{ev.get('snippet', '')[:140]}\"")
    L += ["", "## Notable verified PERSON merges (by edges affected)"]
    for r in sorted(db.execute("SELECT a,b,reason,meta FROM person_pairs WHERE decision='VERIFIED_MERGE'").fetchall(), key=lambda r: -(deg[r["a"]] + deg[r["b"]]))[:10]:
        m = json.loads(r["meta"])
        L.append(f"- {nm(r['a'])} (orgs {m.get('shared_orgs')}, roles {m.get('roles')}, date gap {m.get('date_gap_days')} d, {r['reason']})")
    L += ["", "## Rejected / not merged (by edges affected)"]
    for dec in ("DISTINCT", "AMBIGUOUS"):
        for r in sorted(db.execute("SELECT a,b,reason,conflicts FROM org_pairs WHERE decision=?", (dec,)).fetchall(), key=lambda r: -(deg[r["a"]] + deg[r["b"]]))[:6]:
            L.append(f"- ORG {dec}: {nm(r['a'])} / {nm(r['b'])}: {r['reason']} {json.loads(r['conflicts'])[:1]}")
    for r in db.execute("SELECT a,b,reason,conflicts FROM person_pairs WHERE decision='DISTINCT' LIMIT 6"):
        L.append(f"- PERSON DISTINCT: {nm(r['a'])}: {r['reason']} {json.loads(r['conflicts'])[:1]}")
    ut = Counter()
    for r in db.execute("SELECT decision, reason FROM ut_links"):
        ut[f"{r['decision']}/{r['reason']}"] += 1
    L += ["", "## UNRESOLVED_TEXT outcome", json.dumps(dict(ut.most_common()), ensure_ascii=False)]
    L += ["", "## Mapping", f"- original node keys: {st['mapping']['nodes_original']}; canonical nodes: {st['mapping']['canonical_nodes']}; merged away: {st['mapping']['merged_away']} in {st['mapping']['clusters']} clusters",
          f"- decisions by (kind, decision): {st['mapping']['by_kind_decision']}", f"- top reasons: {st['mapping']['by_reason']}", "", "## Verification invariants", json.dumps(st["verification"], ensure_ascii=False, indent=1)]
    return "\n".join(L)
