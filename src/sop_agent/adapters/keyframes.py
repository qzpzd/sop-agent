from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


def extract_keyframes(
    video: Path,
    out_dir: Path,
    hist_threshold: float = 0.45,
    min_scene_len_sec: float = 1.5,
    max_frames_per_min: int = 12,
    fallback_interval_sec: float = 5.0,
) -> list[dict[str, Any]]:
    """优先 OpenCV；DLL 不可用时回退 FFmpeg 场景检测。"""
    try:
        from sop_agent.adapters import opencv_frames

        return opencv_frames.extract_keyframes(
            video=video,
            out_dir=out_dir,
            hist_threshold=hist_threshold,
            min_scene_len_sec=min_scene_len_sec,
            max_frames_per_min=max_frames_per_min,
            fallback_interval_sec=fallback_interval_sec,
        )
    except Exception:
        return extract_with_ffmpeg(
            video=video,
            out_dir=out_dir,
            scene_threshold=max(0.1, min(0.9, hist_threshold)),
            fallback_interval_sec=fallback_interval_sec,
            max_frames_per_min=max_frames_per_min,
        )


def _probe_duration(video: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def extract_with_ffmpeg(
    video: Path,
    out_dir: Path,
    scene_threshold: float = 0.4,
    fallback_interval_sec: float = 5.0,
    max_frames_per_min: int = 12,
) -> list[dict[str, Any]]:
    """用 FFmpeg select=scene 抽关键帧；不足时按间隔补帧。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    duration = _probe_duration(video)
    max_total = (
        max(8, int((duration / 60.0) * max_frames_per_min + 0.999)) if duration else 30
    )

    # 场景切点时间戳（stderr 里 showinfo）
    scene_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(video),
        "-vf",
        f"select='gt(scene,{scene_threshold})',showinfo",
        "-vsync",
        "vfr",
        "-frame_pts",
        "1",
        str(out_dir / "scene_%08d.jpg"),
    ]
    proc = subprocess.run(scene_cmd, capture_output=True, text=True)
    times = _parse_showinfo_pts(proc.stderr)

    # 若切点太少，按固定间隔补抽
    if len(times) < 2 and duration > 0:
        for t in _frange(0.0, max(duration - 0.1, 0.0), fallback_interval_sec):
            times.append(t)
        times = sorted(set(round(t, 2) for t in times))

    times = times[:max_total]
    if not times:
        times = [0.0]

    # 按精确时间戳重新截取，文件名带秒数
    scenes: list[dict[str, Any]] = []
    for i, t in enumerate(times):
        name = out_dir / f"{t:08.2f}.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{t:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(name),
            ],
            check=True,
            capture_output=True,
        )
        scenes.append(
            {
                "id": i,
                "start": float(t),
                "end": float(t),
                "keyframe": str(name),
                "score": 1.0,
            }
        )

    # 串联 end
    for i in range(len(scenes) - 1):
        scenes[i]["end"] = scenes[i + 1]["start"]
    if scenes:
        scenes[-1]["end"] = duration or (scenes[-1]["start"] + fallback_interval_sec)

    # 清理临时 scene_*.jpg
    for p in out_dir.glob("scene_*.jpg"):
        p.unlink(missing_ok=True)

    return scenes


def _parse_showinfo_pts(stderr: str) -> list[float]:
    # showinfo 行含 pts_time:1.234567
    found = re.findall(r"pts_time:([0-9.]+)", stderr or "")
    return [float(x) for x in found]


def _frange(start: float, stop: float, step: float) -> list[float]:
    if step <= 0:
        return [start]
    vals: list[float] = []
    t = start
    while t <= stop + 1e-6:
        vals.append(t)
        t += step
    return vals
