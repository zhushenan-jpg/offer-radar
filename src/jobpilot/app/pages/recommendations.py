"""职位推荐页面:基于历史评分推荐相似职位."""

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
    """渲染职位推荐页面."""
    st.title(t("recommendations_title"))
    st.info(t("recommendations_info"))

    db_path = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))
    if not db_path.exists():
        st.warning(t("no_jobs_warning"))
        return

    from jobpilot.storage.db import Storage
    storage = Storage.open(db_path)

    # 获取已评分职位
    scored = storage.jobs.scored_with_scores()
    if not scored:
        st.warning(t("no_jobs_warning"))
        return

    # 分析高分职位的特征
    high_scored = [r for r in scored if r["overall"] >= 60]
    if not high_scored:
        st.info(t("no_high_score_jobs"))
        return

    # 提取高频公司和技能
    from collections import Counter
    company_counts = Counter(r["company"] for r in high_scored)
    top_companies = company_counts.most_common(5)

    st.subheader(t("top_companies"))
    for company, count in top_companies:
        avg_score = sum(r["overall"] for r in high_scored if r["company"] == company) / count
        st.write(f"- **{company}**: {count} {t('jobs_count')}，{t('avg_score')} {avg_score:.1f}")

    st.divider()

    # 推荐未评分的职位（按公司和标题相似度）
    all_jobs = storage.jobs.ids_by_status("parsed") + storage.jobs.ids_by_status("new")
    scored_ids = {r["job_id"] for r in scored}

    unscored = []
    for jid in all_jobs:
        if jid not in scored_ids:
            job = storage.jobs.get(jid)
            if job:
                unscored.append(job)

    if not unscored:
        st.success(t("all_jobs_scored"))
        return

    # 简单推荐:优先推荐高分公司的未评分职位
    top_company_names = [c for c, _ in top_companies]
    recommended = []
    other = []
    for job in unscored:
        if job.company in top_company_names:
            recommended.append(job)
        else:
            other.append(job)

    recommended.extend(other[:20])  # 最多显示 20 条

    st.subheader(t("recommended_jobs"))
    st.write(t("recommendation_reason"))

    import pandas as pd
    df_data = []
    for job in recommended[:20]:
        df_data.append({
            t("col_company"): job.company,
            t("col_title"): job.title,
            t("col_location"): job.location or "-",
            t("recommend_reason"): t("high_score_company") if job.company in top_company_names else t("similar_position"),
        })
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True)
