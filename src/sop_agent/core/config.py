from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class AsrConfig(BaseModel):
    # 档位 C / Windows 默认 faster_whisper；有 whisper-cli 时可改 whisper_cpp
    backend: str = "faster_whisper"
    model_path: str = "data/models/whisper/ggml-base-q5_0.bin"
    model_size: str = "base"
    language: str = "zh"
    threads: int = 4
    device: str = "cpu"
    compute_type: str = "int8"


class KeyframesConfig(BaseModel):
    min_scene_len_sec: float = 2.0
    hist_threshold: float = 0.5
    max_frames_per_min: int = 6
    fallback_interval_sec: float = 8.0


class ModelEndpointConfig(BaseModel):
    enabled: bool = True
    base_url: str = "http://127.0.0.1:11434/v1"
    api_key: str = "ollama"
    model: str = "qwen3:8b"
    temperature: float = 0.2
    max_scenes: int = 40
    batch_size: int = 1
    max_retries: int = 2


class RetrievalConfig(BaseModel):
    enabled: bool = False
    index_dir: str = "data/index"
    text_model: str = "data/models/bge-m3"


class PipelineConfig(BaseModel):
    asr: AsrConfig = Field(default_factory=AsrConfig)
    keyframes: KeyframesConfig = Field(default_factory=KeyframesConfig)
    vl: ModelEndpointConfig = Field(
        default_factory=lambda: ModelEndpointConfig(
            enabled=False,
            model="qwen2.5-vl:3b",
            temperature=0.1,
        )
    )
    llm: ModelEndpointConfig = Field(default_factory=ModelEndpointConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


class ExportConfig(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["json", "markdown"])


class StorageConfig(BaseModel):
    root: str = "storage/jobs"
    sqlite_path: str = "storage/jobs.db"


class AppConfig(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: dict[str, Any] = Field(default_factory=lambda: {"level": "INFO"})

    @classmethod
    def load(cls, path: Path | str) -> "AppConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)
