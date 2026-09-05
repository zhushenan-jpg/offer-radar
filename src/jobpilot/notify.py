"""通知推送:apprise 统一封装(邮件/webhook/IM 100+ 渠道)。

未配置通知渠道时静默降级为日志输出——监控流水线永不因通知失败而中断。
"""

import logging

logger = logging.getLogger(__name__)


def send_notification(
    message: str, *, title: str = "OfferRadar 机会雷达", notify_url: str = ""
) -> bool:
    """经 apprise 推送一条通知;无渠道或失败返回 False(不抛异常)."""
    if not notify_url:
        logger.info("未配置通知渠道,消息仅记录:%s", message[:200])
        return False
    try:
        import apprise

        ap = apprise.Apprise()
        if not ap.add(notify_url):
            logger.warning("通知渠道无法解析:%s", notify_url.split("://")[0])
            return False
        return bool(ap.notify(body=message, title=title))
    except Exception as e:  # noqa: BLE001 - 通知是旁路,失败绝不影响主流程
        logger.warning("通知发送失败:%s", e)
        return False


def compose_alert_message(alerts: list[dict], *, threshold: int) -> str:
    """高分职位告警消息(纯文本,适配邮件与 IM 渠道)."""
    lines = [f"发现 {len(alerts)} 条高分职位(≥{threshold} 分):", ""]
    for a in alerts:
        lines.append(
            f"- {a['company']} — {a['title']}({a['overall']}/100){' ' + a['url'] if a.get('url') else ''}"
        )
    return "\n".join(lines)
