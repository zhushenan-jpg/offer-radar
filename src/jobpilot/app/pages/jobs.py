"""职位列表页面:展示已采集和已评分的职位."""

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def render():
    """渲染职位列表页面."""
    st.title("📋 职位列表")
    st.info("查看已采集和已评分的职位信息。")

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
        st.info("💡 暂无已评分的职位，请先进行评分。")
        return

    # 统计信息
    st.header("📊 统计概览")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总职位数", len(rows))
    with col2:
        companies = set(r["company"] for r in rows)
        st.metric("公司数", len(companies))
    with col3:
        avg_score = sum(r["overall"] for r in rows) / len(rows)
        st.metric("平均分", f"{avg_score:.1f}")

    # 筛选
    st.header("🔍 筛选")

    col1, col2 = st.columns([1, 3])

    with col1:
        companies_list = ["全部"] + sorted(companies)
        selected_company = st.selectbox("公司", companies_list)

    with col2:
        search_title = st.text_input("职位名称搜索", placeholder="输入关键词...")

    # 过滤数据
    filtered = rows
    if selected_company != "全部":
        filtered = [r for r in filtered if r["company"] == selected_company]
    if search_title:
        filtered = [r for r in filtered if search_title.lower() in r["title"].lower()]

    # 职位列表
    st.header(f"📋 职位列表 ({len(filtered)} 条)")

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
        st.header("📝 职位详情")

        options = [f"{r['company']} -- {r['title']} ({r['overall']})" for r in filtered]
        selected = st.selectbox("选择职位查看详情", options)

        if selected:
            idx = options.index(selected)
            job = filtered[idx]

            # 基本信息
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**公司**: {job['company']}")
                st.write(f"**职位**: {job['title']}")
                st.write(f"**地点**: {job.get('location', '未知')}")
            with col2:
                st.write(f"**综合评分**: {job['overall']}/100")
                st.write(f"**置信度**: {job['confidence']:.0%}")

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
