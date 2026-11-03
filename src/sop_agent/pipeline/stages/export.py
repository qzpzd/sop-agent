from __future__ import annotations

from pathlib import Path
from typing import Any

from sop_agent.exporters import json_export, markdown


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """导出 SOP 与资源。"""
    out_dir: Path = ctx["out_dir"]
    formats = ctx["config"].export.formats
    sop = ctx["sop"]
    if "json" in formats:
        json_export.write(sop, out_dir / "SOP.json")
    if "markdown" in formats:
        markdown.write(sop, out_dir / "SOP.md", assets_dir=ctx.get("keyframes_dir"))
    return ctx
