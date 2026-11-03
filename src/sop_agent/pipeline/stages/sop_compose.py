from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sop_agent.adapters import llm_client
from sop_agent.core.schemas_sop import SopDocument, SopStep
from sop_agent.pipeline.timeline import join_transcript, segments_in_range


def _build_timeline(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """画面镜头为主；若无镜头则退化为按 ASR 分段。"""
    scenes = ctx.get("scenes") or []
    segments = ctx.get("segments") or []
    analyses = {a.get("scene_id"): a for a in (ctx.get("vl_analyses") or [])}

    if not scenes and segments:
        return [
            {
                "scene_id": i,
                "start": float(s.get("start", 0)),
                "end": float(s.get("end", 0)),
                "keyframe": None,
                "transcript": (s.get("text") or "").strip(),
                "vision": None,
            }
            for i, s in enumerate(segments)
        ]

    timeline = []
    for scene in scenes:
        sid = scene["id"]
        quote = join_transcript(segments_in_range(segments, scene["start"], scene["end"]))
        timeline.append(
            {
                "scene_id": sid,
                "start": scene["start"],
                "end": scene["end"],
                "keyframe": scene.get("keyframe"),
                "transcript": quote,
                "vision": analyses.get(sid),
            }
        )
    return timeline


def _heuristic_sop(timeline: list[dict[str, Any]], topic_hint: str) -> SopDocument:
    """Ollama 不可用时的兜底：按时间线直接落成粗 SOP。"""
    steps: list[SopStep] = []
    for i, item in enumerate(timeline, start=1):
        text = (item.get("transcript") or "").strip() or f"查看关键画面（镜头 {item.get('scene_id')}）"
        steps.append(
            SopStep(
                index=i,
                title=f"步骤 {i}",
                instruction=text,
                expected_result="待人工确认",
                notes=["由启发式规则生成，建议人工修订"],
                timestamp_start=float(item.get("start") or 0),
                timestamp_end=float(item.get("end") or 0),
                keyframe=item.get("keyframe"),
                transcript_quote=text,
            )
        )
    title = topic_hint.strip() if topic_hint.strip() else "未命名操作 SOP"
    return SopDocument(
        title=title,
        summary="根据视频旁白与关键帧自动生成的草稿 SOP（启发式）。",
        prerequisites=[],
        steps=steps,
        warnings=["LLM 未参与或失败，本结果为启发式草稿"],
    )


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """LLM 整理为规范 SOP；失败则启发式兜底。"""
    cfg = ctx["config"].pipeline.llm
    work: Path = ctx["work_dir"]
    timeline = _build_timeline(ctx)
    (work / "timeline.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        client = llm_client.LlmClient(cfg)
        sop = client.compose_sop(timeline=timeline, topic_hint=ctx.get("topic_hint") or "")
        doc = SopDocument.model_validate(sop)
        # 若模型漏了 keyframe，按时间线回填
        for step in doc.steps:
            if not step.keyframe and 0 < step.index <= len(timeline):
                step.keyframe = timeline[step.index - 1].get("keyframe")
    except Exception as exc:  # noqa: BLE001
        doc = _heuristic_sop(timeline, ctx.get("topic_hint") or "")
        doc.warnings.append(f"LLM 失败回退: {exc}")

    sop_path = work / "sop.json"
    sop_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    ctx["sop"] = doc
    ctx["sop_path"] = sop_path
    return ctx
