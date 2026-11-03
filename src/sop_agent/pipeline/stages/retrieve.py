"""Optional FAISS retrieval stage (Phase 3)."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    cfg = ctx["config"].pipeline.retrieval
    if not cfg.enabled:
        return ctx
    # TODO: Phase 3 — embed steps / keyframes and query FAISS
    return ctx
