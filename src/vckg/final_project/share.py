"""Export and install the exact SQLite snapshot used by the local graph website."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

from vckg.final_project.build import OUT

DATABASES = ("profile.sqlite", "quarantine.sqlite")
METADATA = ("metrics.json", "quarantine_metrics.json", "modes.json")
REQUIRED = (*DATABASES, *METADATA)
MANIFEST_VERSION = 1


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _counts(path: Path) -> dict[str, int]:
    with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError(f"SQLite integrity_check failed: {path}")
        return {table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("nodes", "edges", "evidence")}


def _validate_snapshot(folder: Path) -> dict[str, dict[str, int]]:
    missing = [name for name in REQUIRED if not (folder / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Snapshot is incomplete: {', '.join(missing)}")
    counts = {name: _counts(folder / name) for name in DATABASES}
    for name, database in (("metrics.json", "profile.sqlite"),
                           ("quarantine_metrics.json", "quarantine.sqlite")):
        metrics = json.loads((folder / name).read_text(encoding="utf-8-sig"))
        for label, key in (("node_count", "nodes"), ("edge_count", "edges"),
                           ("evidence_count", "evidence")):
            if label in metrics and metrics[label] != counts[database][key]:
                raise ValueError(f"{name}: {label} does not match {database}")
    json.loads((folder / "modes.json").read_text(encoding="utf-8-sig"))
    return counts


def export_snapshot(snapshot: Path, archive: Path) -> dict:
    """Make consistent read-only SQLite backup copies, then archive the copies."""
    snapshot = snapshot.resolve()
    _validate_snapshot(snapshot)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vckg-share-", dir=archive.parent) as scratch:
        staging = Path(scratch)
        for name in DATABASES:
            source = snapshot / name
            with closing(sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)) as src, \
                    closing(sqlite3.connect(staging / name)) as dst:
                src.backup(dst)
        for name in METADATA:
            shutil.copy2(snapshot / name, staging / name)
        counts = _validate_snapshot(staging)
        manifest = {"format": "vckg-final-project-sqlite", "version": MANIFEST_VERSION,
                    "source_snapshot": snapshot.name, "counts": counts,
                    "files": {name: {"sha256": _digest(staging / name),
                                     "bytes": (staging / name).stat().st_size} for name in REQUIRED}}
        temporary_zip = staging / "archive.zip"
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                             allowZip64=True) as bundle:
            bundle.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for name in REQUIRED:
                bundle.write(staging / name, f"snapshot/{name}")
        with zipfile.ZipFile(temporary_zip) as bundle:
            if bundle.testzip() is not None:
                raise ValueError("Archive failed ZIP checksum verification")
        os.replace(temporary_zip, archive)
    return {**manifest, "archive": str(archive), "archive_sha256": _digest(archive),
            "archive_bytes": archive.stat().st_size}


def install_snapshot(archive: Path, output_root: Path = OUT) -> dict:
    """Verify archive paths and content before selecting the installed snapshot."""
    output_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        expected_paths = {"manifest.json", *(f"snapshot/{name}" for name in REQUIRED)}
        if set(bundle.namelist()) != expected_paths:
            raise ValueError("Archive has missing or unexpected paths")
        manifest = json.loads(bundle.read("manifest.json"))
        if (manifest.get("format"), manifest.get("version")) != ("vckg-final-project-sqlite", MANIFEST_VERSION):
            raise ValueError("Unsupported VCKG snapshot archive")
        if set(manifest.get("files", {})) != set(REQUIRED):
            raise ValueError("Manifest does not match required files")
        source_name = manifest.get("source_snapshot", "")
        if not source_name or Path(source_name).name != source_name or any(c in source_name for c in "\\/:"):
            raise ValueError("Invalid snapshot name")
        target = output_root / f"shared-{source_name}"
        if target.exists():
            for name, details in manifest["files"].items():
                if not (target / name).is_file() or _digest(target / name) != details["sha256"]:
                    raise FileExistsError(f"Existing snapshot differs: {target}")
            counts = _validate_snapshot(target)
        else:
            with tempfile.TemporaryDirectory(prefix="vckg-import-", dir=output_root) as scratch:
                staging = Path(scratch) / "snapshot"
                staging.mkdir()
                for name, details in manifest["files"].items():
                    with bundle.open(f"snapshot/{name}") as source, (staging / name).open("wb") as dest:
                        shutil.copyfileobj(source, dest)
                    if _digest(staging / name) != details["sha256"]:
                        raise ValueError(f"SHA-256 mismatch: {name}")
                    if (staging / name).stat().st_size != details["bytes"]:
                        raise ValueError(f"Size mismatch: {name}")
                counts = _validate_snapshot(staging)
                if counts != manifest["counts"]:
                    raise ValueError("Database row counts do not match manifest")
                staging.rename(target)
    active = output_root / "ACTIVE.txt"
    pending = output_root / "ACTIVE.txt.tmp"
    pending.write_text(str(target.resolve()), encoding="utf-8")
    os.replace(pending, active)
    return {"snapshot": str(target), "counts": counts, "active": str(active)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    export = subparsers.add_parser("export")
    export.add_argument("archive", type=Path)
    export.add_argument("--snapshot", type=Path)
    install = subparsers.add_parser("install")
    install.add_argument("archive", type=Path)
    install.add_argument("--output-root", type=Path, default=OUT)
    args = parser.parse_args()
    if args.action == "export":
        from vckg.final_project.app import snapshot_dir

        result = export_snapshot(args.snapshot or snapshot_dir(), args.archive)
    else:
        result = install_snapshot(args.archive, args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
