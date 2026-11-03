"""FAISS store placeholder for Phase 3."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class FaissStore:
    def __init__(self, index_dir: str | Path) -> None:
        self.index_dir = Path(index_dir)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError("FAISS 检索将在 Phase 3 实现")
