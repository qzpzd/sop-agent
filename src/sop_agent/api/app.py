from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from sop_agent.core.config import AppConfig
from sop_agent.db.jobs import JobRecord, JobStore
from sop_agent.pipeline.orchestrator import JobStatus, Orchestrator

app = FastAPI(title="SOP Agent", version="0.1.0")
_config = AppConfig.load(Path("configs/default.yaml"))
_store = JobStore(Path(_config.storage.sqlite_path))


def _run_job(job_id: str, video: Path, out_dir: Path) -> None:
    _store.upsert(
        JobRecord(
            job_id=job_id,
            status=JobStatus.RUNNING.value,
            video_path=str(video),
            out_dir=str(out_dir),
            progress=0.05,
            stage="ingest",
        )
    )
    orch = Orchestrator(_config)
    result = orch.run(video=video, out_dir=out_dir, job_id=job_id)
    _store.upsert(
        JobRecord(
            job_id=job_id,
            status=result.status.value,
            video_path=str(video),
            out_dir=str(out_dir),
            progress=1.0 if result.status == JobStatus.DONE else 0.0,
            stage="done" if result.status == JobStatus.DONE else "failed",
            error=result.error or "",
        )
    )


@app.post("/api/v1/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> JSONResponse:
    job_id = uuid.uuid4().hex[:12]
    out_dir = Path(_config.storage.root) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / (file.filename or "input.mp4")
    video_path.write_bytes(await file.read())
    _store.upsert(
        JobRecord(
            job_id=job_id,
            status=JobStatus.PENDING.value,
            video_path=str(video_path),
            out_dir=str(out_dir),
        )
    )
    background_tasks.add_task(_run_job, job_id, video_path, out_dir)
    return JSONResponse({"job_id": job_id, "status": JobStatus.PENDING.value})


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str) -> JSONResponse:
    row = _store.get(job_id)
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(row)


@app.get("/api/v1/jobs/{job_id}/sop")
def get_sop(job_id: str, fmt: str = "json") -> FileResponse | JSONResponse:
    row = _store.get(job_id)
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    out_dir = Path(row["out_dir"])
    path = out_dir / ("SOP.md" if fmt == "markdown" else "SOP.json")
    if not path.exists():
        return JSONResponse({"error": "sop not ready"}, status_code=404)
    return FileResponse(path)
