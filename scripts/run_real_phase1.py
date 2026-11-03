"""Run Phase0+1 on a real sample video."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sop_agent.pipeline.orchestrator import JobStatus, Orchestrator


def main() -> int:
    video = ROOT / "data" / "samples" / "WIN_20260622_14_40_12_Pro.mp4"
    if not video.exists():
        print("missing:", video)
        return 1
    out = ROOT / "storage" / "jobs" / "win_20260622"
    orch = Orchestrator.from_config(ROOT / "configs" / "default.yaml")
    print("running Phase0+1 →", out)
    job = orch.run(
        video=video,
        out_dir=out,
        topic_hint="Windows 操作录屏 SOP",
        phases=("ingest", "asr", "keyframes", "sop_compose", "export"),
    )
    print("status=", job.status, "job_id=", job.job_id)
    if job.error:
        print("error:", job.error)
    arts = job.artifacts or {}
    print("segments=", len(arts.get("segments") or []))
    print("scenes=", len(arts.get("scenes") or []))
    sop = arts.get("sop")
    if sop is not None:
        print("sop_title=", getattr(sop, "title", None))
        print("sop_steps=", len(getattr(sop, "steps", []) or []))
    print("out=", out)
    print("SOP.json=", out / "SOP.json")
    print("SOP.md=", out / "SOP.md")
    return 0 if job.status == JobStatus.DONE else 1


if __name__ == "__main__":
    raise SystemExit(main())
