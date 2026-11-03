from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sop_agent.adapters import vlm_client
from sop_agent.pipeline.timeline import join_transcript, segments_in_range


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """多模态关键帧分析。"""
    cfg = ctx["config"].pipeline.vl
    work: Path = ctx["work_dir"]
    scenes = ctx.get("scenes") or []
    segments = ctx.get("segments") or []
    if len(scenes) > cfg.max_scenes:
        step = max(1, len(scenes) // cfg.max_scenes)
        scenes = scenes[::step][: cfg.max_scenes]

    analyses = []
    client = vlm_client.VlmClient(cfg)
    for scene in scenes:
        start, end = scene["start"], scene["end"]
        transcript = join_transcript(segments_in_range(segments, start, end))
        result = client.analyze_scene(
            scene_id=scene["id"],
            image_path=scene["keyframe"],
            start=start,
            end=end,
            transcript=transcript,
        )
        analyses.append(result)

    path = work / "vl_analyses.json"
    path.write_text(json.dumps(analyses, ensure_ascii=False, indent=2), encoding="utf-8")
    ctx["vl_analyses"] = analyses
    ctx["vl_analyses_path"] = path
    return ctx
