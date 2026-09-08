"""职位列表页面:展示已采集和已评分的职位."""

import os
import sys
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
    """渲染职位列表页面."""
    st.title(t("jobs_title"))
    st.info(t("jobs_info"))

    # 加载数据
    db_path = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))
    if not db_path.exists():
        st.warning("⚠️ 暂无数据，请先采集职位。")
        return

    from jobpilot.storage.db import Storage
    storage = Storage.open(db_path)

    # 获取已评分职位
    rows = storage.jobs.scored_with_scores()

    if not rows:
        st.info(t("no_data"))
        return

    # 统计信息
    st.header(t("statistics"))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("total_jobs"), len(rows))
    with col2:
        companies = set(r["company"] for r in rows)
        st.metric(t("total_companies"), len(companies))
    with col3:
        avg_score = sum(r["overall"] for r in rows) / len(rows)
        st.metric(t("avg_score"), f"{avg_score:.1f}")

    # 筛选
    st.header(t("filter"))

    col1, col2 = st.columns([1, 3])

    with col1:
        companies_list = [t("all_companies")] + sorted(companies)
        selected_company = st.selectbox(t("company_filter"), companies_list)

    with col2:
        search_title = st.text_input(t("title_search"), placeholder="Enter keywords...")

    # 过滤数据
    filtered = rows
    if selected_company != t("all_companies"):
        filtered = [r for r in filtered if r["company"] == selected_company]
    if search_title:
        filtered = [r for r in filtered if search_title.lower() in r["title"].lower()]

    # 职位列表
    st.header(f"{t('job_list')} ({len(filtered)})")

    if filtered:
        # 转换为 DataFrame
        df_data = []
        for r in filtered:
            df_data.append({
                "分数": r["overall"],
                "公司": r["company"],
                "职位": r["title"],
                "地点": r.get("location", ""),
                "置信度": f"{r['confidence']:.0%}",
            })

        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)

        # 详情查看
        st.header(t("job_details"))

        options = [f"{r['company']} -- {r['title']} ({r['overall']})" for r in filtered]
        selected = st.selectbox(t("select_job"), options)

        if selected:
            idx = options.index(selected)
            job = filtered[idx]

            # 基本信息
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{t('company')}**: {job['company']}")
                st.write(f"**{t('title')}**: {job['title']}")
                st.write(f"**{t('location')}**: {job.get('location', 'Unknown')}")
            with col2:
                st.write(f"**{t('score')}**: {job['overall']}/100")
                st.write(f"**{t('confidence')}**: {job['confidence']:.0%}")

            # 维度评分
            st.subheader("维度评分")
            dims = job.get("dims", {})
            for dim, data in dims.items():
                st.write(f"**{dim}**: {data['score']}/10")
                for ev in data.get("evidence", []):
                    st.caption(f"  📝 {ev['quote']}")

            # 总结
            st.subheader("总结")
            st.write(job.get("summary", ""))

            # 链接
            if job.get("url"):
                st.link_button("🔗 查看原始职位", job["url"])
    else:
        st.info("没有找到匹配的职位。")
