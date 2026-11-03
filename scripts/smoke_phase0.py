"""Phase0 smoke: ingest + asr + keyframes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sop_agent.pipeline.orchestrator import JobStatus, Orchestrator


def main() -> int:
    video = ROOT / "data" / "samples" / "demo_phase0.mp4"
    if not video.exists():
        print(f"缺少样例视频: {video}")
        print("请先运行: powershell -File scripts/make_sample_video.ps1")
        return 1

    out = ROOT / "storage" / "jobs" / "phase0_smoke"
    orch = Orchestrator.from_config(ROOT / "configs" / "default.yaml")
    job = orch.run(video=video, out_dir=out, phases=("ingest", "asr", "keyframes"))
    print(f"status={job.status} job_id={job.job_id}")
    if job.error:
        print("error:", job.error)
        return 1

    arts = job.artifacts
    print("audio:", arts.get("audio_path"))
    print("segments:", len(arts.get("segments") or []))
    print("scenes:", len(arts.get("scenes") or []))
    print("transcript:", arts.get("transcript_path"))
    print("scenes_json:", arts.get("scenes_path"))
    print("out:", out)
    return 0 if job.status == JobStatus.DONE else 1


if __name__ == "__main__":
    raise SystemExit(main())
