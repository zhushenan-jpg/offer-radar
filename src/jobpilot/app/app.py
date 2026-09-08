"""OfferRadar 统一应用入口.

启动方式: streamlit run src/jobpilot/app/app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st

# 添加项目路径
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# 页面配置
st.set_page_config(
    page_title="OfferRadar 求职雷达",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 侧边栏导航
with st.sidebar:
    st.image("https://img.icons8.com/color/96/target.png", width=60)
    st.title("🎯 OfferRadar")
    st.caption("智能求职助手")

    st.divider()

    # 导航菜单
    page = st.radio(
        "导航",
        [
            "🏠 概览",
            "⚙️ 设置",
            "📝 我的简历",
            "📊 在线评分",
            "🏢 目标公司",
            "🔄 一键采集",
            "📋 职位列表",
            "📈 监控面板",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # 快速状态
    db_path = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            job_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            score_count = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
            conn.close()
            st.metric("已采集", job_count)
            st.metric("已评分", score_count)
        except Exception:
            pass

    st.divider()
    st.caption("v1.0 | 基于 AI 的求职助手")

# 路由到对应页面
if page == "🏠 概览":
    from pages import overview
    overview.render()

elif page == "⚙️ 设置":
    from pages import settings
    settings.render()

elif page == "📝 我的简历":
    from pages import profile
    profile.render()

elif page == "📊 在线评分":
    from pages import scoring
    scoring.render()

elif page == "🏢 目标公司":
    from pages import companies
    companies.render()

elif page == "🔄 一键采集":
    from pages import collection
    collection.render()

elif page == "📋 职位列表":
    from pages import jobs
    jobs.render()

elif page == "📈 监控面板":
    from pages import monitoring
    monitoring.render()
