from __future__ import annotations

from pathlib import Path
from typing import Any


def transcribe(
    audio: Path,
    model_size: str = "base",
    language: str = "zh",
    device: str = "cpu",
    compute_type: str = "int8",
) -> list[dict[str, Any]]:
    """CPU 友好的 faster-whisper 转写（档位 C / Windows 默认）。"""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "未安装 faster-whisper。请执行: pip install faster-whisper"
        ) from exc

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments_iter, _info = model.transcribe(
        str(audio),
        language=language if language and language != "auto" else None,
        vad_filter=True,
    )
    segments: list[dict[str, Any]] = []
    for s in segments_iter:
        text = (s.text or "").strip()
        if not text:
            continue
        segments.append(
            {
                "start": float(s.start),
                "end": float(s.end),
                "text": text,
            }
        )
    return segments
