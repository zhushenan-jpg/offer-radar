"""设置页面:API Key、模型、预算配置."""

import os
import sys
from pathlib import Path

import streamlit as st

# 添加 i18n 模块路径
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from i18n import t, get_language

ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


def validate_api_key(base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    """验证 API Key 是否有效.

    通过调用 models.list() 接口验证 key 和 endpoint 的连通性.
    不消耗 token,超时设为 15 秒.

    Args:
        base_url: API 端点地址
        api_key: API 密钥
        model: 模型名称(此函数中未使用,保留供未来扩展)

    Returns:
        tuple[bool, str]: (是否有效, 错误信息). 有效时错误信息为空字符串.
    """
    if not api_key:
        return False, "API Key 为空"
    try:
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=15.0)
        # 尝试列出模型(轻量请求,不消耗 token)
        models = client.models.list()
        return True, ""
    except Exception as e:
        err = str(e)
        # 提取关键错误信息
        if "401" in err or "invalid" in err.lower() or "auth" in err.lower():
            return False, "API Key 无效或已过期"
        elif "403" in err or "forbidden" in err.lower():
            return False, "API Key 权限不足"
        elif "timeout" in err.lower() or "connect" in err.lower():
            return False, "无法连接到 API 服务器，请检查网络和地址"
        else:
            return False, f"验证失败: {err[:200]}"


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
        # 先验证 API Key 有效性
        with st.spinner(t("validating_api_key")):
            is_valid, err_msg = validate_api_key(base_url, api_key, model)

        if not is_valid:
            st.error(t("api_key_invalid").format(error=err_msg))
        else:
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
            st.success(t("api_key_status_ok"))
        else:
            st.error(t("api_key_status_missing"))

    with col2:
        if base_url:
            st.success(t("api_url_status_ok"))
        else:
            st.warning(t("api_url_status_default"))

    with col3:
        if budget > 0:
            st.success(t("budget_status_ok").format(budget=budget))
        else:
            st.warning(t("budget_status_missing"))
