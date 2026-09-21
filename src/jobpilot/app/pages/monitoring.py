"""监控面板页面:展示系统运行状态和成本."""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

_SRC = Path(__file__).resolve().parents[3]
_APP_DIR = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from i18n import t


def render():
    """渲染监控面板页面."""
    st.title(t("monitoring_title"))
    st.info(t("monitoring_info"))

    # 加载数据
    db_path = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))
    if not db_path.exists():
        st.warning(t("no_monitor_data"))
        return

    import sqlite3
    conn = sqlite3.connect(db_path)

    # 概览
    st.header(t("overview_7days"))

    col1, col2, col3, col4 = st.columns(4)

    # Claim 提取统计
    try:
        row = conn.execute("""
            SELECT COUNT(*) FROM claim_extractions
            WHERE created_at > datetime('now', '-7 days')
        """).fetchone()
        claim_count = row[0] if row else 0
    except Exception:
        claim_count = 0

    # 简历补丁统计
    try:
        row = conn.execute("""
            SELECT COUNT(*) FROM resume_patches
            WHERE created_at > datetime('now', '-7 days')
        """).fetchone()
        patch_count = row[0] if row else 0
    except Exception:
        patch_count = 0

    # 面试速览统计
    try:
        row = conn.execute("""
            SELECT COUNT(*) FROM interview_briefs
            WHERE created_at > datetime('now', '-7 days')
        """).fetchone()
        brief_count = row[0] if row else 0
    except Exception:
        brief_count = 0

    # 总成本
    try:
        row = conn.execute("""
            SELECT SUM(cost_cny) FROM usage
            WHERE ts > datetime('now', '-7 days')
        """).fetchone()
        total_cost = row[0] if row else 0.0
    except Exception:
        total_cost = 0.0

    with col1:
        st.metric(t("claim_extraction"), claim_count)
    with col2:
        st.metric(t("resume_patches"), patch_count)
    with col3:
        st.metric(t("interview_briefs"), brief_count)
    with col4:
        st.metric(t("total_cost"), f"¥{total_cost:.2f}")

    # 成本分析
    st.header(t("cost_analysis"))

    try:
        rows = conn.execute("""
            SELECT module, SUM(cost_cny) as cost
            FROM usage
            WHERE ts > datetime('now', '-30 days')
            GROUP BY module
        """).fetchall()

        if rows:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader(t("module_costs"))
                for module, cost in rows:
                    st.write(f"- **{module}**: ¥{cost:.2f}")

            with col2:
                st.subheader(t("extended_costs"))
                st.write(f"- Claim: ¥{claim_count * 0.10:.2f}")
                st.write(f"- Gap Advisor: ¥{patch_count * 0.05:.2f}")
                st.write(f"- Interview Prep: ¥{brief_count * 0.10:.2f}")
        else:
            st.info(t("no_cost_data"))
    except Exception as e:
        st.error(t("cost_fetch_error").format(error=e))

    # 评分分布
    st.header(t("score_distribution"))

    try:
        rows = conn.execute("""
            SELECT ROUND(overall/10)*10 as score_range, COUNT(*) as count
            FROM scores
            GROUP BY score_range
            ORDER BY score_range
        """).fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=[t("score_range_label"), t("count_label")])
            st.bar_chart(df.set_index(t("score_range_label")))
        else:
            st.info(t("no_score_data"))
    except Exception as e:
        st.error(t("score_fetch_error").format(error=e))

    # 最近活动
    st.header(t("recent_activity"))

    try:
        rows = conn.execute("""
            SELECT job_id, resume_version, extraction_tokens, extraction_cost, created_at
            FROM claim_extractions
            ORDER BY created_at DESC
            LIMIT 10
        """).fetchall()

        if rows:
            df = pd.DataFrame(
                rows,
                columns=[t("col_job_id"), t("col_resume_version"), t("col_tokens"), t("col_cost"), t("col_created_at")],
            )
            st.dataframe(df, use_container_width=True)
        else:
            st.info(t("no_activity"))
    except Exception as e:
        st.error(t("activity_fetch_error").format(error=e))

    conn.close()

    # 页脚
    st.divider()
    st.caption(t("data_update_time").format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
