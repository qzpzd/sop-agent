# SOP Agent

从操作录屏/教学视频**私有化自动生成 SOP** 的智能体。

技术栈：FFmpeg · Whisper.cpp / faster-whisper · OpenCV · Qwen-VL · Qwen2 · FAISS（可选）

## 当前运行档

| 项 | 选择 |
|----|------|
| 硬件 | **C（CPU）** |
| 推理 | **Ollama** |
| Python | **conda env `sop`**（3.10；勿用 base 的 3.13） |
| ASR | `faster-whisper` `base` |
| LLM | `qwen2.5:3b-instruct` |
| VL | **关闭** |

## Phase0 冒烟

```bash
conda activate sop
pip install -e .
python scripts/make_sample_video.py
python scripts/smoke_phase0.py
```

## 真实视频 → Job（Phase0+1）

原理说明见 [docs/PIPELINE.md](docs/PIPELINE.md)。

```bash
conda activate sop
# 一键：转写+关键帧+Ollama 成文
python scripts/run_real_phase1.py
# 或指定任意视频
python -m sop_agent.main run --video "data/samples/WIN_20260622_14_40_12_Pro.mp4" --out storage/jobs/my_job --topic-hint "操作录屏"
```

产物：`storage/jobs/<job>/SOP.md`、`SOP.json`、`work/transcript.json`、`work/scenes.json`、`work/keyframes/`。

## 阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 转写 + 关键帧 | **已打通** |
| 1 | Ollama → SOP MVP | **已打通**（默认 `qwen3:8b`） |
| 2 | 质量与 Web | 待开始 |
| 3 | FAISS / 可选 VL | 待开始 |
