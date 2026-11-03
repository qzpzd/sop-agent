from __future__ import annotations

from pathlib import Path

from sop_agent.core.schemas_sop import SopDocument


def write(sop: SopDocument, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sop.model_dump_json(indent=2), encoding="utf-8")
