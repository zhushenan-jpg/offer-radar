"""评测标注页面:可视化标注评测数据集."""

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
    """渲染评测标注页面."""
    st.title(t("annotation_title"))
    st.info(t("annotation_info"))

    db_path = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))
    if not db_path.exists():
        st.warning(t("no_jobs_warning"))
        return

    from jobpilot.storage.db import Storage
    storage = Storage.open(db_path)

    # 操作栏:抽样 + 统计
    col1, col2 = st.columns([1, 1])

    with col1:
        seed_n = st.number_input(
            t("seed_count"), min_value=10, max_value=200, value=50, step=10,
        )
        if st.button(t("seed_dataset_btn"), type="secondary"):
            from jobpilot.eval.dataset import seed_dataset
            picked = seed_dataset(storage, n=seed_n)
            if picked:
                st.success(t("seed_success").format(count=len(picked)))
                st.rerun()
            else:
                st.warning(t("no_jobs_warning"))

    # 统计概览
    eval_ids = storage.eval_ds.all_ids()
    if not eval_ids:
        st.warning(t("eval_empty_warning"))
        return

    annotator = st.text_input(t("annotator_name"), value="human", help=t("annotator_help"))

    pending = storage.annotations.pending_for_eval(annotator or None)
    pairs = storage.annotations.pairs_with_predictions(annotator or None)
    total = len(eval_ids)
    done = total - len(pending)

    # 进度条
    st.divider()
    progress = done / total if total > 0 else 0
    st.progress(progress, text=t("annotation_progress").format(done=done, total=total))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("total_eval_jobs"), total)
    with col2:
        st.metric(t("annotated_count"), done)
    with col3:
        st.metric(t("pending_count"), len(pending))

    # 标注区域
    st.divider()

    if not pending:
        st.success(t("all_annotated"))
        # 显示已标注的对照表
        if pairs:
            st.subheader(t("annotation_pairs"))
            import pandas as pd
            df_data = []
            for p in pairs:
                df_data.append({
                    t("col_company"): p["company"],
                    t("col_title"): p["title"],
                    t("model_score"): p["pred"],
                    t("human_score"): p["human"],
                    t("score_diff"): round(p["pred"] - p["human"], 1),
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
        return

    # 待标注列表
    st.subheader(t("pending_annotations"))

    # 选择待标注的职位
    options = [f"{p['company']} -- {p['title']} ({p['job_id'][:8]}...)" for p in pending]
    selected = st.selectbox(t("select_job_to_annotate"), options)

    if selected:
        idx = options.index(selected)
        job_info = pending[idx]
        job_id = job_info["job_id"]

        # 获取职位详情
        job = storage.jobs.get(job_id)
        clean_text = storage.jobs.get_clean(job_id)

        if job:
            # 显示职位信息
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{t('col_company')}**: {job.company}")
                st.write(f"**{t('col_title')}**: {job.title}")
            with col2:
                if job.url:
                    st.link_button(t("view_original"), job.url)

            # 显示 JD 内容
            jd_text = clean_text or job.description_md or ""
            with st.expander(t("view_jd_content"), expanded=True):
                st.text_area(
                    "JD",
                    value=jd_text[:3000],
                    height=400,
                    disabled=True,
                    label_visibility="collapsed",
                )

            # 如果有模型评分，显示参考
            latest_score = storage.scores.latest_for_job(job_id)
            if latest_score:
                st.info(t("model_score_ref").format(score=latest_score["overall"]))

            # 标注输入
            st.divider()
            st.subheader(t("enter_annotation"))

            human_score = st.slider(
                t("human_score_label"),
                min_value=0, max_value=100, value=50, step=1,
                help=t("human_score_help"),
            )

            # 评分参考
            with st.expander(t("scoring_reference")):
                st.markdown(t("scoring_reference_content"))

            if st.button(t("submit_annotation"), type="primary", use_container_width=True):
                from jobpilot.eval.dataset import record_annotation
                record_annotation(storage, job_id, human_score, annotator or "human")
                st.success(t("annotation_saved").format(score=human_score))
                st.rerun()
