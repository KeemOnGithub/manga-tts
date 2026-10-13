from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings


_lock = threading.RLock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _lock, connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, source_name TEXT NOT NULL,
            page_count INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'uploaded',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS passages (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL, page INTEGER NOT NULL, source_text TEXT NOT NULL,
            text TEXT NOT NULL, speaker_id TEXT, confidence REAL, status TEXT NOT NULL DEFAULT 'extracted',
            UNIQUE(project_id, ordinal)
        );
        CREATE TABLE IF NOT EXISTS speakers (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name TEXT NOT NULL, voice_prompt TEXT NOT NULL DEFAULT '', voice_id TEXT,
            preview_path TEXT, is_narrator INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            kind TEXT NOT NULL, status TEXT NOT NULL, stage TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0,
            error TEXT, result TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audio_segments (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            passage_id TEXT NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
            path TEXT NOT NULL, duration REAL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            pdf_path TEXT NOT NULL, mp3_path TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_passages_project_order ON passages(project_id, ordinal);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at);
        """)


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def new_id() -> str:
    return str(uuid.uuid4())


def create_job(project_id: str, kind: str) -> str:
    job_id = new_id()
    timestamp = now()
    with _lock, connect() as db:
        db.execute("INSERT INTO jobs(id,project_id,kind,status,stage,created_at,updated_at) VALUES(?,?,?,'queued','Queued',?,?)",
                   (job_id, project_id, kind, timestamp, timestamp))
    return job_id


def update_job(job_id: str, *, status: str | None = None, stage: str | None = None,
               progress: float | None = None, error: str | None = None, result: Any = None) -> None:
    fields: list[str] = ["updated_at = ?"]
    values: list[Any] = [now()]
    for key, value in (("status", status), ("stage", stage), ("progress", progress), ("error", error)):
        if value is not None:
            fields.append(f"{key} = ?")
            values.append(value)
    if result is not None:
        fields.append("result = ?")
        values.append(json.dumps(result))
    values.append(job_id)
    with _lock, connect() as db:
        db.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)


def project_exists(project_id: str) -> bool:
    with connect() as db:
        return db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone() is not None


def get_job(job_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    item = row_dict(row)
    if item and item.get("result"):
        item["result"] = json.loads(item["result"])
    return item


def claim_queued_job() -> dict[str, Any] | None:
    with _lock, connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if row is None:
            db.commit()
            return None
        db.execute("UPDATE jobs SET status='running',stage='Starting',updated_at=? WHERE id=?", (now(), row["id"]))
        db.commit()
        return dict(row)


def recover_interrupted_jobs() -> None:
    with _lock, connect() as db:
        db.execute("UPDATE jobs SET status='queued',stage='Resuming after restart',updated_at=? WHERE status='running'", (now(),))
