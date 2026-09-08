"""概览页面:系统状态总览."""

import os
import sys
from pathlib import Path

import streamlit as st

_SRC = Path(__file__).resolve().parents[3]
_APP_DIR = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from i18n import t


def render():
    """渲染概览页面."""
    st.title(t("overview_title"))
    st.info(t("welcome_msg"))

    # 检查配置状态
    from pathlib import Path

    env_file = Path(__file__).resolve().parents[4] / ".env"
    profile_file = Path(__file__).resolve().parents[4] / "profile.yaml"
    sources_file = Path(__file__).resolve().parents[4] / "sources.yaml"
    db_file = Path(__file__).resolve().parents[4] / "jobpilot.db"

    # 配置状态
    st.header(t("config_status"))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if env_file.exists():
            try:
                from jobpilot.config import GatewayConfig
                config = GatewayConfig()
                if config.api_key.get_secret_value():
                    st.success("✅ API Key")
                else:
                    st.error("❌ API Key 未配置")
            except Exception:
                st.error("❌ API Key 配置错误")
        else:
            st.error("❌ 未配置")

    with col2:
        if profile_file.exists():
            st.success("✅ 个人简历")
        else:
            st.error("❌ 未配置")

    with col3:
        if sources_file.exists():
            import yaml
            sources = yaml.safe_load(sources_file.read_text(encoding="utf-8")) or []
            st.success(f"✅ {len(sources)} 家公司")
        else:
            st.error("❌ 未配置")

    with col4:
        if db_file.exists():
            import sqlite3
            conn = sqlite3.connect(db_file)
            try:
                job_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
                score_count = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
                st.success(f"✅ {score_count} 条评分")
            except Exception:
                st.warning("⚠️ 数据库为空")
            finally:
                conn.close()
        else:
            st.warning("⚠️ 暂无数据")

    # 快速开始
    st.header(t("quick_start"))

    st.markdown(f"""
    1. **{t("settings")}** → {t("settings_title")}
    2. **{t("profile")}** → {t("profile_title")}
    3. **{t("companies")}** → {t("companies_title")}
    4. **{t("scoring")}** → {t("scoring_title")}
    5. **{t("jobs")}** → {t("jobs_title")}
    """)

    # 功能介绍
    st.header("📖 功能介绍")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 智能评分")
        st.write("基于 AI 的多维度匹配评分，帮你快速判断职位适合度")

        st.subheader("🔍 证据链")
        st.write("自动提取简历中的可验证声明，与 JD 要求进行匹配")

        st.subheader("⚠️ 差距分析")
        st.write("识别简历与职位要求的差距，给出具体改进建议")

    with col2:
        st.subheader("🏢 公司监控")
        st.write("持续监控目标公司的职位发布，第一时间获取新机会")

        st.subheader("📈 成本控制")
        st.write("精确计量 API 调用成本，支持设置月度预算上限")

        st.subheader("📧 通知推送")
        st.write("高分职位自动推送，不错过任何好机会")

    # 系统信息
    st.divider()
    st.header("ℹ️ 系统信息")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**版本**: v1.0")
        st.write("**技术栈**: Python + Streamlit + SQLite")

    with col2:
        st.write("**模型**: GLM-5.3-Flash")
        st.write("**数据源**: Greenhouse / Lever API")

    with col3:
        st.write("**开源协议**: MIT")
        st.write("**GitHub**: offer-radar")
