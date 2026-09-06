"""OfferRadar 求职雷达面板(Streamlit).

本地运行:.venv/Scripts/streamlit run src/jobpilot/app/dashboard.py
数据源:环境变量 JOBPLOT_DB(默认 ./jobpilot.db);周报目录 JOBPLOT_REPORTS。
部署:Streamlit Community Cloud,主文件指向本文件,演示库见 scripts/export_demo_db.py。
"""

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from jobpilot.agents.prompts import RUBRIC_VERSION
from jobpilot.eval.metrics import compute_metrics
from jobpilot.storage.db import Storage


def _default_db() -> Path:
    """本地开发库优先;不存在或为空库(无 jobs 行)时回退到随仓库的演示库.

    空库回退是必需的:Storage.open 会自动建库,云端容器里上一次运行
    留下的空 jobpilot.db 会让"文件存在"判断失真.
    """
    local = Path("jobpilot.db")
    if local.exists():
        try:
            import sqlite3

            conn = sqlite3.connect(local)
            try:
                has_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] > 0
            finally:
                conn.close()
            if has_jobs:
                return local
        except sqlite3.Error:
            pass  # 空文件/非库文件:按不存在处理
    demo = Path("deploy/demo_jobpilot.db")
    return demo if demo.exists() else local


DB = Path(os.environ.get("JOBPLOT_DB") or _default_db())
REPORTS_DIR = Path(os.environ.get("JOBPLOT_REPORTS", "docs/reports"))


@st.cache_resource
def get_storage() -> Storage:
    return Storage.open(DB)


storage = get_storage()
st.set_page_config(page_title="OfferRadar 求职雷达", page_icon="🎯", layout="wide")
st.title("🎯 OfferRadar 求职雷达")
st.caption(f"数据库:{DB} · rubric {RUBRIC_VERSION}")

tab_over, tab_jobs, tab_review, tab_report, tab_eval = st.tabs(
    ["概览", "职位与评分", "待人工复核", "周报", "评测"]
)

rows = storage.jobs.scored_with_scores()

with tab_over:
    c1, c2, c3, c4 = st.columns(4)
    total_jobs = storage.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    companies = storage.conn.execute("SELECT COUNT(DISTINCT company) FROM jobs").fetchone()[0]
    cost = storage.usage.month_cost_by_module()
    c1.metric("已采集职位", total_jobs)
    c2.metric("已评分", len(rows))
    c3.metric("公司数", companies)
    c4.metric("本月成本", f"¥{sum(cost.values()):.2f}")
    if cost:
        st.dataframe(
            pd.DataFrame([{"模块": m, "费用(¥)": round(v, 4)} for m, v in cost.items()]),
            hide_index=True,
        )

with tab_jobs:
    if not rows:
        st.info("还没有评分数据:先跑 jobpilot report")
    else:
        df = pd.DataFrame(rows)
        col_a, col_b = st.columns([1, 3])
        company = col_a.selectbox("公司", ["全部"] + sorted(df["company"].unique().tolist()))
        keyword = col_b.text_input("标题关键词")
        view = df
        if company != "全部":
            view = view[view["company"] == company]
        if keyword:
            view = view[view["title"].str.contains(keyword, case=False, na=False)]
        if view.empty:
            st.info("没有匹配的职位:调整公司或关键词筛选")
        else:
            st.dataframe(
                view[["overall", "company", "title", "location", "confidence"]].head(50),
                hide_index=True,
                use_container_width=True,
            )
            choice = st.selectbox(
                "查看证据详情",
                view.head(50).apply(
                    lambda r: f"{r['company']} — {r['title']}({r['overall']})", axis=1
                ),
            )
            if choice:
                picked = view[
                    view.apply(lambda r: f"{r['company']} — {r['title']}({r['overall']})", axis=1)
                    == choice
                ].iloc[0]
                st.write(f"**{picked['summary']}**(置信度 {picked['confidence']:.2f})")
                for dim, d in picked["dims"].items():
                    quotes = "; ".join(f"「{e['quote']}」" for e in d["evidence"])
                    st.markdown(f"- **{dim}**:{d['score']}/10 — {quotes}")
                if picked.get("url"):
                    st.markdown(f"[职位原文]({picked['url']})")

with tab_review:
    review = [r for r in rows if r["review_status"] == "review"]
    annotator = st.text_input("标注人", value="human", key="annotator")
    if not review:
        st.info("暂无待复核职位(低置信度评分会出现在这里)")
    for r in review:
        with st.form(key=f"review-{r['job_id'] if 'job_id' in r else r['title']}"):
            st.write(
                f"**{r['company']} — {r['title']}** · 模型分 {r['overall']} · 置信度 {r['confidence']:.2f}"
            )
            human = st.number_input(
                "人工综合分", 0, 100, value=int(r["overall"]), key=f"n-{r['title']}"
            )
            if st.form_submit_button("提交标注"):
                jid = storage.conn.execute(
                    "SELECT job_id FROM scores WHERE overall=? ORDER BY id DESC LIMIT 1",
                    (r["overall"],),
                ).fetchone()[0]
                storage.annotations.add(jid, float(human), annotator)
                st.success(f"已记录 {jid[:8]}… = {human}")

with tab_report:
    reports = sorted(REPORTS_DIR.glob("*.md"), reverse=True) if REPORTS_DIR.exists() else []
    if not reports:
        st.info("还没有周报:先跑 jobpilot report")
    else:
        picked_report = st.selectbox("周报", reports, format_func=lambda p: p.name)
        st.markdown(picked_report.read_text(encoding="utf-8"))

with tab_eval:
    pairs = storage.annotations.pairs_with_predictions()
    if len(pairs) < 3:
        st.info(f"标注不足({len(pairs)} 条,至少 3 条):在「待人工复核」或 CLI eval-annotate 中打分")
    else:
        metrics = compute_metrics(pairs)
        m1, m2, m3 = st.columns(3)
        m1.metric("Spearman 相关", metrics["spearman"])
        m2.metric("MAE", metrics["mae"])
        m3.metric("Top-3 重合率", metrics["topk_overlap"])
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "公司": p["company"],
                        "职位": p["title"][:40],
                        "模型分": p["pred"],
                        "人工分": p["human"],
                        "差值": round(p["pred"] - p["human"], 1),
                    }
                    for p in pairs
                ]
            ),
            hide_index=True,
        )
