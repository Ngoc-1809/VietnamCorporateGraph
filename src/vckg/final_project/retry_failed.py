"""Back up the campaign queue and requeue only NLP articles with Qwen window failures."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "data/campaign/mass"


def requeue(campaign_dir: Path = CAMPAIGN, *, execute: bool = False) -> dict:
    path = campaign_dir / "queue.sqlite"
    if not path.exists():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute("""
            SELECT article_id,url,nlp_error FROM urls
            WHERE nlp_status='failed' AND nlp_error LIKE 'LLMCallFailed:%'
            ORDER BY article_id
        """).fetchall()
        result = {"found": len(rows), "execute": execute, "campaign_dir": str(campaign_dir)}
        if not execute or not rows:
            return result
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        backup_dir = campaign_dir / "retry_backups" / stamp
        backup_dir.mkdir(parents=True, exist_ok=False)
        backup = backup_dir / "queue.sqlite"
        with sqlite3.connect(backup) as destination:
            connection.backup(destination)
        digest = hashlib.sha256(backup.read_bytes()).hexdigest()
        (backup_dir / "articles.json").write_text(
            json.dumps([{"article_id": article_id, "url": url, "error": error} for article_id, url, error in rows],
                       ensure_ascii=False, indent=2), encoding="utf-8")
        with connection:
            changed = connection.execute("""
                UPDATE urls SET nlp_status='pending',chunk_id=NULL,nlp_error=NULL
                WHERE nlp_status='failed' AND nlp_error LIKE 'LLMCallFailed:%'
            """).rowcount
        if changed != len(rows):
            raise RuntimeError(f"Queue changed concurrently: selected={len(rows)}, updated={changed}")
        result.update({"requeued": changed, "backup": str(backup), "backup_sha256": digest})
        return result
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, default=CAMPAIGN)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(requeue(args.campaign_dir, execute=args.execute), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
