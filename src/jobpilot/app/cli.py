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


@app.command()
def report(
    profile: Path = typer.Option(Path("profile.yaml"), "--profile", exists=True),
    db: Path = typer.Option(Path("jobpilot.db"), "--db", help="SQLite 路径"),
    sources: Path = typer.Option(Path("sources.yaml"), "--sources", exists=True),
    out_dir: Path = typer.Option(Path("docs/reports"), "--out-dir", help="周报输出目录"),
    fake: bool = typer.Option(False, "--fake", help="离线演示:假评分+确定性流水线,不花 API 钱"),
    no_crew: bool = typer.Option(False, "--no-crew", help="跳过 crewAI 编排,直接顺序执行"),
    limit: int = typer.Option(None, "--limit", help="最多评分 N 条(小批量验证用)"),
):
    """采集 → 清洗 → 评分 → 生成求职周报(M2 主流程)."""
    import asyncio

    import yaml

    from jobpilot.config import GatewayConfig
    from jobpilot.models.profile import load_profile
    from jobpilot.pipeline import run_report
    from jobpilot.storage.db import Storage

    srcs = yaml.safe_load(sources.read_text(encoding="utf-8"))
    storage = Storage.open(db)
    prof = load_profile(profile)
    cfg = GatewayConfig()
    if fake:
        # 假评分必须记在 fake-model 名下,避免污染真模型的成本/评测数据
        cfg = cfg.model_copy(update={"model": "fake-model"})
        from jobpilot.testing import FakeGateway

        gw, use_crew = FakeGateway(cfg, storage), False
    else:
        from jobpilot.llm_gateway.gateway import LLMGateway

        gw, use_crew = LLMGateway(cfg, storage), not no_crew

    path = asyncio.run(
        run_report(
            storage,
            prof,
            srcs,
            gateway=gw,
            use_crew=use_crew,
            out_dir=out_dir,
            db_path=db,
            limit=limit,
        )
    )
    console.print(f"[green]周报已生成:[/]{path}")


@app.command("eval-seed")
def eval_seed(
    n: int = typer.Option(40, "--n", help="抽样职位数(按公司均衡)"),
    db: Path = typer.Option(Path("jobpilot.db"), "--db"),
):
    """从已采集职位中抽样建立评测集."""
    from jobpilot.eval.dataset import seed_dataset
    from jobpilot.storage.db import Storage

    picked = seed_dataset(Storage.open(db), n)
    table = Table(title=f"评测集抽样:{len(picked)} 条")
    table.add_column("公司")
    table.add_column("职位")
    table.add_column("job_id")
    for p in picked:
        table.add_row(p["company"], p["title"][:44], p["job_id"])
    console.print(table)
    console.print(
        "[dim]下一步:jobpilot eval-annotate --job-id <id> --score <0-100> 逐条人工打分[/]"
    )


@app.command("eval-annotate")
def eval_annotate(
    job_id: str = typer.Option(..., "--job-id"),
    score: float = typer.Option(..., "--score", min=0, max=100, help="人工综合分 0-100"),
    annotator: str = typer.Option("human", "--annotator"),
    db: Path = typer.Option(Path("jobpilot.db"), "--db"),
):
    """记录一条人工标注(可与模型分对照算一致性)."""
    from jobpilot.eval.dataset import record_annotation
    from jobpilot.storage.db import Storage

    record_annotation(Storage.open(db), job_id, score, annotator)
    console.print(f"[green]已记录[/] {job_id} = {score}({annotator})")


@app.command("eval-run")
def eval_run(
    db: Path = typer.Option(Path("jobpilot.db"), "--db"),
    annotator: str = typer.Option(None, "--annotator", help="只统计该标注人"),
    out: Path = typer.Option(Path("docs/eval-report.md"), "--out"),
    top_k: int = typer.Option(3, "--top-k"),
    fake: bool = typer.Option(False, "--fake"),
):
    """补齐当前 rubric 评分 → 计算一致性指标 → 生成评测报告."""
    from jobpilot.config import GatewayConfig
    from jobpilot.eval.run import EvalError, run_eval
    from jobpilot.models.profile import load_profile
    from jobpilot.storage.db import Storage

    storage = Storage.open(db)
    cfg = GatewayConfig()
    if fake:
        cfg = cfg.model_copy(update={"model": "fake-model"})
        from jobpilot.testing import FakeGateway

        gw = FakeGateway(cfg, storage)
    else:
        from jobpilot.llm_gateway.gateway import LLMGateway

        gw = LLMGateway(cfg, storage)
    try:
        metrics = run_eval(
            storage,
            gw,
            load_profile(
                Path("profile.example.yaml")
                if not Path("profile.yaml").exists()
                else "profile.yaml"
            ),
            annotator=annotator,
            out_path=out,
            top_k=top_k,
        )
    except EvalError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
    console.print(
        f"[bold]n={metrics['n']} | Spearman={metrics['spearman']} | MAE={metrics['mae']}"
        f" | Top-{top_k} 重合={metrics['topk_overlap']}[/]"
    )
    console.print(f"[green]评测报告:[/]{out}")


def main() -> None:
    app()
