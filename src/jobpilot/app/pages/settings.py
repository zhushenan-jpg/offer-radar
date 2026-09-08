"""设置页面:API Key、模型、预算配置."""

import os
import sys
from pathlib import Path

import streamlit as st

# 添加 i18n 模块路径
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from i18n import t

ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


def load_env() -> dict:
    """加载 .env 文件."""
    config = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
    return config


def save_env(config: dict) -> None:
    """保存配置到 .env 文件."""
    lines = []
    for key, value in config.items():
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render():
    """渲染设置页面."""
    st.title(t("settings_title"))
    st.info(t("settings_info"))

    # 加载现有配置
    config = load_env()

    # API 配置
    st.header(t("api_config"))

    col1, col2 = st.columns(2)

    with col1:
        api_key = st.text_input(
            t("api_key"),
            value=config.get("ZHIPU_API_KEY", ""),
            type="password",
            help=t("api_key_help"),
            placeholder=t("api_key_placeholder"),
        )

    with col2:
        base_url = st.text_input(
            t("api_url"),
            value=config.get("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
            help=t("api_url_help"),
        )

    col1, col2 = st.columns(2)

    with col1:
        model = st.selectbox(
            t("model"),
            ["glm-5.3-flash", "glm-4-flash", "glm-4", "mimo-v2.5-pro"],
            index=0,
            help=t("model_help"),
        )

    with col2:
        budget = st.number_input(
            t("budget"),
            min_value=0.0,
            max_value=1000.0,
            value=float(config.get("JOBPLOT_MONTHLY_BUDGET_CNY", "30")),
            help=t("budget_help"),
        )

    # 通知配置
    st.header(t("notification_config"))

    col1, col2 = st.columns(2)

    with col1:
        notify_enabled = st.checkbox(
            t("enable_email"),
            value=config.get("ALERT_EMAIL_ENABLED", "").lower() == "true",
        )

    with col2:
        if notify_enabled:
            smtp_host = st.text_input(
                t("smtp_server"),
                value=config.get("ALERT_SMTP_HOST", "smtp.gmail.com"),
            )
        else:
            smtp_host = ""

    if notify_enabled:
        col1, col2, col3 = st.columns(3)

        with col1:
            smtp_port = st.number_input(
                t("smtp_port"),
                value=int(config.get("ALERT_SMTP_PORT", "587")),
            )

        with col2:
            smtp_user = st.text_input(
                t("email_account"),
                value=config.get("ALERT_SMTP_USER", ""),
                placeholder="your@email.com",
            )

        with col3:
            smtp_pass = st.text_input(
                t("email_password"),
                value=config.get("ALERT_SMTP_PASS", ""),
                type="password",
                placeholder="App password",
            )

        recipients = st.text_input(
            t("recipients"),
            value=config.get("ALERT_RECIPIENTS", ""),
            placeholder="recipient@email.com",
        )

    # 保存配置
    st.divider()

    if st.button(t("save_config"), type="primary", use_container_width=True):
        new_config = {
            "ZHIPU_API_KEY": api_key,
            "OPENAI_BASE_URL": base_url,
            "JOBPLOT_MODEL": model,
            "JOBPLOT_MONTHLY_BUDGET_CNY": str(budget),
        }

        if notify_enabled:
            new_config["ALERT_EMAIL_ENABLED"] = "true"
            new_config["ALERT_SMTP_HOST"] = smtp_host
            new_config["ALERT_SMTP_PORT"] = str(smtp_port)
            new_config["ALERT_SMTP_USER"] = smtp_user
            new_config["ALERT_SMTP_PASS"] = smtp_pass
            new_config["ALERT_RECIPIENTS"] = recipients
        else:
            new_config["ALERT_EMAIL_ENABLED"] = "false"

        save_env(new_config)
        st.success(t("config_saved"))

    # 配置状态检查
    st.divider()
    st.header(t("config_status_title"))

    col1, col2, col3 = st.columns(3)

    with col1:
        if api_key:
            st.success("✅ API Key 已配置")
        else:
            st.error("❌ API Key 未配置")

    with col2:
        if base_url:
            st.success("✅ API 地址已配置")
        else:
            st.warning("⚠️ 使用默认地址")

    with col3:
        if budget > 0:
            st.success(f"✅ 预算: ¥{budget}/月")
        else:
            st.warning("⚠️ 未设置预算")
