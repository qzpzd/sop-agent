from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _require_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("未找到 ffmpeg，请先安装并加入 PATH")
    return exe


def normalize_and_extract(video: Path, source_out: Path, audio_out: Path) -> dict[str, Any]:
    """尽量流复制视频；始终抽取 16kHz mono wav 供 ASR。"""
    ffmpeg = _require_ffmpeg()
    # 视频：优先 copy（快）；失败再转码
    copy = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(source_out),
        ],
        capture_output=True,
    )
    if copy.returncode != 0:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(video),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(source_out),
            ],
            check=True,
            capture_output=True,
        )

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(audio_out),
        ],
        check=True,
        capture_output=True,
    )
    meta = probe(source_out)
    (source_out.parent / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


def probe(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"path": str(path)}
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)
