from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from sop_agent.core.config import AppConfig


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class JobResult:
    job_id: str
    status: JobStatus
    out_dir: Path
    error: Optional[str] = None
    artifacts: dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    """阶段编排：ingest → asr → keyframes → vl → compose → export。"""

    STAGES = ("ingest", "asr", "keyframes", "vl_analyze", "sop_compose", "export")

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.log = logging.getLogger("sop_agent.orchestrator")

    @classmethod
    def from_config(cls, path: Path | str) -> "Orchestrator":
        return cls(AppConfig.load(path))

    def run(
        self,
        video: Path,
        out_dir: Path,
        topic_hint: Optional[str] = None,
        job_id: Optional[str] = None,
        phases: Optional[tuple[str, ...]] = None,
    ) -> JobResult:
        """phases 默认全流程；Phase0 可传 ("ingest","asr","keyframes")。"""
        job_id = job_id or uuid.uuid4().hex[:12]
        out_dir.mkdir(parents=True, exist_ok=True)
        selected = phases or ("ingest", "asr", "keyframes", "vl_analyze", "sop_compose", "export")
        ctx: dict[str, Any] = {
            "job_id": job_id,
            "video": video,
            "out_dir": out_dir,
            "topic_hint": topic_hint or "",
            "config": self.config,
        }

        try:
            from sop_agent.pipeline.stages import (
                asr,
                export,
                ingest,
                keyframes,
                sop_compose,
                vl_analyze,
            )

            if "ingest" in selected:
                ctx = ingest.run(ctx)
            if "asr" in selected:
                ctx = asr.run(ctx)
            if "keyframes" in selected:
                ctx = keyframes.run(ctx)
            if "vl_analyze" in selected and self.config.pipeline.vl.enabled:
                ctx = vl_analyze.run(ctx)
            if "sop_compose" in selected:
                ctx = sop_compose.run(ctx)
            if "export" in selected:
                ctx = export.run(ctx)
            return JobResult(job_id=job_id, status=JobStatus.DONE, out_dir=out_dir, artifacts=ctx)
        except Exception as exc:  # noqa: BLE001 — 顶层任务边界
            self.log.exception("job failed: %s", job_id)
            return JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                out_dir=out_dir,
                error=str(exc),
            )
