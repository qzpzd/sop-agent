from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class JobRecord:
    job_id: str
    status: str
    video_path: str
    out_dir: str
    progress: float = 0.0
    stage: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JobStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @classmethod
    def default(cls) -> "JobStore":
        return cls(Path("storage/jobs.db"))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                  job_id TEXT PRIMARY KEY,
                  status TEXT NOT NULL,
                  video_path TEXT,
                  out_dir TEXT,
                  progress REAL DEFAULT 0,
                  stage TEXT DEFAULT '',
                  error TEXT DEFAULT '',
                  payload TEXT DEFAULT '{}'
                )
                """
            )

    def upsert(self, job: JobRecord, payload: Optional[dict[str, Any]] = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs(job_id, status, video_path, out_dir, progress, stage, error, payload)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(job_id) DO UPDATE SET
                  status=excluded.status,
                  progress=excluded.progress,
                  stage=excluded.stage,
                  error=excluded.error,
                  payload=excluded.payload
                """,
                (
                    job.job_id,
                    job.status,
                    job.video_path,
                    job.out_dir,
                    job.progress,
                    job.stage,
                    job.error,
                    json.dumps(payload or {}, ensure_ascii=False),
                ),
            )

    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            return dict(row) if row else None
