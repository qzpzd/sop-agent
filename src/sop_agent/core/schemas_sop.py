from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator


def _as_str_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)]


class SopStep(BaseModel):
    index: int
    title: str
    instruction: str
    expected_result: str = ""
    notes: list[str] = Field(default_factory=list)
    timestamp_start: float = 0.0
    timestamp_end: float = 0.0
    keyframe: Optional[str] = None
    transcript_quote: str = ""

    @field_validator("notes", mode="before")
    @classmethod
    def coerce_notes(cls, v: Any) -> list[str]:
        return _as_str_list(v)

    @field_validator("expected_result", "title", "instruction", "transcript_quote", mode="before")
    @classmethod
    def coerce_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class SopDocument(BaseModel):
    title: str
    summary: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    steps: list[SopStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("prerequisites", "warnings", mode="before")
    @classmethod
    def coerce_lists(cls, v: Any) -> list[str]:
        return _as_str_list(v)

    @field_validator("title", "summary", mode="before")
    @classmethod
    def coerce_title(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)
