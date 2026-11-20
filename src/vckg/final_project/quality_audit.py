"""Export diagnostic and random benchmark samples; score only full-article human labels."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sqlite3
from collections import defaultdict
from pathlib import Path

from vckg.final_project.app import snapshot_dir
from vckg.final_project.build import ER, EXCLUSIONS, _endpoints_ok, _official, _read

FIELDS = ["sample_group", "qa_tier", "edge_id", "edge_uid", "relation_type", "subject_name", "subject_type", "object_name",
          "object_type", "factual_status", "quarantine_classes", "evidence_text", "source_url",
          "article_id", "published_at", "valid_relation", "valid_endpoints", "valid_evidence", "valid_status",
          "reviewer", "review_mode", "notes"]
TARGET = {"VALIDATED": 200, "QUARANTINE": 80, "EXCLUDED": 20}
GOLD_FIELDS = ("valid_relation", "valid_endpoints", "valid_evidence", "valid_status")


def _group(row: dict, nodes: dict[str, dict] | None = None, exclusions: set[tuple[str, str]] | None = None) -> str | None:
    if nodes is None and row.get("sample_group"):
        return row["sample_group"]
    if row["qa_tier"] in {"LEGACY_OFFICIAL", "QA_PASS"}:
        if exclusions is not None and (row["qa_tier"], row["edge_id"]) in exclusions:
            return "EXCLUDED"
        return "VALIDATED" if nodes is not None and _official(row) and _endpoints_ok(row, nodes) else "EXCLUDED"
    if row["qa_tier"] == "QUARANTINE":
        return "QUARANTINE"
    return None


def export(er: Path, output: Path, target: dict[str, int] = TARGET) -> dict:
    nodes = {row["node_id"]: row for row in _read(er / "nodes_v2.csv")}
    exclusions = {(row["qa_tier"], row["edge_id"]) for row in _read(EXCLUSIONS)} if EXCLUSIONS.exists() else set()
    by_edge = {}
    for row in _read(er / "edges_v2.csv"):
        group = _group(row, nodes, exclusions)
        if not group:
            continue
        row["sample_group"] = group
        key = (group, row["qa_tier"], row["edge_id"])
        if key not in by_edge or (row["evidence_text"] and not by_edge[key]["evidence_text"]):
            by_edge[key] = row
    by_group = defaultdict(lambda: defaultdict(list))
    for row in by_edge.values():
        by_group[_group(row)][row["relation_type"]].append(row)
    randomizer = random.Random(20261120)
    selected = []
    for group, n in target.items():
        buckets = by_group[group]
        for bucket in buckets.values():
            randomizer.shuffle(bucket)
        names = sorted(buckets)
        while len([r for r in selected if _group(r) == group]) < n and names:
            for name in names[:]:
                if buckets[name]:
                    selected.append(buckets[name].pop())
                else:
                    names.remove(name)
                if len([r for r in selected if _group(r) == group]) >= n:
                    break
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in FIELDS} for row in selected)
    return {"sample": str(output), "selected": {group: sum(_group(r) == group for r in selected) for group in target},
            "method": "Diagnostic stratification by relation type; not a representative overall-precision sample."}


def export_benchmark(snapshot: Path, output: Path, *, size: int = 200, seed: int = 20261120) -> dict:
    """Uniformly sample unique (subject, predicate, object) triples in the application graph."""
    if size < 1:
        raise ValueError("Benchmark sample size must be positive")
    randomizer = random.Random(seed)
    with sqlite3.connect(snapshot / "profile.sqlite") as connection:
        connection.row_factory = sqlite3.Row
        edges = connection.execute("""
            SELECT e.edge_uid,e.edge_id,e.tier,e.subject_id,e.predicate,e.object_id,e.factual_status,
                   s.name AS subject_name,s.entity_type AS subject_type,
                   o.name AS object_name,o.entity_type AS object_type
            FROM edges e JOIN nodes s ON s.node_id=e.subject_id JOIN nodes o ON o.node_id=e.object_id
            ORDER BY e.edge_uid
        """).fetchall()
        triples: dict[tuple[str, str, str], list[sqlite3.Row]] = defaultdict(list)
        for edge in edges:
            triples[(edge["subject_id"], edge["predicate"], edge["object_id"])].append(edge)
        selected = []
        for triple in randomizer.sample(sorted(triples), min(size, len(triples))):
            edge = randomizer.choice(triples[triple])
            evidence = connection.execute("""
                SELECT article_id,source_url,published_at,evidence_text FROM evidence
                WHERE edge_uid=? ORDER BY evidence_id
            """, (edge["edge_uid"],)).fetchall()
            if not evidence:
                raise ValueError(f"Edge without evidence: {edge['edge_uid']}")
            quote = randomizer.choice(evidence)
            selected.append({"sample_group": "BENCHMARK_RANDOM", "qa_tier": edge["tier"],
                             "edge_id": edge["edge_id"], "edge_uid": edge["edge_uid"],
                             "relation_type": edge["predicate"], "subject_name": edge["subject_name"],
                             "subject_type": edge["subject_type"], "object_name": edge["object_name"],
                             "object_type": edge["object_type"], "factual_status": edge["factual_status"],
                             **dict(quote)})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in FIELDS} for row in selected)
    return {"sample": str(output), "sampled": len(selected), "population_unique_triples": len(triples),
            "seed": seed, "method": "Simple random sample of unique triples; one random evidence record per triple."}


def wilson(success: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if not total:
        return 0.0, 0.0
    p = success / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return center - half, center + half


def evaluate(path: Path) -> dict:
    rows = _read(path)
    reviewed = [row for row in rows if row.get("reviewer", "").strip() and row.get("review_mode") == "HUMAN_FULL_ARTICLE"
                and all(row.get(field) in {"YES", "NO"} for field in GOLD_FIELDS)]
    benchmark = [row for row in rows if _group(row) == "BENCHMARK_RANDOM"]
    benchmark_reviewed = [row for row in reviewed if _group(row) == "BENCHMARK_RANDOM"]
    correct = sum(all(row[field] == "YES" for field in GOLD_FIELDS) for row in benchmark_reviewed)
    complete = bool(benchmark) and len(benchmark_reviewed) == len(benchmark)
    diagnostic = [row for row in reviewed if _group(row) == "VALIDATED"]
    by_relation: dict[str, dict[str, int]] = defaultdict(lambda: {"reviewed": 0, "correct": 0})
    for row in diagnostic:
        result = by_relation[row["relation_type"]]
        result["reviewed"] += 1
        result["correct"] += int(all(row[field] == "YES" for field in GOLD_FIELDS))
    return {"total_sampled": len(rows), "independently_human_reviewed": len(reviewed),
            "benchmark_sampled": len(benchmark), "benchmark_reviewed": len(benchmark_reviewed),
            "benchmark_correct": correct, "diagnostic_validated_reviewed": len(diagnostic),
            "diagnostic_by_relation": dict(sorted(by_relation.items())),
            "edge_precision_estimate": correct / len(benchmark) if complete else None,
            "wilson_95": wilson(correct, len(benchmark)) if complete else None,
            "note": "Overall precision requires a fully human-reviewed random benchmark. The balanced diagnostic sample cannot estimate overall precision. NER recall needs a separate article/span sample."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("export")
    create.add_argument("--er", type=Path, default=ER)
    create.add_argument("--out", type=Path, default=Path("reports/final_project/quality_sample.csv"))
    benchmark = sub.add_parser("export-benchmark")
    benchmark.add_argument("--snapshot", type=Path)
    benchmark.add_argument("--out", type=Path, default=Path("reports/final_project/benchmark_random.csv"))
    benchmark.add_argument("--size", type=int, default=200)
    benchmark.add_argument("--seed", type=int, default=20261120)
    score = sub.add_parser("evaluate")
    score.add_argument("sample", type=Path)
    args = parser.parse_args()
    if args.cmd == "export":
        result = export(args.er, args.out)
    elif args.cmd == "export-benchmark":
        result = export_benchmark(args.snapshot or snapshot_dir(), args.out, size=args.size, seed=args.seed)
    else:
        result = evaluate(args.sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
