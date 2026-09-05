"""定时监控:错峰跑批 + 增量评分 + 高分推送 + 预算巡检.

排程设计(Asia/Shanghai):
- 周五 21:00 周全量(智谱非高峰积分半价窗口,周末全天同价)
- 每日 07:30 增量:采集 → 清洗 → 仅评新职位 → 高分即时推送
- 每日 08:00 预算巡检:超限即停跑并告警
"""

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from jobpilot.notify import compose_alert_message, send_notification
from jobpilot.pipeline import clean_pending, collect_all, run_report, score_pending

logger = logging.getLogger(__name__)

TIMEZONE = "Asia/Shanghai"


def high_score_alerts(storage, threshold: int = 75) -> list[dict]:
    """最近 24 小时内评分且达到阈值的职位(增量推送的 diff 检测,时区免疫)."""
    rows = storage.conn.execute(
        """SELECT j.company AS company, j.title AS title, j.url AS url, s.overall AS overall
           FROM jobs j JOIN scores s ON s.job_id = j.id
           WHERE s.overall >= ? AND s.created_at >= datetime('now', '-1 day')
           ORDER BY s.overall DESC""",
        (threshold,),
    ).fetchall()
    return [dict(r) for r in rows]


def daily_incremental(
    storage,
    profile,
    sources,
    gateway,
    *,
    notify_url: str = "",
    threshold: int = 75,
    limit: int | None = None,
) -> dict:
    """每日增量:采集 → 清洗 → 评新职位 → 高分推送."""
    crawl = asyncio.run(collect_all(storage, sources))
    cleaned = clean_pending(storage)
    scored = score_pending(storage, profile, gateway, limit=limit)
    alerts = high_score_alerts(storage, threshold)
    if alerts:
        send_notification(compose_alert_message(alerts, threshold=threshold), notify_url=notify_url)
    summary = {
        "new_jobs": sum(v for v in crawl.values() if v > 0),
        "cleaned": cleaned,
        "scored": scored,
        "alerts": len(alerts),
        "skipped_sources": [k for k, v in crawl.items() if v < 0],
    }
    logger.info("每日增量完成:%s", summary)
    return summary


def weekly_job(
    storage, profile, sources, gateway, *, out_dir="docs/reports", db_path="jobpilot.db"
) -> dict:
    """周全量:无人值守模式走确定性流水线(不启用 crew 推理),产出周报."""
    report = asyncio.run(
        run_report(
            storage,
            profile,
            sources,
            gateway=gateway,
            use_crew=False,
            out_dir=out_dir,
            db_path=db_path,
        )
    )
    logger.info("周全量完成:%s", report)
    return {"report": str(report)}


def budget_patrol(storage, gateway, *, notify_url: str = "") -> dict:
    """预算巡检:超限即停跑并告警."""
    from jobpilot.llm_gateway.exceptions import BudgetExceeded

    try:
        gateway._budget_check()
        return {"over_budget": False, "month_cost": storage.usage.month_cost()}
    except BudgetExceeded as e:
        send_notification(f"⚠️ OfferRadar 预算告警:\n{e}", notify_url=notify_url)
        return {"over_budget": True, "month_cost": storage.usage.month_cost()}


def build_scheduler(
    storage, profile, sources, gateway, *, notify_url: str = ""
) -> BackgroundScheduler:
    """注册三个定时任务;调用方自行 start()。任务异常被 APScheduler 捕获记日志."""
    from jobpilot.config import GatewayConfig

    cfg: GatewayConfig = gateway.cfg
    threshold = cfg.alert_threshold

    sched = BackgroundScheduler(timezone=TIMEZONE)
    sched.add_job(
        lambda: weekly_job(storage, profile, sources, gateway),
        "cron",
        day_of_week="fri",
        hour=21,
        minute=0,
        id="weekly-full",
    )
    sched.add_job(
        lambda: daily_incremental(
            storage, profile, sources, gateway, notify_url=notify_url, threshold=threshold
        ),
        "cron",
        hour=7,
        minute=30,
        id="daily-incremental",
    )
    sched.add_job(
        lambda: budget_patrol(storage, gateway, notify_url=notify_url),
        "cron",
        hour=8,
        minute=0,
        id="budget-patrol",
    )
    return sched
