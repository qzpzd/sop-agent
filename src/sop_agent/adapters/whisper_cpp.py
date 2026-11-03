from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _find_whisper_cli() -> str:
    for name in ("whisper-cli", "whisper-cpp", "main"):
        exe = shutil.which(name)
        if exe:
            return exe
    raise RuntimeError(
        "未找到 whisper.cpp 可执行文件（whisper-cli）。"
        "请编译安装 whisper.cpp 并确保在 PATH 中，或后续在配置中指定 binary_path。"
    )


def transcribe(
    audio: Path,
    model_path: str | Path,
    language: str = "zh",
    threads: int = 4,
    out_json: Path | None = None,
) -> list[dict[str, Any]]:
    """调用 whisper.cpp CLI，返回 segments[{start,end,text}]。"""
    model = Path(model_path)
    if not model.exists():
        raise FileNotFoundError(
            f"Whisper 模型不存在: {model}。请下载 ggml 模型到 data/models/whisper/"
        )

    cli = _find_whisper_cli()
    # 新版 whisper.cpp 常用: whisper-cli -m model -f audio -oj -of out_prefix
    out_prefix = (out_json or audio.with_suffix("")).with_suffix("")
    cmd = [
        cli,
        "-m",
        str(model),
        "-f",
        str(audio),
        "-l",
        language,
        "-t",
        str(threads),
        "-oj",
        "-of",
        str(out_prefix),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    result_path = Path(str(out_prefix) + ".json")
    if not result_path.exists():
        # 部分构建输出名为 audio.json
        alt = audio.with_suffix(".json")
        if alt.exists():
            result_path = alt
        else:
            raise FileNotFoundError("whisper.cpp 未产出 JSON 转写结果")

    raw = json.loads(result_path.read_text(encoding="utf-8"))
    segments = []
    for s in raw.get("transcription") or raw.get("segments") or []:
        # whisper.cpp -oj 格式字段名可能是 offsets / timestamps
        start = s.get("offsets", {}).get("from", s.get("start", 0))
        end = s.get("offsets", {}).get("to", s.get("end", 0))
        # offsets 常为毫秒
        if isinstance(start, (int, float)) and start > 1000:
            start, end = start / 1000.0, end / 1000.0
        text = (s.get("text") or "").strip()
        segments.append({"start": float(start), "end": float(end), "text": text})
    return segments
