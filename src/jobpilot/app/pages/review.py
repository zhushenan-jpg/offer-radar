"""人工审核队列页面:审核低置信度评分."""

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
    """渲染人工审核队列页面."""
    st.title(t("review_title"))
    st.info(t("review_info"))

    db_path = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))
    if not db_path.exists():
        st.warning(t("no_jobs_warning"))
        return

    from jobpilot.storage.db import Storage
    storage = Storage.open(db_path)

    # 获取待审核列表
    pending = storage.scores.pending_review()

    # 统计
    all_scored = storage.jobs.scored_with_scores()
    review_count = len(pending)
    approved_count = len([r for r in all_scored if r.get("review_status") == "approved"])
    auto_count = len([r for r in all_scored if r.get("review_status") == "auto"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("review_pending"), review_count)
    with col2:
        st.metric(t("review_approved"), approved_count)
    with col3:
        st.metric(t("review_auto"), auto_count)

    st.divider()

    if not pending:
        st.success(t("review_all_done"))
        return

    # 待审核列表
    st.subheader(t("review_queue"))

    for item in pending:
        job_id = item["job_id"]
        confidence_pct = f"{item['confidence']:.0%}"

        with st.expander(
            f"⚠️ {item['company']} — {item['title']} | "
            f"{t('score')}: {item['overall']}/100 | "
            f"{t('confidence')}: {confidence_pct}",
            expanded=False,
        ):
            # 基本信息
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{t('col_company')}**: {item['company']}")
                st.write(f"**{t('col_title')}**: {item['title']}")
                st.write(f"**{t('col_location')}**: {item.get('location', '-')}")
            with col2:
                st.metric(t("score"), f"{item['overall']}/100")
                st.metric(t("confidence"), confidence_pct)

            # 模型评价
            st.write(f"**{t('summary_label')}**: {item.get('summary', '-')}")

            # 维度评分
            st.subheader(t("dim_scores"))
            dims = item.get("dims", {})
            for dim, data in dims.items():
                score_val = data.get("score", 0) if isinstance(data, dict) else 0
                st.write(f"**{dim}**: {score_val}/10")

            # 证据链
            claims = item.get("claims", [])
            if claims:
                st.subheader(t("evidence_chain_label"))
                for claim in claims[:5]:
                    if isinstance(claim, dict):
                        st.write(f"- **{claim.get('claim_type', '')}**: {claim.get('claim_text', '')}")

            # 差距分析
            gaps = item.get("gaps", [])
            if gaps:
                st.subheader(t("gap_analysis_label"))
                for gap in gaps:
                    if isinstance(gap, dict):
                        st.write(f"- **{gap.get('gap_type', '')}**: {gap.get('jd_requirement', '')}")

            # 查看原始职位
            if item.get("url"):
                st.link_button(t("view_original"), item["url"])

            # 审核操作
            st.divider()
            st.subheader(t("review_action"))

            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    t("review_approve"),
                    key=f"approve_{job_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    storage.scores.update_review_status(job_id, "approved")
                    st.success(t("review_approved_msg"))
                    st.rerun()

            with col2:
                override_score = st.slider(
                    t("review_override_label"),
                    min_value=0, max_value=100, value=item["overall"],
                    key=f"slider_{job_id}",
                )
                if st.button(
                    t("review_override"),
                    key=f"override_{job_id}",
                    type="secondary",
                    use_container_width=True,
                ):
                    # 记录人工标注并标记为已审核
                    storage.annotations.add(job_id, override_score, "human_review")
                    storage.scores.update_review_status(job_id, "approved")
                    st.success(t("review_overridden_msg").format(score=override_score))
                    st.rerun()
