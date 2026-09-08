"""设置页面:API Key、模型、预算配置."""

import os
from pathlib import Path

import streamlit as st

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
    st.title("⚙️ 系统设置")
    st.info("配置 API Key 和系统参数，配置完成后即可使用所有功能。")

    # 加载现有配置
    config = load_env()

    # API 配置
    st.header("🔑 API 配置")

    col1, col2 = st.columns(2)

    with col1:
        api_key = st.text_input(
            "API Key",
            value=config.get("ZHIPU_API_KEY", ""),
            type="password",
            help="智谱 AI 或其他 OpenAI 兼容端点的 API Key",
            placeholder="输入你的 API Key...",
        )

    with col2:
        base_url = st.text_input(
            "API 地址",
            value=config.get("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
            help="OpenAI 兼容端点的地址",
        )

    col1, col2 = st.columns(2)

    with col1:
        model = st.selectbox(
            "模型",
            ["glm-5.3-flash", "glm-4-flash", "glm-4", "mimo-v2.5-pro"],
            index=0,
            help="选择使用的 AI 模型",
        )

    with col2:
        budget = st.number_input(
            "月度预算（元）",
            min_value=0.0,
            max_value=1000.0,
            value=float(config.get("JOBPLOT_MONTHLY_BUDGET_CNY", "30")),
            help="每月 API 调用费用上限",
        )

    # 通知配置
    st.header("📧 通知配置（可选）")

    col1, col2 = st.columns(2)

    with col1:
        notify_enabled = st.checkbox(
            "启用邮件通知",
            value=config.get("ALERT_EMAIL_ENABLED", "").lower() == "true",
        )

    with col2:
        if notify_enabled:
            smtp_host = st.text_input(
                "SMTP 服务器",
                value=config.get("ALERT_SMTP_HOST", "smtp.gmail.com"),
            )
        else:
            smtp_host = ""

    if notify_enabled:
        col1, col2, col3 = st.columns(3)

        with col1:
            smtp_port = st.number_input(
                "端口",
                value=int(config.get("ALERT_SMTP_PORT", "587")),
            )

        with col2:
            smtp_user = st.text_input(
                "邮箱账号",
                value=config.get("ALERT_SMTP_USER", ""),
                placeholder="your@email.com",
            )

        with col3:
            smtp_pass = st.text_input(
                "邮箱密码",
                value=config.get("ALERT_SMTP_PASS", ""),
                type="password",
                placeholder="应用专用密码",
            )

        recipients = st.text_input(
            "收件人邮箱",
            value=config.get("ALERT_RECIPIENTS", ""),
            placeholder="recipient@email.com（多个用逗号分隔）",
        )

    # 保存配置
    st.divider()

    if st.button("💾 保存配置", type="primary", use_container_width=True):
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
        st.success("✅ 配置已保存！请刷新页面使配置生效。")

    # 配置状态检查
    st.divider()
    st.header("📋 配置状态")

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
