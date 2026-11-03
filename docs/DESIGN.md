# SOP 自动生成智能体 — 设计方案

> 目标：复刻「类 Hinto AI」视频 → SOP 能力，**完全私有化**、可本地/内网部署。

---

## 1. 产品目标与边界

### 1.1 核心能力

| 能力 | 说明 |
|------|------|
| 视频理解 | 从操作录屏/教学视频中抽取步骤、关键画面、旁白 |
| SOP 结构化 | 输出规范 SOP（标题、步骤、要点、注意事项、截图） |
| 素材对齐 | 步骤与关键帧、字幕片段一一对应 |
| 可选检索 | 与已有 SOP/素材库做相似匹配，避免重复建设 |

### 1.2 非目标（首期不做）

- 在线 SaaS、多租户计费
- 实时流式直播 SOP（首期批处理即可）
- 自动执行操作（RPA），仅做「文档生成」
- 闭源云端多模态 API（可预留适配层，默认走本地）

### 1.3 成功标准（MVP）

1. 输入一段 5–30 分钟操作录屏，输出 Markdown / JSON SOP
2. 每步含：序号、动作描述、关键帧截图、对应时间戳、旁白摘录
3. 端到端可在单机 GPU（≥24GB 显存，如 4090）或「CPU+量化」弱化配置跑通
4. 全链路无外网依赖（模型权重预下载）

---

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        API / CLI / Web UI                        │
│                     (FastAPI + 简易前端)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ Job 提交
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator（编排层）                        │
│            状态机：PENDING → RUNNING → DONE / FAILED              │
└─┬───────┬──────────┬──────────┬──────────┬──────────┬───────────┘
  │       │          │          │          │          │
  ▼       ▼          ▼          ▼          ▼          ▼
┌────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│FFmpeg│ │Whisper│ │ OpenCV │ │ VL 模型 │ │ Qwen2  │ │ FAISS    │
│拆解 │ │.cpp  │ │抽帧/变 │ │关键帧  │ │SOP整理 │ │(可选检索)│
└────┘ │ASR   │ │化检测  │ │理解    │ │        │ └──────────┘
       └──────┘ └────────┘ └────────┘ └────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Artifact Store  │
                    │ 帧/音频/字幕/SOP │
                    └─────────────────┘
```

### 2.1 数据流（Pipeline）

```
Video
  │
  ├─(1) FFmpeg ──► audio.wav + 规范化视频
  │
  ├─(2) Whisper.cpp ──► transcript.json (segments: t0,t1,text)
  │
  ├─(3) OpenCV ──► keyframes/ + scene_cuts.json
  │         │
  │         └─ 与 transcript 时间对齐 → shot 列表
  │
  ├─(4) InternVL / Qwen-VL ──► 对每个 shot/关键帧做视觉描述
  │                              + 操作意图（点击/输入/切换…）
  │
  ├─(5) Qwen2 LLM ──► 合并「旁白 + 视觉描述 + 时间线」
  │                    → 规范 SOP（JSON Schema 约束）
  │
  └─(6) [可选] FAISS ──► 相似历史 SOP / 图标素材匹配
           │
           ▼
      SOP.md + SOP.json + assets/
