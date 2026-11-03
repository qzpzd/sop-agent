from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

import httpx
import yaml

from sop_agent.core.config import ModelEndpointConfig


def _load_prompt() -> dict[str, str]:
    path = Path("configs/prompts/vl_scene.yaml")
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        "system": "分析屏幕截图，输出 JSON。",
        "user_template": "scene_id={scene_id} transcript={transcript}",
    }


def _b64_image(path: str | Path) -> str:
    data = Path(path).read_bytes()
    return base64.b64encode(data).decode("ascii")


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        return json.loads(m.group(0))


class VlmClient:
    def __init__(self, cfg: ModelEndpointConfig) -> None:
        self.cfg = cfg
        self.prompts = _load_prompt()

    def analyze_scene(
        self,
        scene_id: int,
        image_path: str,
        start: float,
        end: float,
        transcript: str,
    ) -> dict[str, Any]:
        user = self.prompts["user_template"].format(
            scene_id=scene_id,
            start=start,
            end=end,
            transcript=transcript or "（无旁白）",
        )
        content = [
            {"type": "text", "text": user},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{_b64_image(image_path)}"},
            },
        ]
        payload = {
            "model": self.cfg.model,
            "temperature": self.cfg.temperature,
            "messages": [
                {"role": "system", "content": self.prompts["system"]},
                {"role": "user", "content": content},
            ],
        }
        with httpx.Client(base_url=self.cfg.base_url, timeout=120.0) as client:
            r = client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {self.cfg.api_key}"},
                json=payload,
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        data = _extract_json(text)
        data.setdefault("scene_id", scene_id)
        return data
