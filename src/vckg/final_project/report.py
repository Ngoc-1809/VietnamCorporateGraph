"""Render the final-project academic report from the same immutable app snapshot."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

import markdown

from vckg.final_project.app import snapshot_dir
from vckg.final_project.build import ROOT

TEMPLATE = Path(__file__).with_name("report.md.in")
OUTPUT = ROOT / "reports/final_project"
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
CHROME = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")

CSS = """
@page{size:A4;margin:16mm 17mm 15mm}*{box-sizing:border-box}body{font:11pt/1.39 'Times New Roman',serif;color:#161616}
h1,h2,h3{font-family:Arial,sans-serif;line-height:1.22}h1{font-size:17pt;margin:0 0 6mm;letter-spacing:.01em}
h2{font-size:12.4pt;margin:5mm 0 2mm}p{margin:0 0 3mm;text-align:justify}ul,ol{margin:2mm 0 4mm;padding-left:7mm}
li{margin:1mm 0;text-align:justify}table{width:100%;border-collapse:collapse;font-size:9pt;margin:4mm 0}
th,td{border:1px solid #666;padding:1.8mm 2mm;vertical-align:top}th{background:#eee;text-align:left}
code{font:9pt Consolas,monospace;background:#f4f4f4;padding:0 1mm}a{color:#172e4b}.pagebreak{break-before:page;page-break-before:always;height:0}
.cover-logo{text-align:center;margin-top:11mm}.cover-logo img{height:36mm;width:36mm;object-fit:contain}
.cover-heading{text-align:center;font:700 13pt/1.6 Arial,sans-serif;margin:5mm 0 26mm}
.cover-heading+h1{text-align:center;font-size:20pt;margin:0 0 12mm}.cover-title{text-align:center;font:700 17pt/1.4 Arial,sans-serif;margin:0 4mm 23mm}
body>p:first-of-type{line-height:1.9}blockquote{margin:3mm 0;padding:2mm 4mm;background:#f4f4f4;border-left:2px solid #444}
"""


def vi_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def vi_float(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def render(snapshot: Path, output: Path = OUTPUT, *, pdf: bool = False) -> dict:
    meta = json.loads((snapshot / "metrics.json").read_text(encoding="utf-8"))
    analysis = meta["analysis"]
    with sqlite3.connect(snapshot / "profile.sqlite") as db:
        leaders = db.execute("SELECT name,entity_type,degree,pagerank FROM nodes ORDER BY pagerank DESC LIMIT 8").fetchall()
    top = "| Node | Loại | Bậc | PageRank |\n|---|---|---:|---:|\n"
    top += "\n".join(f"| {name.replace('|', ' ')} | {kind} | {vi_int(degree)} | {vi_float(rank, 6)} |"
                     for name, kind, degree, rank in leaders)
    status_excluded = sum(meta["excluded_nonofficial_evidence_rows"].get(reason, 0)
                          for reason in ("PLANNED", "ALLEGED", "UNKNOWN", "DENIED"))
    with sqlite3.connect(ROOT / "data/campaign/mass/queue.sqlite") as db:
        articles, done = db.execute("SELECT count(*) FROM urls WHERE parse_status='ok'").fetchone()[0], \
                         db.execute("SELECT count(*) FROM urls WHERE nlp_status='done'").fetchone()[0]
    variables = {
        "DATE": datetime.now().astimezone().strftime("%d/%m/%Y"), "SNAPSHOT": meta["snapshot_id"],
        "ARTICLES": vi_int(articles), "DONE": vi_int(done), "NODES": vi_int(meta["node_count"]),
        "EDGES": vi_int(meta["edge_count"]), "EVIDENCE": vi_int(meta["evidence_count"]),
        "REL_TYPES": meta["relation_types"], "EXCLUDED_ENDPOINT": meta["excluded_nonofficial_evidence_rows"].get("ENDPOINT_IDENTITY", 0),
        "EXCLUDED_STATUS": status_excluded, "PAIRS": vi_int(analysis["simple_undirected_pairs"]),
        "EXCLUDED_SCREENED": meta["excluded_nonofficial_evidence_rows"].get("AI_SCREENED_EVIDENCE_MISMATCH", 0),
        "COMPONENTS": f"{analysis['connected_components']:,}", "LCC": f"{analysis['largest_component']:,}",
        "LCC_SHARE": vi_float(100 * analysis["largest_component_share"], 1),
        "COMMUNITIES": vi_int(analysis["communities"]), "MAX_CORE": analysis["max_core"],
        "ASPL": vi_float(analysis["largest_component_average_shortest_path"], 3),
        "CLUSTER": vi_float(analysis["largest_component_clustering"], 4),
        "REACHABLE_ASPL": vi_float(analysis["reachable_pair_average_shortest_path"], 3),
        "TRIALS": analysis["random_trials"], "LAST_SEED": analysis["random_trials"] - 1,
        "RANDOM_CLUSTER": vi_float(analysis["random_baseline_clustering"], 4),
        "RANDOM_ASPL": vi_float(analysis["random_baseline_path_length"], 3),
        "SIGMA": vi_float(analysis["small_world_sigma_largest_component"], 3),
        "MODULARITY": vi_float(analysis["modularity"], 3), "TOP_TABLE": top,
    }
    source = TEMPLATE.read_text(encoding="utf-8")
    for key, value in variables.items():
        source = source.replace("{{" + key + "}}", str(value))
    if "{{" in source:
        raise ValueError("Unfilled report placeholder")
    body = markdown.markdown(source, extensions=["tables", "fenced_code"])
    output.mkdir(parents=True, exist_ok=True)
    html_path = output / "topic17_final_report.html"
    html_path.write_text("<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
                         f"<title>VCKG · Báo cáo cuối kỳ</title><style>{CSS}</style></head><body>{body}</body></html>",
                         encoding="utf-8")
    result = {"html": str(html_path), "snapshot": meta["snapshot_id"], "page_breaks": source.count('class="pagebreak"')}
    if pdf:
        browser = EDGE if EDGE.exists() else CHROME
        if not browser.exists():
            raise FileNotFoundError("Microsoft Edge or Chrome is required to print PDF")
        pdf_path = output / "topic17_final_report.pdf"
        subprocess.run([str(browser), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={ROOT / 'tmp/final-report-browser'}", f"--print-to-pdf={pdf_path}",
                        html_path.as_uri()], check=True, timeout=120, capture_output=True)
        if not pdf_path.exists() or pdf_path.stat().st_size < 10_000:
            raise RuntimeError("PDF print did not produce a valid-sized file")
        result["pdf"] = str(pdf_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=None)
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    print(json.dumps(render(args.snapshot or snapshot_dir(), pdf=args.pdf), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
