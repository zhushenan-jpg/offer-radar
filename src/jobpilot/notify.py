"""通知推送:apprise 统一封装(邮件/webhook/IM 100+ 渠道)。

未配置通知渠道时静默降级为日志输出——监控流水线永不因通知失败而中断。
支持邮件告警通知。
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailAlertSender:
    """邮件告警发送器."""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        recipients: list[str] | None = None,
    ):
        self.smtp_host = smtp_host or os.environ.get("ALERT_SMTP_HOST", "")
        self.smtp_port = smtp_port or int(os.environ.get("ALERT_SMTP_PORT", "587"))
        self.username = username or os.environ.get("ALERT_SMTP_USER", "")
        self.password = password or os.environ.get("ALERT_SMTP_PASS", "")
        self.recipients = recipients or [
            r.strip()
            for r in os.environ.get("ALERT_RECIPIENTS", "").split(",")
            if r.strip()
        ]

    @property
    def is_configured(self) -> bool:
        """检查是否已配置."""
        return all([self.smtp_host, self.username, self.password, self.recipients])

    def send_alert(self, subject: str, message: str, severity: str = "warning") -> bool:
        """发送告警邮件."""
        if not self.is_configured:
            logger.info("邮件告警未配置，跳过发送: %s", subject)
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.username
            msg["To"] = ", ".join(self.recipients)
            msg["Subject"] = f"[OfferRadar {severity.upper()}] {subject}"

            body = f"""
            <html>
            <body>
                <h2>OfferRadar 告警通知</h2>
                <p><strong>严重程度：</strong>{severity}</p>
                <p><strong>告警内容：</strong>{message}</p>
                <p><strong>告警时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p><small>此邮件由 OfferRadar 监控系统自动发送</small></p>
            </body>
            </html>
            """

            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info("告警邮件已发送: %s", subject)
            return True

        except Exception as e:
            logger.warning("发送告警邮件失败: %s", e)
            return False


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
