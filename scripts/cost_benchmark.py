"""成本优化量化实验:测量规则清洗的 token 节省和缓存命中效果.

用法: py scripts/cost_benchmark.py [--db jobpilot.db] [--limit 50]

产出:
1. 规则清洗前后的 token 对比（预期降幅 30%+）
2. 缓存命中率与二次运行成本降幅（预期 80%+）
3. 结果写入 docs/cost-benchmark.md
"""

import argparse
import json
import sys
from pathlib import Path

# 添加项目路径
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数(中文约 1.5 字/token,英文约 4 字符/token)."""
    import re
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = len(text) - chinese
    return int(chinese / 1.5 + other / 4)


def run_benchmark(db_path: Path, limit: int = 50) -> dict:
    """运行成本基准测试."""
    from jobpilot.collectors.clean import clean_jd_text
    from jobpilot.storage.db import Storage

    storage = Storage.open(db_path)

    # 获取已评分职位
    rows = storage.jobs.scored_with_scores()
    if not rows:
        print("没有已评分的职位数据，请先运行采集和评分。")
        return {}

    rows = rows[:limit]
    results = []

    for row in rows:
        job_id = row["job_id"]
        job = storage.jobs.get(job_id)
        if not job or not job.description_md:
            continue

        raw_text = job.description_md
        clean_text = clean_jd_text(raw_text)

        raw_tokens = estimate_tokens(raw_text)
        clean_tokens = estimate_tokens(clean_text)
        saved = raw_tokens - clean_tokens
        pct = (saved / raw_tokens * 100) if raw_tokens > 0 else 0

        results.append({
            "company": row["company"],
            "title": row["title"],
            "raw_tokens": raw_tokens,
            "clean_tokens": clean_tokens,
            "saved_tokens": saved,
            "saved_pct": round(pct, 1),
        })

    # 缓存统计
    try:
        cache_stats = storage.conn.execute(
            "SELECT COUNT(*) as total, SUM(cache_hit) as hits FROM usage"
        ).fetchone()
        total_calls = cache_stats[0] if cache_stats else 0
        cache_hits = cache_stats[1] or 0 if cache_stats else 0
        hit_rate = (cache_hits / total_calls * 100) if total_calls > 0 else 0
    except Exception:
        total_calls = 0
        cache_hits = 0
        hit_rate = 0

    # 费用统计
    try:
        cost_stats = storage.conn.execute(
            """SELECT
                SUM(CASE WHEN cache_hit=0 THEN cost_cny ELSE 0 END) as no_cache_cost,
                SUM(CASE WHEN cache_hit=1 THEN cost_cny ELSE 0 END) as cache_cost,
                SUM(cost_cny) as total_cost
            FROM usage"""
        ).fetchone()
        no_cache_cost = cost_stats[0] or 0 if cost_stats else 0
        cache_cost = cost_stats[1] or 0 if cost_stats else 0
        total_cost = cost_stats[2] or 0 if cost_stats else 0
    except Exception:
        no_cache_cost = 0
        cache_cost = 0
        total_cost = 0

    # 聚合统计
    if results:
        avg_raw = sum(r["raw_tokens"] for r in results) / len(results)
        avg_clean = sum(r["clean_tokens"] for r in results) / len(results)
        avg_saved_pct = sum(r["saved_pct"] for r in results) / len(results)
    else:
        avg_raw = avg_clean = avg_saved_pct = 0

    return {
        "samples": len(results),
        "avg_raw_tokens": round(avg_raw),
        "avg_clean_tokens": round(avg_clean),
        "avg_saved_pct": round(avg_saved_pct, 1),
        "total_api_calls": total_calls,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(hit_rate, 1),
        "no_cache_cost": round(no_cache_cost, 4),
        "cache_cost": round(cache_cost, 4),
        "total_cost": round(total_cost, 4),
        "cost_savings_pct": round(
            (1 - cache_cost / no_cache_cost) * 100 if no_cache_cost > 0 else 0, 1
        ),
        "details": results[:20],  # 前 20 条明细
    }


def write_report(benchmark: dict, out_path: Path) -> None:
    """写入 Markdown 报告."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# OfferRadar 成本优化基准报告",
        "",
        "## 1. 规则清洗 Token 节省",
        "",
        f"- 样本数: {benchmark['samples']}",
        f"- 平均原始 token: {benchmark['avg_raw_tokens']}",
        f"- 平均清洗后 token: {benchmark['avg_clean_tokens']}",
        f"- **平均 token 降幅: {benchmark['avg_saved_pct']}%**",
        "",
        "### 明细（前 20 条）",
        "",
        "| 公司 | 职位 | 原始 token | 清洗后 | 节省 |",
        "|---|---|---|---|---|",
    ]
    for d in benchmark.get("details", []):
        lines.append(
            f"| {d['company']} | {d['title'][:30]} | {d['raw_tokens']} "
            f"| {d['clean_tokens']} | {d['saved_pct']}% |"
        )

    lines += [
        "",
        "## 2. 缓存命中与成本节省",
        "",
        f"- 总 API 调用: {benchmark['total_api_calls']}",
        f"- 缓存命中: {benchmark['cache_hits']}",
        f"- **缓存命中率: {benchmark['cache_hit_rate']}%**",
        f"- 非缓存调用费用: ¥{benchmark['no_cache_cost']:.4f}",
        f"- 缓存调用费用: ¥{benchmark['cache_cost']:.4f}",
        f"- 总费用: ¥{benchmark['total_cost']:.4f}",
        f"- **二次运行成本降幅: {benchmark['cost_savings_pct']}%**",
        "",
        "## 说明",
        "",
        "- token 估算基于中英文字符比例粗算，实际值以 API 返回为准",
        "- 缓存命中时 token 计为 0，成本计为 0",
        "- 二次运行成本降幅 = 1 - 缓存费用/非缓存费用",
        "",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="OfferRadar 成本优化基准测试")
    parser.add_argument("--db", type=Path, default=Path("jobpilot.db"))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", type=Path, default=Path("docs/cost-benchmark.md"))
    args = parser.parse_args()

    if not args.db.exists():
        print(f"数据库不存在: {args.db}")
        sys.exit(1)

    print("运行成本优化基准测试...")
    benchmark = run_benchmark(args.db, args.limit)

    if benchmark:
        write_report(benchmark, args.out)
        print(f"\n结果:")
        print(f"  Token 降幅: {benchmark['avg_saved_pct']}%")
        print(f"  缓存命中率: {benchmark['cache_hit_rate']}%")
        print(f"  成本降幅: {benchmark['cost_savings_pct']}%")
        print(f"\n报告已写入: {args.out}")


if __name__ == "__main__":
    main()
