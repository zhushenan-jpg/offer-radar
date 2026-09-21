"""薪资分析页面:分析职位薪资范围."""

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
    """渲染薪资分析页面."""
    st.title(t("salary_title"))
    st.info(t("salary_info"))

    db_path = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))
    if not db_path.exists():
        st.warning(t("no_jobs_warning"))
        return

    from jobpilot.storage.db import Storage
    storage = Storage.open(db_path)

    # 获取已评分职位
    rows = storage.jobs.scored_with_scores()
    if not rows:
        st.warning(t("no_jobs_warning"))
        return

    # 从 JD 中提取薪资信息（简单的正则匹配）
    import re
    salary_data = []
    for row in rows:
        job = storage.jobs.get(row["job_id"])
        if not job or not job.description_md:
            continue

        text = job.description_md
        # 匹配常见薪资格式
        patterns = [
            r"(?:薪资|工资|salary|compensation)[：:\s]*(\d+)[kK-~～至到](\d+)[kK]",
            r"(\d+)[kK]\s*[-~～至到]\s*(\d+)[kK]",
            r"¥\s*(\d{4,6})\s*[-~～至到]\s*(\d{4,6})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                low, high = int(match.group(1)), int(match.group(2))
                if low < 1000:  # k 格式
                    low *= 1000
                    high *= 1000
                if 5000 <= low <= 200000 and 5000 <= high <= 200000:
                    salary_data.append({
                        "company": row["company"],
                        "title": row["title"],
                        "score": row["overall"],
                        "salary_low": low,
                        "salary_high": high,
                        "salary_avg": (low + high) / 2,
                    })
                break

    if not salary_data:
        st.info(t("no_salary_data"))
        return

    import pandas as pd

    # 统计概览
    st.subheader(t("salary_overview"))
    df = pd.DataFrame(salary_data)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("salary_avg_metric"), f"¥{df['salary_avg'].mean():,.0f}")
    with col2:
        st.metric(t("salary_max_metric"), f"¥{df['salary_high'].max():,.0f}")
    with col3:
        st.metric(t("salary_min_metric"), f"¥{df['salary_low'].min():,.0f}")

    st.divider()

    # 按公司分组
    st.subheader(t("salary_by_company"))
    company_salary = df.groupby("company").agg({
        "salary_avg": "mean",
        "salary_low": "min",
        "salary_high": "max",
        "score": "count",
    }).rename(columns={"score": t("jobs_count")}).sort_values("salary_avg", ascending=False)

    company_salary["salary_avg"] = company_salary["salary_avg"].apply(lambda x: f"¥{x:,.0f}")
    company_salary["salary_low"] = company_salary["salary_low"].apply(lambda x: f"¥{x:,.0f}")
    company_salary["salary_high"] = company_salary["salary_high"].apply(lambda x: f"¥{x:,.0f}")
    company_salary.columns = [t("salary_avg_label"), t("salary_low_label"), t("salary_high_label"), t("jobs_count")]

    st.dataframe(company_salary, use_container_width=True)

    st.divider()

    # 薪资 vs 评分散点数据
    st.subheader(t("salary_vs_score"))
    scatter_data = df[[t("col_company"), t("col_title"), "score", "salary_avg"]].copy()
    scatter_data.columns = [t("col_company"), t("col_title"), t("score"), t("salary_avg_label")]
    st.dataframe(scatter_data, use_container_width=True)

    # 薪资分布
    st.subheader(t("salary_distribution"))
    chart_data = df[["salary_avg"]].copy()
    chart_data.columns = [t("salary_avg_label")]
    st.bar_chart(chart_data)
