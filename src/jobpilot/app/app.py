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
    # 语言切换
    from i18n import t, set_language, get_language

    lang_options = {"中文": "zh", "English": "en"}
    current_lang = "中文" if get_language() == "zh" else "English"
    selected_lang = st.selectbox(
        "🌐 Language",
        list(lang_options.keys()),
        index=list(lang_options.keys()).index(current_lang),
        label_visibility="collapsed",
    )
    if lang_options[selected_lang] != get_language():
        set_language(lang_options[selected_lang])
        st.rerun()

    st.image("https://img.icons8.com/color/96/target.png", width=60)
    st.title(t("app_title"))
    st.caption(t("app_subtitle"))

    st.divider()

    # 导航菜单
    page = st.radio(
        t("navigation"),
        [
            t("overview"),
            t("settings"),
            t("profile"),
            t("scoring"),
            t("companies"),
            t("collection"),
            t("jobs"),
            t("monitoring"),
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
            st.metric(t("collected"), job_count)
            st.metric(t("scored"), score_count)
        except Exception:
            pass

    st.divider()
    st.caption("v1.0 | AI Job Search Assistant")

# 路由到对应页面（使用语言无关的 key）
from i18n import t

if page == t("overview"):
    from pages import overview
    overview.render()

elif page == t("settings"):
    from pages import settings
    settings.render()

elif page == t("profile"):
    from pages import profile
    profile.render()

elif page == t("scoring"):
    from pages import scoring
    scoring.render()

elif page == t("companies"):
    from pages import companies
    companies.render()

elif page == t("collection"):
    from pages import collection
    collection.render()

elif page == t("jobs"):
    from pages import jobs
    jobs.render()

elif page == t("monitoring"):
    from pages import monitoring
    monitoring.render()
