"""AI 简历优化页面:基于 Gap 分析生成简历改写建议."""

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
    """渲染简历优化页面."""
    st.title(t("resume_optimize_title"))
    st.info(t("resume_optimize_info"))

    db_path = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))
    profile_path = Path(__file__).resolve().parents[4] / "profile.yaml"

    if not profile_path.exists():
        st.warning(t("profile_required"))
        return

    if not db_path.exists():
        st.warning(t("no_jobs_warning"))
        return

    from jobpilot.models.profile import load_profile
    from jobpilot.storage.db import Storage

    storage = Storage.open(db_path)
    profile = load_profile(profile_path)

    # 获取已评分职位
    rows = storage.jobs.scored_with_scores()
    if not rows:
        st.warning(t("no_jobs_warning"))
        return

    # 选择职位
    options = [f"{r['company']} -- {r['title']} ({r['overall']}/100)" for r in rows]
    selected = st.selectbox(t("select_job"), options)

    if not selected:
        return

    idx = options.index(selected)
    job_info = rows[idx]
    job_id = job_info["job_id"]

    # 显示职位信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("score"), f"{job_info['overall']}/100")
    with col2:
        st.metric(t("confidence"), f"{job_info['confidence']:.0%}")
    with col3:
        st.write(f"**{t('col_company')}**: {job_info['company']}")

    st.divider()

    # 生成简历优化建议
    if st.button(t("generate_resume_patch"), type="primary", use_container_width=True):
        with st.spinner(t("generating_patch")):
            try:
                from jobpilot.config import GatewayConfig
                from jobpilot.llm_gateway.gateway import LLMGateway
                from jobpilot.tools.gap_advisor import GapAdvisor

                cfg = GatewayConfig()
                gateway = LLMGateway(cfg, storage)

                # 获取 claims 和 gaps
                latest_score = storage.scores.latest_for_job(job_id)
                import json
                claims = json.loads(latest_score["claims_json"]) if latest_score and latest_score["claims_json"] else []
                gaps = json.loads(latest_score["gaps_json"]) if latest_score and latest_score["gaps_json"] else []

                job = storage.jobs.get(job_id)
                clean_text = storage.jobs.get_clean(job_id) or (job.description_md if job else "")

                advisor = GapAdvisor(gateway, storage)
                patch = advisor.generate_patch(
                    resume_text=profile.resume_md or "",
                    job_posting_summary=clean_text[:2000],
                    claims=claims,
                    gaps=gaps,
                    job_id=job_id,
                )

                st.success(t("patch_generated"))

                # 显示 Bullet 改写建议
                if patch.bullet_rewrites:
                    st.subheader(t("bullet_rewrites"))
                    for br in patch.bullet_rewrites:
                        with st.expander(f"✏️ {br.original_text[:60]}..."):
                            st.write(f"**{t('original_text')}**: {br.original_text}")
                            st.write(f"**{t('suggested_rewrite')}**: {br.suggested_rewrite}")
                            st.write(f"**{t('matched_requirement')}**: {br.matched_jd_requirement}")

                # 显示缺失证据建议
                if patch.missing_evidence:
                    st.subheader(t("missing_evidence"))
                    for me in patch.missing_evidence:
                        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(me.priority, "⚪")
                        st.write(f"{priority_emoji} **{me.priority.upper()}**: {me.suggested_activity}")

                # 显示 HR 开场白
                if patch.hr_opener:
                    st.subheader(t("hr_opener"))
                    st.info(patch.hr_opener.opener_text)

                # 显示合并的增量内容
                if patch.patch_markdown:
                    st.subheader(t("patch_markdown"))
                    st.markdown(patch.patch_markdown)

                    # 下载按钮
                    st.download_button(
                        label=t("download_patch"),
                        data=patch.patch_markdown,
                        file_name=f"resume_patch_{job_info['company']}_{job_info['title']}.md",
                        mime="text/markdown",
                    )

            except Exception as e:
                st.error(t("error_unknown").format(error=e))
                st.exception(e)
