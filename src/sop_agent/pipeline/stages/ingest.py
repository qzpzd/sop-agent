from __future__ import annotations

from pathlib import Path
from typing import Any

from sop_agent.adapters import ffmpeg as ffmpeg_adapter


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """规范化视频并抽取音频。"""
    out_dir: Path = ctx["out_dir"]
    video: Path = ctx["video"]
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)

    source = work / "source.mp4"
    audio = work / "audio.wav"
    meta = ffmpeg_adapter.normalize_and_extract(video, source, audio)
    ctx["work_dir"] = work
    ctx["source_video"] = source
    ctx["audio_path"] = audio
    ctx["media_meta"] = meta
    return ctx
