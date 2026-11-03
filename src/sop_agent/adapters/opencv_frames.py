"""OpenCV keyframe extraction (optional; may fail on some Windows Python builds)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np


def _hist_diff(a: np.ndarray, b: np.ndarray) -> float:
    ha = cv2.calcHist([a], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    hb = cv2.calcHist([b], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    cv2.normalize(ha, ha)
    cv2.normalize(hb, hb)
    corr = cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL)
    return float(max(0.0, 1.0 - corr))


def extract_keyframes(
    video: Path,
    out_dir: Path,
    hist_threshold: float = 0.45,
    min_scene_len_sec: float = 1.5,
    max_frames_per_min: int = 12,
    fallback_interval_sec: float = 5.0,
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if fps else 0.0
    # 短视频至少保留若干关键帧，避免 duration/60 截成 1
    max_total = max(8, int((duration / 60.0) * max_frames_per_min + 0.999))

    scenes: list[dict[str, Any]] = []
    prev_small = None
    scene_start = 0.0
    last_emit_t = -1e9
    idx = 0
    frame_i = 0
    step = max(1, int(fps * 0.5))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_i % step != 0:
            frame_i += 1
            continue
        t = frame_i / fps
        small = cv2.resize(frame, (160, 90))
        emit = False
        if prev_small is None:
            emit = True
        else:
            diff = _hist_diff(prev_small, small)
            if diff >= hist_threshold and (t - scene_start) >= min_scene_len_sec:
                emit = True
            elif (t - last_emit_t) >= fallback_interval_sec:
                emit = True

        if emit and len(scenes) < max_total:
            name = out_dir / f"{t:08.2f}.jpg"
            cv2.imwrite(str(name), frame)
            scenes.append(
                {
                    "id": idx,
                    "start": t,
                    "end": t,
                    "keyframe": str(name),
                    "score": 1.0,
                }
            )
            idx += 1
            scene_start = t
            last_emit_t = t

        prev_small = small
        frame_i += 1

    cap.release()
    if scenes:
        scenes[-1]["end"] = duration or scenes[-1]["start"] + 0.1
        for i in range(len(scenes) - 1):
            scenes[i]["end"] = scenes[i + 1]["start"]
    return scenes
