from __future__ import annotations

from pathlib import Path
from typing import Optional

from sop_agent.core.schemas_sop import SopDocument


def write(sop: SopDocument, path: Path, assets_dir: Optional[Path] = None) -> None:
    lines: list[str] = [
        f"# {sop.title}",
        "",
        sop.summary,
        "",
    ]
    if sop.prerequisites:
        lines.append("## 前置条件")
        lines.extend(f"- {p}" for p in sop.prerequisites)
        lines.append("")
    lines.append("## 操作步骤")
    lines.append("")
    for step in sop.steps:
        lines.append(f"### {step.index}. {step.title}")
        lines.append("")
        lines.append(step.instruction)
        lines.append("")
        if step.expected_result:
            lines.append(f"**预期结果：** {step.expected_result}")
            lines.append("")
        if step.keyframe:
            # Markdown 相对路径：尽量指向任务目录内资源
            lines.append(f"![step-{step.index}]({step.keyframe})")
            lines.append("")
        if step.transcript_quote:
            lines.append(f"> 旁白：{step.transcript_quote}")
            lines.append("")
        if step.notes:
            lines.extend(f"- 注意：{n}" for n in step.notes)
            lines.append("")
        lines.append(f"*时间戳：{step.timestamp_start:.1f}s – {step.timestamp_end:.1f}s*")
        lines.append("")
    if sop.warnings:
        lines.append("## 风险提示")
        lines.extend(f"- {w}" for w in sop.warnings)
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
