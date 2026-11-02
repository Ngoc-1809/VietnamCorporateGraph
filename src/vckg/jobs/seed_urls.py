"""Seed-URL job: fetch an explicit list of article URLs (politely, compliance-gated) into a SEPARATE staging DB and run the unchanged Phase 6C worker on them as one
independent job. Nothing touches the campaign queue, the master staging DB or the source registry (the job registry is a private copy of the cumulative registry).
  python -m vckg.jobs.seed_urls --job-id dagoras01 --source dagoras --urls data/dagoras/urls.txt [--source-note "..."]
Every article carries its source key; self-published pages (a company's own site) are flagged in the job metadata - they are claims by the subject, not independent press."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from vckg.crawlers.extract import ExtractionRejected, decode_response, extract_article
from vckg.crawlers.http import FetchError, PoliteClient, RobotsDisallowed, check_request_spacing
from vckg.crawlers.runner import load_sources
from vckg.jobs.pipeline_worker import PIPE_DIR, Worker, real_runtime
from vckg.jobs.selection import cleared_sources, load_compliance
from vckg.storage.sqlite import Staging

ROOT = Path(__file__).resolve().parents[3]


def run(job_id: str, source: str, urls: list[str], note: str, min_delay: float = 2.5, pipe_dir: Path = PIPE_DIR, registry: Path | None = None, max_qwen: int = 60) -> int:
    comp = load_compliance(ROOT / "config/crawl_compliance.yaml")
    if source not in cleared_sources(comp):
        raise SystemExit(f"source {source!r} is not cleared in config/crawl_compliance.yaml")
    d = pipe_dir / job_id
    d.mkdir(parents=True, exist_ok=True)
    staging_path = d / "staging.sqlite"
    st = Staging(staging_path)
    cfg = load_sources(ROOT / "config/sources.yaml")["crawler"]
    client = PoliteClient(cfg["user_agent"], max(float(cfg["min_delay_seconds"]), min_delay), 40.0, 2, cfg["backoff_base"], request_log=d / "http_requests.jsonl")
    manifest, report = [], []
    for u in urls:
        row = {"url": u, "status": None}
        try:
            r = client.get(u)
            ex = extract_article(decode_response(r.content, r.charset_encoding), u)
            status, art = st.add_article(u, source, ex.title, ex.text, ex.published_at, ex.parser, r.status_code)
            row.update(status=status, chars=len(ex.text), title=ex.title)
            if art is not None:
                manifest.append({"article_id": art.article_id, "url": u, "source": source, "subset": "seed"})
                row["article_id"] = art.article_id
        except RobotsDisallowed:
            row["status"] = "robots_disallowed"
        except FetchError as e:
            row["status"] = "fetch_error: " + str(e)[:100]
        except ExtractionRejected as e:
            row["status"] = "rejected: " + str(e)
        report.append(row)
    client.close()
    st.close()
    sp = check_request_spacing(d / "http_requests.jsonl", min_delay)
    (d / "seed_report.json").write_text(json.dumps({"source": source, "note": note, "self_published_source": "self-published" in note, "fetch": report, "http_spacing": {k: sp[k] for k in ("ok", "violations", "total_requests")}}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if not sp["ok"]:
        print("HTTP spacing violation: stopping before NLP", file=sys.stderr)
        return 6
    if not manifest:
        print("no article stored")
        return 4
    reg = registry or ROOT / "data/campaign/mass/registry_cumulative.sqlite"
    if not reg.exists():
        reg = ROOT / "data/registry/registry_p5_new.sqlite"
    (d / "manifest.jsonl").write_text("\n".join(json.dumps(m, ensure_ascii=False) for m in manifest), encoding="utf-8")
    shutil.copy(reg, d / "registry_source_copy.sqlite")  # the worker makes its own private copy from this file; the original is only read
    w = Worker(job_id, manifest, make_runtime=real_runtime, pipe_dir=pipe_dir, staging_db=staging_path, registry_source=d / "registry_source_copy.sqlite", max_articles=len(manifest),
               max_qwen_calls=max_qwen, batch_ceiling=max(len(manifest), 1), install_signals=False)
    return w.run()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="seed_urls")
    ap.add_argument("--job-id", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--urls", required=True)
    ap.add_argument("--source-note", default="")
    ap.add_argument("--max-qwen", type=int, default=60)
    a = ap.parse_args(argv)
    urls = [x.strip() for x in Path(a.urls).read_text(encoding="utf-8-sig").splitlines() if x.strip() and not x.startswith("#")]
    return run(a.job_id, a.source, urls, a.source_note, max_qwen=a.max_qwen)


if __name__ == "__main__":
    sys.exit(main())
