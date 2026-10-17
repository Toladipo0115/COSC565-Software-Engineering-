"""US-01: transactional, reproducible CSV staging (no detection or aggregation)."""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {
    "courses.csv": ("code_module", "code_presentation", "module_presentation_length"),
    "studentRegistration.csv": (
        "code_module", "code_presentation", "id_student", "date_registration", "date_unregistration"
    ),
    "studentVle.csv": ("code_module", "code_presentation", "id_student", "date", "sum_click"),
}
POLICY = "csv-staging-v1"
SCHEMA = """
CREATE TABLE IF NOT EXISTS dataset_versions (
    dataset_version_id TEXT PRIMARY KEY,
    imported_at TEXT NOT NULL,
    source_name TEXT NOT NULL,
    preprocessing_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'STAGED')
);
CREATE TABLE IF NOT EXISTS source_files (
    dataset_version_id TEXT NOT NULL REFERENCES dataset_versions(dataset_version_id),
    filename TEXT NOT NULL,
    checksum TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    staged_rows INTEGER NOT NULL,
    PRIMARY KEY (dataset_version_id, filename)
);
CREATE TABLE IF NOT EXISTS source_records (
    dataset_version_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    record_number INTEGER NOT NULL,
    fields_json TEXT NOT NULL,
    PRIMARY KEY (dataset_version_id, filename, record_number),
    FOREIGN KEY (dataset_version_id, filename)
        REFERENCES source_files(dataset_version_id, filename)
);
"""


class ImportErrorDetail(ValueError):
    """An actionable input failure, safe to display without a traceback."""


def _snapshot(path: Path, destination: Path, max_bytes: int) -> tuple[str, int]:
    """Hash the exact bytes later parsed, even if the input changes during import."""
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as src, destination.open("wb") as target:
        while chunk := src.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                raise ImportErrorDetail(f"{path.name}: exceeds the configured {max_bytes} byte limit")
            digest.update(chunk)
            target.write(chunk)
    return digest.hexdigest(), size


def import_dataset(input_dir: str | Path, database: str | Path, *, max_file_mb: int = 100) -> dict:
    """Stage three required OULAD files atomically and return a JSON-ready summary.

    Only required fields are retained. Row values remain strings for US-02 validation.
    A content-identical import returns the existing version without duplicating rows.
    """
    if isinstance(max_file_mb, bool) or not isinstance(max_file_mb, int) or max_file_mb <= 0:
        raise ImportErrorDetail("max_file_mb must be a positive integer")
    input_dir, database = Path(input_dir), Path(database)
    for name in REQUIRED:
        if not (input_dir / name).is_file():
            raise ImportErrorDetail(f"Missing required CSV file: {name}")
    try:
        with tempfile.TemporaryDirectory(prefix="engagetrace-import-") as temporary:
            snapshots = Path(temporary)
            manifest = {}
            for name in REQUIRED:
                checksum, size = _snapshot(input_dir / name, snapshots / name, max_file_mb * 1024 * 1024)
                manifest[name] = {"checksum": checksum, "size_bytes": size}
                with (snapshots / name).open(encoding="utf-8-sig", newline="") as stream:
                    header = next(csv.reader(stream, strict=True), None)
                if header is None:
                    raise ImportErrorDetail(f"{name}: empty file; required header is missing")
                if len(header) != len(set(header)) or any(not col for col in header):
                    raise ImportErrorDetail(f"{name}: duplicate or blank column names")
                missing = sorted(set(REQUIRED[name]) - set(header))
                if missing:
                    raise ImportErrorDetail(f"{name}: missing required columns: {', '.join(missing)}")
            identity = {"policy": POLICY, "files": manifest}
            version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            database.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(database)
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.executescript(SCHEMA)
                with connection:
                    # Serialize duplicate checks and writes across concurrent imports.
                    connection.execute("BEGIN IMMEDIATE")
                    exists = connection.execute(
                        "SELECT 1 FROM dataset_versions WHERE dataset_version_id = ?", (version,)
                    ).fetchone()
                    if not exists:
                        connection.execute(
                            "INSERT INTO dataset_versions VALUES (?, ?, ?, ?, 'STAGED')",
                            (version, datetime.now(timezone.utc).isoformat(), "OULAD", POLICY),
                        )
                        for name, columns in REQUIRED.items():
                            item = manifest[name]
                            connection.execute(
                                "INSERT INTO source_files VALUES (?, ?, ?, ?, 0)",
                                (version, name, item["checksum"], item["size_bytes"]),
                            )
                            count = 0
                            with (snapshots / name).open(encoding="utf-8-sig", newline="") as stream:
                                reader = csv.DictReader(stream, strict=True)
                                for row in reader:
                                    if None in row or any(value is None for value in row.values()):
                                        raise ImportErrorDetail(f"{name}: malformed record ending at line {reader.line_num}")
                                    count += 1
                                    connection.execute(
                                        "INSERT INTO source_records VALUES (?, ?, ?, ?)",
                                        (version, name, count, json.dumps({key: row[key] for key in columns})),
                                    )
                            if not count:
                                raise ImportErrorDetail(f"{name}: no data records")
                            connection.execute(
                                "UPDATE source_files SET staged_rows = ? WHERE dataset_version_id = ? AND filename = ?",
                                (count, version, name),
                            )
                    sources = connection.execute(
                        "SELECT filename, checksum, size_bytes, staged_rows FROM source_files "
                        "WHERE dataset_version_id = ? ORDER BY filename", (version,)
                    ).fetchall()
                    imported_at = connection.execute(
                        "SELECT imported_at FROM dataset_versions WHERE dataset_version_id = ?", (version,)
                    ).fetchone()[0]
                return {
                    "dataset_version_id": version, "status": "STAGED", "source_name": "OULAD",
                    "preprocessing_version": POLICY, "imported_at": imported_at,
                    "already_imported": bool(exists),
                    "files": [dict(zip(("filename", "checksum", "size_bytes", "staged_rows"), row)) for row in sources],
                    "total_staged_rows": sum(row[3] for row in sources),
                }
            finally:
                connection.close()
    except (OSError, UnicodeError, csv.Error, sqlite3.Error) as exc:
        raise ImportErrorDetail(f"Import failed; no partial dataset was saved: {exc}") from exc
