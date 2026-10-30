"""Standard KPI definitions (Phase 5). Computed from a run directory + its registry DB.

 - graph_entity_nodes: distinct domain entities in OFFICIAL edges only (no registry-only rows, no articles/sources).
 - official_unique_edges: unique (subject, predicate, object, validity-window); N sources for one fact = 1 edge.
 - candidate_unique_edges: unique candidate-only edges (never official), same dedup key.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def _read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def edge_event_key(e: dict) -> tuple:
    """Same entities+predicate but different validity windows are different events (e.g. two tenures)."""
    vf = sorted({r.get("valid_from") or "" for r in e["evidence"]})
    vt = sorted({r.get("valid_to") or "" for r in e["evidence"]})
    window = (vf[-1] if vf else "", vt[-1] if vt else "")
    return (e["subject_id"], e["predicate"], e["object_id"], window)


def unique_edges(edges: list[dict]) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for e in edges:
        k = edge_event_key(e)
        if k in out:
            seen = {(r["article_id"], r["evidence_start"], r["evidence_end"]) for r in out[k]["evidence"]}
            out[k]["evidence"] += [r for r in e["evidence"] if (r["article_id"], r["evidence_start"], r["evidence_end"]) not in seen]
        else:
            out[k] = {**e, "evidence": list(e["evidence"])}
    return out


def compute_kpis(run_dir: str | Path, registry_db: str | Path | None = None) -> dict:
    d = Path(run_dir)
    summary = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    official = unique_edges(_read(d / "relations_official.jsonl"))
    official_keys = {(k[0], k[1], k[2]) for k in official}
    cands = {k: v for k, v in unique_edges(_read(d / "relations_candidate.jsonl")).items() if (k[0], k[1], k[2]) not in official_keys}
    nodes = {k[0] for k in official} | {k[2] for k in official}
    n_art = summary["articles"]
    c = summary["counters"]
    reg = {}
    if registry_db and Path(registry_db).exists():
        db = sqlite3.connect(str(registry_db))
        q = lambda s: db.execute(s).fetchone()[0]
        reg = {
            "registry_entities": q("SELECT COUNT(*) FROM entities WHERE merged_into IS NULL"),
            "external_verified_entities": q("SELECT COUNT(*) FROM entities WHERE merged_into IS NULL AND resolution_status IN ('VERIFIED','EXTERNAL_VERIFIED')"),
            "article_grounded_entities": q("SELECT COUNT(*) FROM entities WHERE merged_into IS NULL AND resolution_status='ARTICLE_GROUNDED'"),
            "provisional_entities": q("SELECT COUNT(*) FROM entities WHERE merged_into IS NULL AND resolution_status='PROVISIONAL'"),
        }
        db.close()
    else:
        ra = summary["registry_after"]["by_status"]
        reg = {"registry_entities": summary["registry_after"]["entities_active"],
               "external_verified_entities": ra.get("VERIFIED", 0) + ra.get("EXTERNAL_VERIFIED", 0),
               "article_grounded_entities": ra.get("ARTICLE_GROUNDED", 0), "provisional_entities": ra.get("PROVISIONAL", 0)}
    art_with_official = {r["article_id"] for e in official.values() for r in e["evidence"]}
    linked = c["linked_verified"] + c["linked_provisional"] + c.get("linked_grounded", 0)
    inscope = max(c["mentions_in_scope"], 1)
    rel_types = sorted({k[1] for k in official})
    llm = summary.get("llm") or {}
    return {
        **reg,
        "graph_entity_nodes": len(nodes),
        "official_unique_edges": len(official),
        "candidate_unique_edges": len(cands),
        "official_relation_types": len(rel_types),
        "official_relation_type_names": rel_types,
        "candidate_relation_type_names": sorted({k[1] for k in cands}),
        "articles_processed": n_art,
        "articles_with_official_edges": len(art_with_official),
        "official_edges_per_article": round(len(official) / n_art, 4) if n_art else None,
        "candidates_per_article": round(c["candidates"] / n_art, 4) if n_art else None,
        "entity_linking_rate_in_scope": round(linked / inscope, 4),
        "entity_linking_rate_external_verified_only": round(c["linked_verified"] / inscope, 4),
        "llm_calls_per_article": round((llm.get("llm_calls", 0) + llm.get("cache_hits", 0)) / n_art, 4) if n_art else None,
        "llm_live_calls": llm.get("llm_calls"), "llm_cache_hits": llm.get("cache_hits"),
        "evidence_records_official": sum(len(e["evidence"]) for e in official.values()),
        "duplicate_edges_merged_in_official": sum(len(e["evidence"]) - 1 for e in official.values()),
        "official_by_predicate": {p: sum(1 for k in official if k[1] == p) for p in rel_types},
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(compute_kpis(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), ensure_ascii=False, indent=2))
