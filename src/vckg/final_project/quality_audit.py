"""Export a fixed stratified review sample; score only independently checked human labels."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from vckg.final_project.build import ER, EXCLUSIONS, _endpoints_ok, _official, _read

FIELDS = ["sample_group", "qa_tier", "edge_id", "relation_type", "subject_name", "subject_type", "object_name",
          "object_type", "factual_status", "quarantine_classes", "evidence_text", "source_url",
          "article_id", "published_at", "valid_relation", "valid_endpoints", "valid_evidence",
          "reviewer", "review_mode", "notes"]
TARGET = {"VALIDATED": 200, "QUARANTINE": 80, "EXCLUDED": 20}


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
            "method": "Deterministic round-robin by relation type; one evidence excerpt per edge; independent full-article review required."}


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
    reviewed = [row for row in rows if row["reviewer"].strip() and row["review_mode"] == "HUMAN_FULL_ARTICLE"
                and all(row[field] in {"YES", "NO"} for field in ("valid_relation", "valid_endpoints", "valid_evidence"))]
    passed = [row for row in reviewed if _group(row) == "VALIDATED"]
    correct = sum(all(row[field] == "YES" for field in ("valid_relation", "valid_endpoints", "valid_evidence")) for row in passed)
    return {"total_sampled": len(rows), "independently_human_reviewed": len(reviewed),
            "validated_reviewed": len(passed), "validated_correct": correct,
            "edge_precision_estimate": correct / len(passed) if passed else None,
            "wilson_95": wilson(correct, len(passed)) if passed else None,
            "note": "AI-assisted or excerpt-only labels never count as independent human gold. NER recall needs a separate article/span sample."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("export")
    create.add_argument("--er", type=Path, default=ER)
    create.add_argument("--out", type=Path, default=Path("reports/final_project/quality_sample.csv"))
    score = sub.add_parser("evaluate")
    score.add_argument("sample", type=Path)
    args = parser.parse_args()
    result = export(args.er, args.out) if args.cmd == "export" else evaluate(args.sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