```

---

## 3. 技术选型（落地版）

### 3.1 选型一览

| 层级 | 选型 | 理由 | 替代/降级 |
|------|------|------|-----------|
| 视频/音频 | **FFmpeg** | 事实标准，拆轨、转码、截帧稳定 | — |
| ASR | **whisper.cpp** | 本地 C++，量化后 CPU 可跑；无 Python GIL 压力 | faster-whisper（若已有 CUDA 生态） |
| 抽帧/切镜 | **OpenCV** + 直方图/SSIM 变化检测 | 轻量、可控阈值 | PySceneDetect |
| 多模态 VL | **Qwen2.5-VL-7B**（首选）或 InternVL2-8B | 中文强、开源可私有化；7B 单卡可跑 | 3B/量化 INT4 弱机 |
| 文本 LLM | **Qwen2.5-7B/14B-Instruct** | 结构化输出、中文 SOP 质量好 | 同系 3B / AWQ |
| 推理运行时 | **vLLM** 或 **Ollama** / **llama.cpp** | vLLM 吞吐好；Ollama 运维最简单 | LMDeploy |
| 向量检索 | **FAISS** + sentence-transformers（bge-m3） | 纯本地、成熟 | Chroma（要持久化管理时） |
| 编排 | **Python 3.11+** + 自研 Pipeline / Prefect | 首期自研状态机即可 | Celery+Redis |
| API | **FastAPI** | 异步任务、SSE 进度 | — |
| 存储 | 本地目录 + SQLite（任务元数据） | 零运维 | PostgreSQL（多机） |
| 前端 | Vue3 / React 简易页（上传+进度+预览） | MVP 可先 CLI | — |

### 3.2 模型落地建议（硬件分层）

| 档位 | 硬件 | 推荐组合 |
|------|------|----------|
| **A. 生产推荐** | RTX 4090 24GB | Qwen2.5-VL-7B-Instruct (AWQ/GPTQ) + Qwen2.5-14B-Instruct；whisper `large-v3` q5 |
| **B. 开发机** | 16GB 显存 | VL-7B INT4 + LLM-7B INT4；whisper `medium` |
| **C. CPU-only 演示** | 无 GPU | whisper.cpp tiny/base；跳过 VL 或极稀疏抽帧 + 仅旁白生成粗 SOP |

**已确认首期走档位 C + Ollama**：关 VL，Whisper `base` 量化 + `qwen2.5:3b-instruct`；配置见 `configs/default.yaml`。

### 3.3 为何 VL 与 LLM 拆开

- VL：专管「看见了什么、界面发生了什么」
- LLM：专管「写成规范 SOP、合并去重、统一语气、填 Schema」
- 好处：提示词可独立迭代；LLM 可更大；失败可局部重试

---

## 4. 模块设计

### 4.1 `ingest` — 接入与规范化

- 校验格式：mp4/mkv/mov/webm
- FFmpeg：统一为 H.264 + AAC；抽取 mono 16kHz wav（Whisper 友好）
- 产出：`work/{job_id}/source.mp4`, `audio.wav`, `meta.json`（时长、分辨率、fps）

### 4.2 `asr` — Whisper.cpp

- 调用方式：子进程调用 `whisper-cli`，或 `pywhispercpp` 绑定
- 输出：VTT/JSON segments
- 后处理：中文标点（可选 `ct-punc` 或 LLM 轻修）、合并过短 segment

### 4.3 `vision` — OpenCV 关键帧

策略（可配置）：

1. **硬切检测**：相邻帧直方图差 / 光流幅度超阈值 → scene cut
2. **定时兜底**：每 N 秒至少 1 帧（防止静音长镜头漏抽）
3. **UI 变化增强**（可选）：屏幕录制场景对窗口 ROI 做差分，提高「点击后界面变化」召回

产出：`keyframes/{ts}.jpg` + `scenes.json`：

```json
{
  "scenes": [
    {"id": 0, "start": 12.3, "end": 28.1, "keyframe": "keyframes/12.30.jpg", "score": 0.82}
  ]
}
```

### 4.4 `vl_analyze` — 多模态关键帧理解

对每个 scene（或合并后的 shot）：

**输入**：关键帧（可拼 1–3 帧）+ 该时段旁白摘要  
**输出**（严格 JSON）：

```json
{
  "scene_id": 0,
  "action": "点击左侧「订单管理」菜单",
  "ui_elements": ["侧边栏", "订单管理"],
  "result": "进入订单列表页",
  "risk_notes": [],
  "confidence": 0.78
}
```

批处理：按 GPU 显存动态 `batch_size`；失败 scene 记入 retry 队列。

### 4.5 `sop_compose` — Qwen2 结构化成文

**输入**：全量 timeline（ASR + VL + 时间戳）  
**约束**：JSON Schema（见下）  
**后处理**：校验必填字段；步骤合并（相邻同动作）；生成 Markdown

SOP Schema（MVP）：

```json
{
  "title": "string",
  "summary": "string",
  "prerequisites": ["string"],
  "steps": [
    {
      "index": 1,
      "title": "string",
      "instruction": "string",
      "expected_result": "string",
      "notes": ["string"],
      "timestamp_start": 0.0,
      "timestamp_end": 0.0,
      "keyframe": "assets/step_01.jpg",
      "transcript_quote": "string"
    }
  ],
  "warnings": ["string"]
}
```

### 4.6 `retrieval` — FAISS（可选，二期）

- 文本：步骤 instruction → `bge-m3` 向量
- 图像：关键帧 → CLIP / Chinese-CLIP 向量（可选）
- 用途：推荐相似历史 SOP；补全「标准话术」；图标/按钮素材库匹配

### 4.7 `orchestrator`

- Job 状态机 + 断点续跑（每 stage 落盘）
- 进度事件：通过 SSE / WebSocket 推送百分比与当前阶段
- 并发：单机默认 1 路视频（GPU 争用）；队列可扩展 Redis

---

## 5. 项目框架（目录与职责）

```
sop-agent/
├── README.md
├── docs/
│   └── DESIGN.md                 # 本设计文档
├── pyproject.toml / requirements.txt
├── configs/
│   ├── default.yaml              # 管线默认参数
│   ├── models.yaml               # 模型路径、量化、设备
│   └── prompts/                  # VL / LLM 提示词模板
│       ├── vl_scene.yaml
│       └── sop_compose.yaml
├── scripts/
│   ├── download_models.sh        # 预拉权重
│   ├── build_whisper.sh
│   └── smoke_test.py
├── third_party/                  # 可选：whisper.cpp 预编译说明
├── data/
│   ├── models/                   # gitignore，本地权重
│   ├── samples/                  # 样例视频
│   └── index/                    # FAISS 索引
├── storage/
│   └── jobs/                     # 运行产物
├── src/
│   └── sop_agent/
│       ├── __init__.py
│       ├── main.py               # CLI 入口
│       ├── api/
│       │   ├── app.py            # FastAPI
│       │   ├── routes_jobs.py
│       │   └── schemas.py
│       ├── core/
│       │   ├── config.py
│       │   ├── logging.py
│       │   └── schemas_sop.py    # Pydantic SOP 模型
│       ├── pipeline/
│       │   ├── orchestrator.py
│       │   ├── stages/
│       │   │   ├── ingest.py
│       │   │   ├── asr.py
│       │   │   ├── keyframes.py
│       │   │   ├── vl_analyze.py
│       │   │   ├── sop_compose.py
│       │   │   └── retrieve.py
│       │   └── timeline.py       # ASR↔Scene 对齐
│       ├── adapters/
│       │   ├── ffmpeg.py
│       │   ├── whisper_cpp.py
│       │   ├── opencv_frames.py
│       │   ├── vlm_client.py     # OpenAI-compatible / 本地 HTTP
│       │   ├── llm_client.py
│       │   └── faiss_store.py
│       ├── exporters/
│       │   ├── markdown.py
│       │   └── json_export.py
│       └── db/
│           └── jobs.py           # SQLite 任务表
├── web/                          # 可选前端（二期）
│   └── ...
├── tests/
│   ├── unit/
│   └── fixtures/
└── docker/
    ├── Dockerfile
    └── docker-compose.yml        # api + 模型服务
