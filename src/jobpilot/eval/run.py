"""评测运行:补齐当前 rubric 评分 → 指标计算 → Markdown 报告.

回归语义:rubric/prompt 变更后重跑 run_eval,版本化缓存键会让全部数据集
用新 rubric 重新评分(产生真实 API 成本),指标与上一版报告对比即回归。
"""

from pathlib import Path

from jobpilot.agents.prompts import RUBRIC_VERSION
from jobpilot.eval.metrics import compute_metrics


class EvalError(Exception):
    """评测前置条件不满足(数据集为空/标注不足)."""


def run_eval(
    storage,
    gateway,
    profile,
    *,
    annotator: str | None = None,
    out_path: Path | str = "docs/eval-report.md",
    top_k: int = 3,
) -> dict:
    job_ids = storage.eval_ds.all_ids()
    if not job_ids:
        raise EvalError("评测集为空:先运行 jobpilot eval-seed")

    # 1) 补齐当前 rubric 版本的模型评分(缓存命中则零成本)
    # 错误隔离:单条评分失败记入 failed,不中断整场评测
    from jobpilot.agents.matcher import score_and_store
    from jobpilot.llm_gateway.exceptions import BudgetExceeded

    rescored = 0
    failed: list[dict] = []
    for jid in job_ids:
        latest = storage.scores.latest_for_job(jid)
        if latest is None or latest["rubric_version"] != RUBRIC_VERSION:
            job = storage.jobs.get(jid)
            clean = storage.jobs.get_clean(jid) or job.description_md
            try:
                score_and_store(gateway, storage, profile, clean, job_id=jid)
            except BudgetExceeded:
                raise
            except Exception as e:  # noqa: BLE001 - 单条失败不影响其余评测
                failed.append(
                    {
                        "job_id": jid,
                        "company": job.company,
                        "title": job.title,
                        "error": f"{type(e).__name__}: {e}"[:160],
                    }
                )
            else:
                rescored += 1

    # 2) 取模型分 × 人工分配对(无分的失败职位自动被 JOIN 排除)
    pairs = storage.annotations.pairs_with_predictions(annotator)
    if len(pairs) < 3:
        raise EvalError(f"标注不足({len(pairs)} 条,至少 3 条):用 jobpilot eval-annotate 逐条打分")

    # 3) 指标 + 报告
    metrics = compute_metrics(pairs, top_k=top_k)
    metrics["failed"] = failed
    model_version = storage.conn.execute(
        "SELECT model_version FROM scores ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    _write_report(storage, metrics, out_path, model_version, rescored)
    return metrics


def _write_report(storage, metrics: dict, out_path, model_version: str, rescored: int) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    m_sp, m_mae = metrics["spearman"], metrics["mae"]
    k_overlap = metrics["topk_overlap"]
    lines = [
        "# OfferRadar 评测报告",
        "",
        f"- 样本:n={metrics['n']} | 本轮重评 {rescored} 条 | rubric {RUBRIC_VERSION} | model {model_version}",
        f"- **Spearman 相关:{m_sp}**(模型排序与人工排序的一致性)",
        f"- **MAE:{m_mae}**(平均绝对误差,百分制)",
        f"- **Top-3 重合率:{k_overlap}**",
        "",
        "## 逐条对照",
        "",
        "| 公司 | 职位 | 模型分 | 人工分 | 差值 |",
        "|---|---|---|---|---|",
    ]
    for p in metrics["pairs"]:
        diff = round(p["pred"] - p["human"], 1)
        lines.append(
            f"| {p['company']} | {p['title'][:36]} | {p['pred']} | {p['human']} | {diff:+} |"
        )
    lines += [
        "",
        "## 校准(按模型分位桶看人工分均值)",
        "",
        "| 模型分区间 | n | 模型均值 | 人工均值 |",
        "|---|---|---|---|",
    ]
    for b in metrics["calibration"]:
        lines.append(
            f"| {b['range']} | {b['n']} | {b['mean_pred'] if b['mean_pred'] is not None else '-'}"
            f" | {b['mean_human'] if b['mean_human'] is not None else '-'} |"
        )
    lines += [
        "",
        "## 说明与局限",
        "",
        f"- 本轮重评 {rescored} 条成功"
        + (f",{len(metrics['failed'])} 条失败(见下);" if metrics["failed"] else ";"),
        "- 样本量小,数字用于 prompt/rubric 迭代的相对比较,不是统计结论;",
        "- 人工标注存在主观性,多人标注取均值可降低方差(annotations 表按 annotator 区分);",
        "- 证据引用逐字校验(evidence_validator)在评分时已强制执行。",
        "",
    ]
    if metrics["failed"]:
        lines += ["## 评分失败明细", ""]
        for f in metrics["failed"]:
            lines.append(f"- {f['company']} — {f['title'][:40]}:`{f['error']}`")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
