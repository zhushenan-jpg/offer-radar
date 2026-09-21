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

from i18n import t, set_language, get_language

# 语言无关的页面 key 列表（路由用，不随语言变化）
PAGE_KEYS = [
    "overview", "settings", "profile", "scoring",
    "companies", "collection", "jobs", "monitoring", "annotation", "review",
    "resume_optimize", "interview_sim", "recommendations", "salary",
]

# 侧边栏导航
with st.sidebar:
    # 语言切换
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

    # 导航菜单：用翻译后的标签做显示，但通过 index 映射回语言无关的 key
    labels = [t(key) for key in PAGE_KEYS]
    # 恢复上次选中的页面（存的是 key，与语言无关）
    if "current_page" in st.session_state and st.session_state.current_page in PAGE_KEYS:
        default_index = PAGE_KEYS.index(st.session_state.current_page)
    else:
        default_index = 0
    selected_label = st.radio(
        t("navigation"),
        labels,
        index=default_index,
        label_visibility="collapsed",
    )
    # 将选中的标签映射回 key 并存入 session_state
    selected_key = PAGE_KEYS[labels.index(selected_label)]
    st.session_state.current_page = selected_key

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

# 路由到对应页面（使用语言无关的 key，不再依赖翻译文本）
page = st.session_state.get("current_page", "overview")

if page == "overview":
    from pages import overview
    overview.render()
elif page == "settings":
    from pages import settings
    settings.render()
elif page == "profile":
    from pages import profile
    profile.render()
elif page == "scoring":
    from pages import scoring
    scoring.render()
elif page == "companies":
    from pages import companies
    companies.render()
elif page == "collection":
    from pages import collection
    collection.render()
elif page == "jobs":
    from pages import jobs
    jobs.render()
elif page == "monitoring":
    from pages import monitoring
    monitoring.render()
elif page == "annotation":
    from pages import annotation
    annotation.render()
elif page == "review":
    from pages import review
    review.render()
elif page == "resume_optimize":
    from pages import resume_optimize
    resume_optimize.render()
elif page == "interview_sim":
    from pages import interview_sim
    interview_sim.render()
elif page == "recommendations":
    from pages import recommendations
    recommendations.render()
elif page == "salary":
    from pages import salary
    salary.render()
