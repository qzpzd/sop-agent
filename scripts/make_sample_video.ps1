# Phase0: 生成带中文旁白的短样例视频（Windows SAPI + FFmpeg）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$SampleDir = Join-Path $Root "data\samples"
New-Item -ItemType Directory -Force -Path $SampleDir | Out-Null

$Wav = Join-Path $SampleDir "_narration.wav"
$Video = Join-Path $SampleDir "demo_phase0.mp4"

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = -1
$synth.SetOutputToWaveFile($Wav)
$synth.Speak("第一步，打开订单管理页面。第二步，点击新建订单按钮。第三步，填写客户名称并保存。")
$synth.Dispose()

$ffArgs = @(
  "-y",
  "-f", "lavfi", "-i", "color=c=blue:s=1280x720:d=5",
  "-f", "lavfi", "-i", "color=c=green:s=1280x720:d=5",
  "-f", "lavfi", "-i", "color=c=orange:s=1280x720:d=5",
  "-i", $Wav,
  "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
  "-map", "[v]",
  "-map", "3:a",
  "-c:v", "libx264",
  "-pix_fmt", "yuv420p",
  "-preset", "veryfast",
  "-c:a", "aac",
  "-shortest",
  $Video
)

& ffmpeg @ffArgs
if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed: $LASTEXITCODE" }

Remove-Item $Wav -Force -ErrorAction SilentlyContinue
Write-Host "OK: $Video"
