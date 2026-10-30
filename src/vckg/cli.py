"""CLI: python -m vckg.cli {identity-load, crawl, crawl-targeted, process, prototype}.

All paths are under the project root (T:\\VietnamCorporateGraph). Run `. .\\scripts\\enter-project.ps1` first."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from pathlib import Path

from vckg.entity_linking.identity import HandwrittenSeedProvider, VietstockSitemapProvider, load_provider
from vckg.entity_linking.resolver import EntityResolver
from vckg.entity_linking.store import RegistryStore
from vckg.models import Article
from vckg.pipeline import Counters, process_article
from vckg.relation_extraction.candidates import load_config, load_relations
from vckg.storage.jsonl import write_jsonl
from vckg.storage.sqlite import Staging
from vckg.validation.evidence import EdgeStore

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DB = ROOT / "data/registry/registry.sqlite"
STAGING_DB = ROOT / "data/staging/staging.sqlite"
LLM_CACHE_DB = ROOT / "data/staging/llm_cache.sqlite"
SEED = ROOT / "data/registry/seed_registry.json"
REL_PATH = str(ROOT / "config/relations.yaml")

# Hypothetical sentences (not real articles) for the smoke prototype.
FIXTURE = [
    "Ông Phạm Nhật Vượng là Chủ tịch HĐQT Tập đoàn Vingroup.",
    "Vinhomes là công ty con của Vingroup.",
    "Ông Phạm Nhật Vượng không phải là Chủ tịch HĐQT Vinhomes.",
    "Vingroup dự kiến sẽ mua lại VinFast trong năm tới.",
    "Ngân hàng VPBank ký hợp đồng tín dụng với Tập đoàn Hòa Phát.",
    "Ủy ban Chứng khoán Nhà nước xử phạt Công ty cổ phần FPT vì công bố thông tin chậm.",
    "Vingroup và Hòa Phát cùng có mặt trong danh sách VN30.",
]


def build_runtime(use_ner: bool, use_llm: bool, registry_path: Path | str, llm_cache: bool = True):
    store = RegistryStore(registry_path)
    resolver = EntityResolver(store)
    rel = load_relations(REL_PATH)
    cfg = load_config(REL_PATH)
    edges = EdgeStore(status_policy=cfg.get("status_policy"))
    ner = verifier = None
    if use_ner:
        from vckg.ner.gliner_adapter import GlinerNER
        ner = GlinerNER()
    if use_llm:
        from vckg.relation_extraction.qwen_verifier import LLMCache, QwenVerifier
        verifier = QwenVerifier(predicates=list(rel), cache=LLMCache(LLM_CACHE_DB) if llm_cache else None)
        if not verifier.is_available():
            print("UNAVAILABLE: Ollama/qwen3.5:9b not reachable; verifier disabled (no edge can become official)")
            verifier = None
    return resolver, rel, edges, ner, verifier


def run_pipeline(articles: list[Article], out_dir: Path, use_ner: bool, use_llm: bool,
                 registry_path: Path | str, llm_cache: bool = True, sentence_ner: bool = True) -> dict:
    t0 = time.perf_counter()
    resolver, rel, edges, ner, verifier = build_runtime(use_ner, use_llm, registry_path, llm_cache)
    reg_before = resolver.store.stats()
    cn = Counters()
    mention_rows, cands, verdict_rows, outcome_rows = [], [], [], []
    for a in articles:
        r = process_article(a, rel, resolver, edges, ner, verifier, cn, sentence_ner=sentence_ner)
        mention_rows += [{"article_id": a.article_id, **m.model_dump(mode="json")} for m in r.mentions]
        cands += r.candidates
        for c in r.candidates:
            v = r.verdicts.get(c.candidate_id)
            oc = edges.outcomes.get(c.candidate_id)
            if c.candidate_id in r.verdicts:
                verdict_rows.append({"candidate_id": c.candidate_id, "model": getattr(verifier, "model", ""),
                                     "prompt_version": getattr(verifier, "prompt_version", ""),
                                     "verdict": v.model_dump(mode="json") if v else None})
            outcome_rows.append({
                "article_id": a.article_id, "source_url": a.url, "candidate_id": c.candidate_id, "predicate": c.predicate,
                "subject_text": c.subject.text, "subject_type": c.subject.label.value, "subject_entity": c.subject.entity_id or "",
                "subject_status": c.subject_entity_status or "", "object_text": c.object.text, "object_type": c.object.label.value,
                "object_entity": c.object.entity_id or "", "object_status": c.object_entity_status or "",
                "pattern_id": c.pattern_id, "direction_source": c.direction_source, "rule_status": c.factual_status.value,
                "modality_cues": "|".join(c.modality_cues), "llm_valid": "" if v is None else v.valid,
                "llm_status": "" if v is None else v.factual_status.value, "llm_rejection": "" if v is None else v.rejection_reason,
                "outcome": oc.outcome if oc else "", "reasons": "|".join(x.value for x in oc.reasons) if oc else "",
                "evidence": c.evidence_text})
    merged = resolver.consolidate_persons()
    edges.remap(resolver.store.canonical_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "entities.jsonl").write_text("".join(json.dumps(m, ensure_ascii=False) + "\n" for m in mention_rows), encoding="utf-8")
    write_jsonl(out_dir / "candidates.jsonl", cands)
    (out_dir / "verdicts.jsonl").write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in verdict_rows), encoding="utf-8")
    write_jsonl(out_dir / "relations.jsonl", edges.edges.values())
    write_jsonl(out_dir / "relations_official.jsonl", edges.official_edges())
    write_jsonl(out_dir / "relations_candidate.jsonl", edges.candidate_edges())
    if outcome_rows:
        with (out_dir / "candidate_outcomes.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(outcome_rows[0].keys()))
            w.writeheader()
            w.writerows(outcome_rows)
    summary = {
        "articles": len(articles), "ner": "gliner2.5" if ner else "off",
        "verifier": f"{verifier.model} prompt={verifier.prompt_version}" if verifier else "off",
        "counters": cn.as_dict(), "person_clusters_merged": merged,
        "edges_total": len(edges.edges), "edges_official": len(edges.official_edges()),
        "edges_candidate_only": len(edges.candidate_edges()),
        "official_by_predicate": _count([e.predicate for e in edges.official_edges()]),
        "candidate_by_predicate": _count([e.predicate for e in edges.candidate_edges()]),
        "registry_before": reg_before, "registry_after": resolver.store.stats(),
        "llm": verifier.stats.as_dict() if verifier else None,
        "wall_seconds": round(time.perf_counter() - t0, 1),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _count(xs):
    d: dict = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("identity-load")
    p.add_argument("--provider", choices=["seed", "vietstock"], required=True)
    p.add_argument("--registry", default=str(REGISTRY_DB))
    p = sub.add_parser("prototype")
    p.add_argument("--no-ner", action="store_true")
    p.add_argument("--no-llm", action="store_true")
    p = sub.add_parser("crawl")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--source", default=None)
    p = sub.add_parser("crawl-targeted")
    p.add_argument("--per-source", type=int, default=15)
    p.add_argument("--min-score", type=int, default=3)
    p.add_argument("--source", action="append", default=None)
    p.add_argument("--out", default=str(ROOT / "data/outputs/experiment/selected_articles.jsonl"))
    p = sub.add_parser("process")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--ids-from", default=None, help="restrict to article_ids found in <dir>/entities.jsonl")
    p.add_argument("--selection", default=None, help="restrict to URLs in a selected_articles.jsonl")
    p.add_argument("--out", default=str(ROOT / "data/outputs/articles"))
    p.add_argument("--registry", default=str(REGISTRY_DB))
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--doc-ner", action="store_true", help="whole-article NER instead of sentence-level (comparison only)")
    p = sub.add_parser("annotation-export")
    p.add_argument("--runs", nargs="+", required=True, help="run output dirs (with entities.jsonl + candidate_outcomes.csv)")
    p.add_argument("--n", type=int, default=120)
    p.add_argument("--seed", type=int, default=13)
    p.add_argument("--out", default=str(ROOT / "reports/phase4_annotation_sample.csv"))
    p = sub.add_parser("evaluate")
    p.add_argument("csv")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    if args.cmd == "identity-load":
        store = RegistryStore(args.registry)
        if args.provider == "seed":
            print(json.dumps(load_provider(store, HandwrittenSeedProvider(SEED)), ensure_ascii=False))
        else:
            from vckg.crawlers.http import PoliteClient
            from vckg.crawlers.runner import load_sources
            c = load_sources(ROOT / "config/sources.yaml")["crawler"]
            client = PoliteClient(c["user_agent"], c["min_delay_seconds"], 60.0, c["max_retries"], c["backoff_base"])
            print(json.dumps(load_provider(store, VietstockSitemapProvider(client)), ensure_ascii=False))
        print(json.dumps(store.stats(), ensure_ascii=False, indent=2))
    elif args.cmd == "prototype":
        arts = [Article(article_id=f"fixture-{i}", url=f"fixture://sentence/{i}", source="fixture", text=t) for i, t in enumerate(FIXTURE)]
        proto_reg = ROOT / "data/registry/prototype.sqlite"  # seed names only (PROVISIONAL, handwritten); no provider fetch
        load_provider(RegistryStore(proto_reg), HandwrittenSeedProvider(SEED))
        s = run_pipeline(arts, ROOT / "data/outputs/prototype", not args.no_ner, not args.no_llm, proto_reg, llm_cache=False)
        print(json.dumps(s, ensure_ascii=False, indent=2))
    elif args.cmd == "crawl":
        from vckg.crawlers.http import PoliteClient
        from vckg.crawlers.runner import crawl_feed, load_sources
        cfg = load_sources(ROOT / "config/sources.yaml")
        c = cfg["crawler"]
        client = PoliteClient(c["user_agent"], c["min_delay_seconds"], c["timeout_seconds"], c["max_retries"], c["backoff_base"])
        st = Staging(STAGING_DB)
        for key, src in cfg["sources"].items():
            if args.source and key != args.source:
                continue
            for feed in src.get("feeds", [])[:1]:
                print(key, feed, dict(crawl_feed(key, feed, client, st, limit=args.limit)))
        print("articles in staging:", st.count_articles())
    elif args.cmd == "crawl-targeted":
        from vckg.crawlers.http import PoliteClient
        from vckg.crawlers.runner import load_sources
        from vckg.crawlers.targeted import crawl_targeted, dump_selection
        cfg = load_sources(ROOT / "config/sources.yaml")
        c = cfg["crawler"]
        client = PoliteClient(c["user_agent"], c["min_delay_seconds"], c["timeout_seconds"], c["max_retries"], c["backoff_base"])
        st = Staging(STAGING_DB)
        stats, selected, arts = crawl_targeted(client, st, cfg["sources"], args.per_source, args.min_score, args.source)
        dump_selection(args.out, selected)
        print(json.dumps(dict(stats), ensure_ascii=False, indent=2))
        print("selected+staged:", len(arts), "| total in staging:", st.count_articles())
    elif args.cmd == "annotation-export":
        from vckg.annotation import export_from_runs
        st = Staging(STAGING_DB)
        print(json.dumps(export_from_runs([Path(r) for r in args.runs], st.get_articles(), args.out, args.n, args.seed), ensure_ascii=False, indent=2))
    elif args.cmd == "evaluate":
        from vckg.evaluation import evaluate, load
        print(json.dumps(evaluate(load(args.csv)), ensure_ascii=False, indent=2))
    elif args.cmd == "process":
        st = Staging(STAGING_DB)
        arts = st.get_articles()
        if args.ids_from:
            ids = {json.loads(x)["article_id"] for x in (Path(args.ids_from) / "entities.jsonl").read_text(encoding="utf-8").splitlines()}
            arts = [a for a in arts if a.article_id in ids]
        if args.selection:
            urls = {json.loads(x).get("url") for x in Path(args.selection).read_text(encoding="utf-8").splitlines() if x.strip()}
            arts = [a for a in arts if a.url in urls]
        if args.limit:
            arts = arts[: args.limit]
        s = run_pipeline(arts, Path(args.out), True, not args.no_llm, args.registry, llm_cache=not args.no_cache, sentence_ner=not args.doc_ner)
        print(json.dumps(s, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()



