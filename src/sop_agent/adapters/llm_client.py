from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
import yaml

from sop_agent.core.config import ModelEndpointConfig


def _load_prompt() -> dict[str, str]:
    path = Path("configs/prompts/sop_compose.yaml")
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        "system": "整理 SOP，输出 JSON。",
        "user_template": "{timeline_json}",
    }


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    # Qwen3 等模型可能夹带思考标签
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"<thinking>[\s\S]*?</thinking>", "", text, flags=re.IGNORECASE).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        return json.loads(m.group(0))


class LlmClient:
    """OpenAI-compatible chat（默认对接本机 Ollama）。"""

    def __init__(self, cfg: ModelEndpointConfig) -> None:
        self.cfg = cfg
        self.prompts = _load_prompt()

    def compose_sop(self, timeline: list[dict[str, Any]], topic_hint: str = "") -> dict[str, Any]:
        user = self.prompts["user_template"].format(
            topic_hint=topic_hint or "（无）",
            timeline_json=json.dumps(timeline, ensure_ascii=False, indent=2),
        )
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "temperature": self.cfg.temperature,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.prompts["system"]},
                {"role": "user", "content": user},
            ],
            # Ollama / 部分后端支持；忽略不支持时的校验错误由重试处理
            "format": "json",
        }
        # CPU 3B 生成较长 JSON 可能很慢
        timeout = httpx.Timeout(600.0, connect=30.0)
        last_err: Exception | None = None
        retries = max(1, self.cfg.max_retries)
        for attempt in range(retries):
            try:
                with httpx.Client(base_url=self.cfg.base_url, timeout=timeout) as client:
                    r = client.post(
                        "/chat/completions",
                        headers={"Authorization": f"Bearer {self.cfg.api_key}"},
                        json=payload,
                    )
                    if r.status_code == 400 and "format" in payload:
                        payload.pop("format", None)
                        r = client.post(
                            "/chat/completions",
                            headers={"Authorization": f"Bearer {self.cfg.api_key}"},
                            json=payload,
                        )
                    r.raise_for_status()
                    body = r.json()
                    text = body["choices"][0]["message"]["content"]
                return _extract_json(text)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                if attempt + 1 >= retries:
                    break
        raise RuntimeError(
            f"SOP 生成失败（请确认 Ollama 已启动且已 pull {self.cfg.model}）: {last_err}"
        )
