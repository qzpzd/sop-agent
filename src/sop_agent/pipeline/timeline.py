"""Timeline helpers: align ASR segments with scenes."""

from __future__ import annotations

from typing import Any


def segments_in_range(
    segments: list[dict[str, Any]],
    start: float,
    end: float,
) -> list[dict[str, Any]]:
    return [s for s in segments if s.get("end", 0) >= start and s.get("start", 0) <= end]


def join_transcript(segments: list[dict[str, Any]]) -> str:
    return "".join(s.get("text", "") for s in segments).strip()
