# 管线原理：FFmpeg × Whisper × OpenCV → Phase1 SOP

## 如何把已有视频变成新 Job

```bash
conda activate sop
cd D:\qzp\sop-agent

# Phase0：拆解 + 转写 + 关键帧
python -m sop_agent.main phase0 `
  --video "D:\qzp\sop-agent\data\samples\WIN_20260622_14_40_12_Pro.mp4" `
  --out "D:\qzp\sop-agent\storage\jobs\win_real_01"

# Phase0+1：再接 Ollama 生成 SOP
python -m sop_agent.main run `
  --video "D:\qzp\sop-agent\data\samples\WIN_20260622_14_40_12_Pro.mp4" `
  --out "D:\qzp\sop-agent\storage\jobs\win_real_01" `
  --topic-hint "操作录屏 SOP"
```

每个 `--out` 目录即一个 job；产物落在 `out/work/` 与 `out/SOP.json|md`。

---

## 三者如何结合（数据流）

```
输入视频
   │
   ├─① FFmpeg（ingest）
   │     ├─ source.mp4   统一编码，便于后续解码
   │     └─ audio.wav    16kHz 单声道 PCM —— Whisper 专用
   │
   ├─② Whisper / faster-whisper（asr）
   │     └─ transcript.json
   │           segments: [{start, end, text}, ...]
   │           ↑ 文本来自「声音」；时间轴来自声学对齐
   │
   ├─③ OpenCV 或 FFmpeg（keyframes）
   │     └─ scenes.json + keyframes/*.jpg
   │           scenes: [{id, start, end, keyframe}, ...]
   │           ↑ 画面来自「像素变化」；与声音无关
   │
   └─④ 时间线对齐（timeline）
         对每个 scene，取 [start,end] 内的 ASR 旁白拼在一起
         → timeline.json: 画面关键点 + 对应口播
         → Phase1：Ollama LLM 整理成 SOP.json / SOP.md
```

**核心思想：** 声音与画面两条线并行抽取，再用**时间戳对齐**合成「步骤候选」，最后由 LLM 写成规范 SOP。档位 C 关闭 VL，不看图理解 UI，只靠旁白 + 关键帧路径。

---

## 文本从哪来（Whisper）

1. FFmpeg 抽出 `audio.wav`（16 kHz mono），匹配 Whisper 训练分布。
2. `faster-whisper` 加载 `base` 模型（CPU int8）。
3. 模型做语音识别 + 时间戳对齐，输出带 `start/end` 的句子片段。
4. 可选 VAD：跳过静音，减少幻觉。

**原理：** 声学特征 → 编码器 → 解码器生成 token；强制对齐得到每段起止时间。

---

## 关键帧从哪来（OpenCV / FFmpeg）

本仓库策略（可配置）：

1. **画面变化检测（主）**  
   降采样读帧 → 算相邻帧颜色直方图相关度 → 差异 ≥ `hist_threshold` 且间隔 ≥ `min_scene_len_sec` → 记为新镜头并截图。
2. **定时兜底**  
   若长时间无显著变化，每 `fallback_interval_sec` 仍抽一帧（避免静音长镜头漏检）。
3. **密度上限**  
   `max_frames_per_min` 限制过密抽帧（短视频另有下限，避免只剩 1 帧）。
4. **回退**  
   OpenCV DLL 不可用时，改用 FFmpeg `select=gt(scene,…)` + 按时间戳截图。

**原理：** 不是「语义理解画面」，而是「像素/直方图突变 ≈ 切镜或界面大变」；录屏里点击后页面跳转常会触发。

---

## Phase1 做什么

把 `timeline`（每镜：时间、关键帧路径、旁白）喂给 Ollama `qwen2.5:3b-instruct`，约束输出 SOP Schema（标题、步骤、预期结果、时间戳、旁白摘录），再导出 Markdown/JSON。
