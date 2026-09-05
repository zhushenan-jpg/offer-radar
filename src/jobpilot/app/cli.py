"""CLI 入口:typer 应用."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(no_args_is_help=True, help="JobPilot — 多 Agent 求职调研助手")
console = Console()


@app.callback()
def _root() -> None:
    """强制子命令模式,保证 `jobpilot <command>` 用法随命令增多保持稳定."""


@app.command()
def score(
    file: Path = typer.Option(..., "--file", exists=True, help="JD markdown 文件"),
    profile: Path = typer.Option(Path("profile.yaml"), "--profile", exists=True),
    db: Path = typer.Option(Path("jobpilot.db"), "--db", help="SQLite 路径"),
    fake: bool = typer.Option(False, "--fake", help="离线演示:内置假 LLM,不调用真实 API"),
):
    """对单个 JD 文件做简历匹配评分并入库."""
    from jobpilot.agents.matcher import score_and_store
    from jobpilot.config import GatewayConfig
    from jobpilot.models.job import JobPosting
    from jobpilot.models.profile import load_profile
    from jobpilot.storage.db import Storage

    prof = load_profile(profile)
    jd_md = file.read_text(encoding="utf-8")
    job = JobPosting(
        id=JobPosting.compute_id("manual", "manual", file.stem, ""),
        source="manual",
        company="manual",
        title=file.stem,
        description_md=jd_md,
    )
    storage = Storage.open(db)
    storage.jobs.upsert(job)

    cfg = GatewayConfig()
    if fake:
        from jobpilot.testing import FakeGateway

        gw = FakeGateway(cfg, storage)
    else:
        from jobpilot.llm_gateway.gateway import LLMGateway

        gw = LLMGateway(cfg, storage)

    result = score_and_store(gw, storage, prof, jd_md, job_id=job.id)

    table = Table(title=f"{file.name} × {prof.name}")
    table.add_column("维度")
    table.add_column("得分", justify="right")
    table.add_column("证据(逐字引用 JD)")
    for dim in ("skills", "experience", "constraints", "growth"):
        ds = result.dims[dim]
        table.add_row(dim, f"{ds.score}/10", ds.evidence[0].quote)
    console.print(table)
    console.print(
        f"[bold]综合匹配:{result.overall}/100[/] | 置信度:{result.confidence:.2f} | {result.summary}"
    )
    if fake:
        console.print("[dim]--fake 模式:以上为离线假数据,不花 API 费用[/]")


def main() -> None:
    app()