```

### 5.1 配置驱动（`configs/default.yaml` 示意）

```yaml
pipeline:
  asr:
    model: large-v3-q5_0
    language: zh
  keyframes:
    min_scene_len_sec: 1.5
    hist_threshold: 0.45
    max_frames_per_min: 12
  vl:
    model: Qwen2.5-VL-7B-Instruct
    max_scenes: 80          # 超长视频抽样上限
    batch_size: 1
  llm:
    model: Qwen2.5-7B-Instruct
    temperature: 0.2
  retrieval:
    enabled: false
export:
  formats: [json, markdown]
```

---

## 6. 接口设计（MVP）

### 6.1 CLI

```bash
sop-agent run --video ./demo.mp4 --out ./storage/jobs/demo --config configs/default.yaml
sop-agent status --job <id>
```

### 6.2 HTTP

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/jobs` | multipart 上传视频，创建 job |
| GET | `/api/v1/jobs/{id}` | 状态、进度、错误 |
| GET | `/api/v1/jobs/{id}/events` | SSE 进度流 |
| GET | `/api/v1/jobs/{id}/sop` | 获取 SOP JSON/MD |
| GET | `/api/v1/jobs/{id}/assets/{name}` | 关键帧等静态资源 |

---

## 7. 分阶段落地路线

