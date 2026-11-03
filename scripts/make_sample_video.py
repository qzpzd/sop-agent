"""Generate a short demo video with Chinese narration for Phase0."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "samples" / "demo_phase0.mp4"


def make_wav(path: Path) -> None:
    text = "第一步，打开订单管理页面。第二步，点击新建订单按钮。第三步，填写客户名称并保存。"
    # Windows SAPI via PowerShell (ASCII-only script body; Chinese in -Command string)
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.Rate = -1; "
        f"$s.SetOutputToWaveFile('{path.as_posix()}'); "
        f"$s.Speak('{text}'); "
        "$s.Dispose();"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=True,
    )


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "narration.wav"
        make_wav(wav)
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=1280x720:d=5",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=1280x720:d=5",
            "-f",
            "lavfi",
            "-i",
            "color=c=orange:s=1280x720:d=5",
            "-i",
            str(wav),
            "-filter_complex",
            "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
            "-map",
            "[v]",
            "-map",
            "3:a",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-shortest",
            str(OUT),
        ]
        subprocess.run(cmd, check=True)
    print(f"OK: {OUT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("failed:", exc, file=sys.stderr)
        raise SystemExit(1)
