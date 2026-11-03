"""Resume Phase1 compose+export from an existing Phase0 work dir."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sop_agent.core.config import AppConfig
from sop_agent.pipeline.stages import export, sop_compose


def main() -> int:
    out = ROOT / "storage" / "jobs" / "win_20260622"
    work = out / "work"
    cfg = AppConfig.load(ROOT / "configs" / "default.yaml")
    ctx = {
        "out_dir": out,
        "work_dir": work,
        "topic_hint": "Windows 操作录屏 SOP",
        "config": cfg,
        "segments": json.loads((work / "transcript.json").read_text(encoding="utf-8")).get(
            "segments", []
        ),
        "scenes": json.loads((work / "scenes.json").read_text(encoding="utf-8")).get("scenes", []),
        "keyframes_dir": work / "keyframes",
    }
    ctx = sop_compose.run(ctx)
    ctx = export.run(ctx)
    sop = ctx["sop"]
    print("title=", sop.title)
    print("steps=", len(sop.steps))
    print("warnings=", sop.warnings)
    print("SOP.md=", out / "SOP.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
