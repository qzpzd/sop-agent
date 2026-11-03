from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sop_agent.adapters import keyframes as keyframes_adapter


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """关键帧抽取（OpenCV 或 FFmpeg 回退）。"""
    cfg = ctx["config"].pipeline.keyframes
    work: Path = ctx["work_dir"]
    kf_dir = work / "keyframes"
    scenes = keyframes_adapter.extract_keyframes(
        video=ctx["source_video"],
        out_dir=kf_dir,
        hist_threshold=cfg.hist_threshold,
        min_scene_len_sec=cfg.min_scene_len_sec,
        max_frames_per_min=cfg.max_frames_per_min,
        fallback_interval_sec=cfg.fallback_interval_sec,
    )
    scenes_path = work / "scenes.json"
    scenes_path.write_text(
        json.dumps({"scenes": scenes}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ctx["keyframes_dir"] = kf_dir
    ctx["scenes"] = scenes
    ctx["scenes_path"] = scenes_path
    return ctx
