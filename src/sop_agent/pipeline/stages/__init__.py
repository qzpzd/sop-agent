"""Lazy imports in stage modules to avoid hard OpenCV DLL failures at import time."""

__all__ = [
    "asr",
    "export",
    "ingest",
    "keyframes",
    "retrieve",
    "sop_compose",
    "vl_analyze",
]


def __getattr__(name: str):
    if name in __all__:
        import importlib

        return importlib.import_module(f"sop_agent.pipeline.stages.{name}")
    raise AttributeError(name)
