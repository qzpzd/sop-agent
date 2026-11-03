from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print

app = typer.Typer(add_completion=False, help="SOP Agent CLI")


@app.command("run")
def run(
    video: Path = typer.Option(..., exists=True, dir_okay=False, help="输入视频路径"),
    out: Path = typer.Option(..., help="产出目录"),
    config: Path = typer.Option(
        Path("configs/default.yaml"),
        exists=True,
        dir_okay=False,
        help="管线配置",
    ),
    topic_hint: Optional[str] = typer.Option(None, help="主题提示，辅助 SOP 标题"),
) -> None:
    """运行完整视频 → SOP 管线。"""
    from sop_agent.pipeline.orchestrator import Orchestrator

    orch = Orchestrator.from_config(config)
    job = orch.run(video=video, out_dir=out, topic_hint=topic_hint)
    print(f"[green]完成[/green] job={job.job_id} status={job.status} → {out}")
    if job.error:
        print(f"[red]{job.error}[/red]")
        raise typer.Exit(1)


@app.command("phase0")
def phase0(
    video: Path = typer.Option(..., exists=True, dir_okay=False, help="输入视频路径"),
    out: Path = typer.Option(..., help="产出目录"),
    config: Path = typer.Option(
        Path("configs/default.yaml"),
        exists=True,
        dir_okay=False,
        help="管线配置",
    ),
) -> None:
    """Phase0 冒烟：ingest + asr + keyframes。"""
    from sop_agent.pipeline.orchestrator import Orchestrator

    orch = Orchestrator.from_config(config)
    job = orch.run(
        video=video,
        out_dir=out,
        phases=("ingest", "asr", "keyframes"),
    )
    arts = job.artifacts or {}
    n_seg = len(arts.get("segments") or [])
    n_scene = len(arts.get("scenes") or [])
    print(
        f"[green]Phase0[/green] job={job.job_id} status={job.status} "
        f"segments={n_seg} scenes={n_scene} → {out}"
    )
    if job.error:
        print(f"[red]{job.error}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status(job_id: str = typer.Argument(..., help="任务 ID")) -> None:
    """查询任务状态（SQLite）。"""
    from sop_agent.db.jobs import JobStore

    store = JobStore.default()
    job = store.get(job_id)
    if not job:
        print(f"[red]未找到[/red] {job_id}")
        raise typer.Exit(1)
    print(job)


if __name__ == "__main__":
    app()
