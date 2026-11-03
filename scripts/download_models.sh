#!/usr/bin/env bash
# 档位 C + Ollama：拉取本地推理与 ASR 模型
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/data/models/whisper"

echo "=== 档位 C / Ollama ==="
echo
echo "1) Ollama LLM（必需）:"
echo "   ollama pull qwen2.5:3b-instruct"
echo
echo "2) Whisper.cpp ggml-base（必需）:"
echo "   下载 ggml-base-q5_0.bin → data/models/whisper/"
echo "   参考: https://huggingface.co/ggerganov/whisper.cpp"
echo
echo "3) 可选轻量 VL（默认关闭，仅当你改 configs/default.yaml vl.enabled=true）:"
echo "   ollama pull qwen2.5-vl:3b"
echo
echo "4) 确认 Ollama 监听: http://127.0.0.1:11434"
echo "完成。默认配置已指向档位 C。"