### Phase 0 — 骨架（约 3–5 天）

- 仓库结构、配置、FFmpeg/OpenCV 抽帧、Whisper.cpp 转写打通
- CLI 一键跑通「视频 → 字幕 + 关键帧」

### Phase 1 — MVP SOP（约 1–2 周）

- 接入 Ollama LLM（档位 C 默认无 VL，旁白主导）；Timeline 对齐 + Schema 约束输出
- Markdown/JSON 导出；FastAPI 上传与查询

### Phase 2 — 质量与体验（约 2 周）

- 步骤合并/去噪、置信度过滤、人工校正回写
- 进度 SSE、简易 Web 预览（步骤 ↔ 关键帧）
- 提示词与评测集（10 条样例视频人工打分）

### Phase 3 — 检索与规模（可选）

- FAISS 历史 SOP 检索、素材库匹配
- 队列化、多 GPU、Docker 一键部署

---

## 8. 质量与风险

| 风险 | 缓解 |
|------|------|
| VL 幻觉（编造按钮名） | 旁白交叉验证；低置信度标「待人工确认」 |
| 长视频 scene 爆炸 | `max_frames_per_min` + 自适应抽样 |
| 无旁白纯操作视频 | 提高抽帧密度；VL 权重加大；模板提示「无语音」 |
| GPU OOM | 量化、单 batch、VL/LLM 分时加载 |
| 结构化失败 | JSON repair + Schema 重试（最多 2 次） |

**评测指标（内部）：**

- 步骤召回（人工标注步骤覆盖率）
- 时间戳对齐误差（秒）
- 指令可执行性主观分（1–5）
- 端到端耗时（× 视频时长）

---

## 9. 部署形态

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  sop-agent   │────▶│  vLLM / Ollama   │     │  whisper.cpp    │
│  API + 管线  │     │  VL + LLM 服务   │     │  (本地二进制)    │
└──────┬───────┘     └──────────────────┘     └─────────────────┘
       │
       ▼
  ./storage/jobs + SQLite
```

- 开发：单进程 CLI
- 内网生产：`docker-compose` 起 API + 推理服务；模型挂 volume
- 空气间隙：离线 wheel + 预下载 `data/models`

---

## 10. 结论与下一步

**可立即落地的最小闭环：**

`FFmpeg → Whisper.cpp → OpenCV → Qwen2.5-VL → Qwen2.5-Instruct → Markdown/JSON`

FAISS 作为二期增强，不阻塞 MVP。

**建议下一步：**

1. 确认硬件档位（A/B/C）与默认模型
2. 按本仓库骨架初始化代码与 `configs/`
3. 用 1 条真实业务录屏跑 Phase 0 冒烟

---

## 附录 A — 与「类 Hinto」能力映射

| Hinto 类能力 | 本方案模块 |
|--------------|------------|
| 视频拆解 | ingest + FFmpeg |
| 语音理解 | asr / whisper.cpp |
| 画面关键节点 | keyframes / OpenCV |
| 界面/动作理解 | vl_analyze |
| SOP 成文 | sop_compose |
| 素材/知识复用 | retrieval / FAISS |

## 附录 B — 许可注意

使用 Qwen / InternVL / Whisper 权重时，确认其开源协议是否满足商用与私有化分发要求；企业内网部署一般可行，对外再分发需单独法务确认。
