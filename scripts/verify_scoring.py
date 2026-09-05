"""小批量评分质量验证(M3 评测台的先行版)。

从已采集职位中选一组"预期相关"与"预期不相关"的职位,用真实模型评分,
自动做三项质量检查:
1. 反幻觉:每条 evidence.quote 必须逐字出现在清洗后的 JD 文本中;
2. 区分度:两组职位的 overall 必须拉开(relevant 均值应显著高于 irrelevant);
3. 成本:记录本次真实 token 费用(来自网关计量表)。

用法:
  python scripts/verify_scoring.py --per-side 3            # 真实评分
  python scripts/verify_scoring.py --per-side 3 --fake     # 离线验证工具本身
结果:控制台表格 + docs/eval/score-sample.json
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from jobpilot.agents.matcher import score_and_store
from jobpilot.collectors.clean import clean_jd
from jobpilot.config import GatewayConfig
from jobpilot.storage.db import Storage

console = Console()

RELEVANT_PATTERNS = (
    "python",
    "backend",
    "data engineer",
    "site reliability",
    "software engineer",
    "infrastructure",
    "platform engineer",
)
IRRELEVANT_PATTERNS = (
    "recruit",
    "legal",
    "marketing",
    "sales",
    "people operations",
    "workplace",
    "communications",
    "account executive",
)
# 区分度测试应优先用学生真正会投的岗位(实习/校招),否则"资深岗 vs 学生"会压扁分数
JUNIOR_MARKERS = (
    "intern",
    "university",
    "new grad",
    "early career",
    "campus",
    "student",
)


def pick_sample(
    storage: Storage, patterns: tuple[str, ...], n: int, junior_only: bool = False
) -> list:
    """相关组优先抽实习/校招岗。

    注意用词边界匹配:LIKE '%intern%' 会误命中 'Engine Internals'。
    """
    import re

    where = " OR ".join(["lower(title) LIKE ?"] * len(patterns))
    candidates = storage.conn.execute(
        f"SELECT id, company, title FROM jobs WHERE {where} ORDER BY title LIMIT 200",
        [f"%{p}%" for p in patterns],
    ).fetchall()
    if not junior_only:
        return candidates[:n]
    junior = [
        r
        for r in candidates
        if any(re.search(rf"\b{m}\b", r["title"].lower()) for m in JUNIOR_MARKERS)
    ]
    return (junior or candidates)[:n]


def prepare(storage: Storage, job_id: str) -> str:
    """重置状态并清洗单条职位,返回清洗后文本."""
    job = storage.jobs.get(job_id)
    clean_md = clean_jd(job.description_md)
    storage.jobs.set_clean_md(job_id, clean_md)
    storage.jobs.update_status(job_id, "parsed")
    return clean_md


def check_evidence(score, clean_md: str) -> list[str]:
    """返回未逐字命中 JD 原文的证据引用(幻觉信号)."""
    from jobpilot.agents.matcher import canonical_text

    canonical_md = canonical_text(clean_md)
    bad = []
    for dim, ds in score.dims.items():
        for ev in ds.evidence:
            if canonical_text(ev.quote) not in canonical_md:
                bad.append(f"{dim}: {ev.quote[:40]}…")
    return bad


def main(
    per_side: int = typer.Option(3, "--per-side", help="每组抽取职位数"),
    db: str = typer.Option("jobpilot.db", "--db"),
    fake: bool = typer.Option(False, "--fake", help="用离线假网关验证工具本身"),
):
    storage = Storage.open(Path(db))
    cfg = GatewayConfig()
    if fake:
        cfg = cfg.model_copy(update={"model": "fake-model"})
        from jobpilot.testing import FakeGateway

        gw = FakeGateway(cfg, storage)
    else:
        if not cfg.api_key.get_secret_value():
            console.print("[red]未配置 ZHIPU_API_KEY:复制 .env.example 为 .env 并填入密钥[/]")
            raise typer.Exit(1)
        from jobpilot.llm_gateway.gateway import LLMGateway

        gw = LLMGateway(cfg, storage)

    sample = [
        (r, "relevant") for r in pick_sample(storage, RELEVANT_PATTERNS, per_side, junior_only=True)
    ] + [(r, "irrelevant") for r in pick_sample(storage, IRRELEVANT_PATTERNS, per_side)]
    if not sample:
        console.print("[red]库中无职位:先跑 jobpilot report --fake 完成一次采集[/]")
        raise typer.Exit(1)

    cost_before = storage.usage.month_cost()
    results, elapsed = [], 0.0
    for row, expected in sample:
        clean_md = prepare(storage, row["id"])
        start = time.perf_counter()
        try:
            score = score_and_store(gw, storage, _profile(), clean_md, job_id=row["id"])
        except Exception as e:  # noqa: BLE001 - 单条失败即中止,人工查看原因
            console.print(f"[red]评分失败({row['title']}):{type(e).__name__}: {e}[/]")
            raise typer.Exit(2)
        elapsed += time.perf_counter() - start
        storage.jobs.update_status(row["id"], "scored")
        results.append(
            {
                "job_id": row["id"],
                "company": row["company"],
                "title": row["title"],
                "expected": expected,
                "overall": score.overall,
                "dims": {k: v.score for k, v in score.dims.items()},
                "confidence": score.confidence,
                "summary": score.summary,
                "evidence_violations": check_evidence(score, clean_md),
            }
        )

    cost = storage.usage.month_cost() - cost_before
    rel = [r["overall"] for r in results if r["expected"] == "relevant"]
    irr = [r["overall"] for r in results if r["expected"] == "irrelevant"]
    violations = [r for r in results if r["evidence_violations"]]

    table = Table(title=f"评分质量抽查(model={cfg.model}, {len(results)} 条)")
    table.add_column("预期")
    table.add_column("公司")
    table.add_column("职位")
    table.add_column("overall", justify="right")
    table.add_column("置信度", justify="right")
    table.add_column("证据逐字命中", justify="center")
    for r in results:
        table.add_row(
            r["expected"],
            r["company"],
            r["title"][:34],
            f"{r['overall']}",
            f"{r['confidence']:.2f}",
            "✓" if not r["evidence_violations"] else "✗ " + ";".join(r["evidence_violations"])[:40],
        )
    console.print(table)
    summary = {
        "model": cfg.model,
        "n": len(results),
        "elapsed_s": round(elapsed, 1),
        "cost_cny": round(cost, 4),
        "relevant_mean": round(sum(rel) / len(rel), 1) if rel else None,
        "irrelevant_mean": round(sum(irr) / len(irr), 1) if irr else None,
        "evidence_violation_jobs": len(violations),
        "generated_at": datetime.now(UTC).isoformat(),
        "results": results,
    }
    out = Path("docs/eval/score-sample.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(
        f"相关组均值 {summary['relevant_mean']} vs 不相关组均值 {summary['irrelevant_mean']}"
        f" | 证据违规 {len(violations)} 条 | 成本 ¥{summary['cost_cny']} | 耗时 {summary['elapsed_s']}s"
    )
    console.print(f"[dim]明细已写入 {out}[/]")


def _profile():
    """加载正式简历 profile(评分对象)."""
    from jobpilot.models.profile import load_profile

    path = Path("profile.yaml")
    if not path.exists():
        path = Path("profile.example.yaml")
    return load_profile(path)


if __name__ == "__main__":
    typer.run(main)
