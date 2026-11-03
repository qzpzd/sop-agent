from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """语音转写：whisper_cpp 或 faster_whisper。"""
    cfg = ctx["config"].pipeline.asr
    work: Path = ctx["work_dir"]
    transcript_path = work / "transcript.json"
    backend = (cfg.backend or "faster_whisper").lower()

    if backend in ("faster_whisper", "faster-whisper"):
        from sop_agent.adapters import faster_whisper_asr

        segments = faster_whisper_asr.transcribe(
            audio=ctx["audio_path"],
            model_size=cfg.model_size,
            language=cfg.language,
            device=cfg.device,
            compute_type=cfg.compute_type,
        )
    elif backend in ("whisper_cpp", "whisper.cpp"):
        from sop_agent.adapters import whisper_cpp

        segments = whisper_cpp.transcribe(
            audio=ctx["audio_path"],
            model_path=cfg.model_path,
            language=cfg.language,
            threads=cfg.threads,
            out_json=transcript_path,
        )
    else:
        raise ValueError(f"不支持的 ASR backend: {backend}")

    ctx["transcript_path"] = transcript_path
    ctx["segments"] = segments
    transcript_path.write_text(
        json.dumps({"segments": segments, "backend": backend}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ctx
