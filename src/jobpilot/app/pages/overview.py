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
                    st.success(t("api_key_configured"))
                else:
                    st.error(t("api_key_not_configured"))
            except Exception:
                st.error(t("api_key_config_error"))
        else:
            st.error(t("not_configured"))

    with col2:
        if profile_file.exists():
            st.success(t("resume_configured"))
        else:
            st.error(t("not_configured"))

    with col3:
        if sources_file.exists():
            import yaml
            sources = yaml.safe_load(sources_file.read_text(encoding="utf-8")) or []
            st.success(t("companies_count").format(count=len(sources)))
        else:
            st.error(t("not_configured"))

    with col4:
        if db_file.exists():
            import sqlite3
            conn = sqlite3.connect(db_file)
            try:
                job_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
                score_count = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
                st.success(t("scores_count").format(count=score_count))
            except Exception:
                st.warning(t("db_empty"))
            finally:
                conn.close()
        else:
            st.warning(t("no_data_yet"))

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
    st.header(t("features_title"))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(t("smart_scoring_title"))
        st.write(t("smart_scoring_desc"))

        st.subheader(t("evidence_chain_title"))
        st.write(t("evidence_chain_desc"))

        st.subheader(t("gap_analysis_title"))
        st.write(t("gap_analysis_desc"))

    with col2:
        st.subheader(t("company_monitor_title"))
        st.write(t("company_monitor_desc"))

        st.subheader(t("cost_control_title"))
        st.write(t("cost_control_desc"))

        st.subheader(t("notification_push_title"))
        st.write(t("notification_push_desc"))

    # 系统信息
    st.divider()
    st.header(t("system_info_title"))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write(f"**{t('version_label')}**: v1.0")
        st.write(f"**{t('tech_stack_label')}**: Python + Streamlit + SQLite")

    with col2:
        st.write(f"**{t('model_label')}**: GLM-5.3-Flash")
        st.write(f"**{t('data_source_label')}**: Greenhouse / Lever API")

    with col3:
        st.write(f"**{t('license_label')}**: MIT")
        st.write("**GitHub**: offer-radar")
