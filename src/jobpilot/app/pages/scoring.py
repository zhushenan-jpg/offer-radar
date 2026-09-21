"""在线评分页面:粘贴 JD 文本直接评分."""

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
    """渲染在线评分页面."""
    st.title(t("scoring_title"))
    st.info(t("scoring_info"))

    # 检查配置
    from jobpilot.config import GatewayConfig
    from jobpilot.models.profile import load_profile

    profile_path = Path(__file__).resolve().parents[4] / "profile.yaml"
    if not profile_path.exists():
        st.warning(t("profile_required"))
        return

    config = GatewayConfig()
    if not config.api_key.get_secret_value():
        st.warning(t("api_key_required"))
        return

    # JD 输入
    st.header(t("input_jd"))

    tab1, tab2 = st.tabs([t("paste_text"), t("upload_file")])

    jd_text = ""

    with tab1:
        jd_text = st.text_area(
            t("paste_jd"),
            height=300,
            placeholder="""Job Title: Backend Intern

Company Description:
We are a technology company focused on cloud computing...

Responsibilities:
1. Design and develop backend APIs
2. Participate in system architecture design
3. Write technical documentation

Requirements:
1. Proficient in Python or Java
2. Familiar with MySQL, Redis databases
3. Docker experience preferred
4. At least 4 days per week, 3+ months internship""",
        )

    with tab2:
        uploaded_file = st.file_uploader(
            t("upload_jd_file"),
            type=["md", "txt", "pdf"],
            help=t("upload_help"),
        )

        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                st.info(t("pdf_parsing"))
                st.warning(t("pdf_coming_soon"))
            else:
                jd_text = uploaded_file.read().decode("utf-8")
                st.success(t("uploaded_file").format(name=uploaded_file.name))

    # 评分按钮
    st.divider()

    if jd_text:
        if st.button(t("start_scoring"), type="primary", use_container_width=True):
            with st.spinner(t("analyzing")):
                try:
                    # 加载配置和简历
                    profile = load_profile(profile_path)

                    from jobpilot.agents.matcher import score_and_store
                    from jobpilot.llm_gateway.gateway import LLMGateway
                    from jobpilot.models.job import JobPosting
                    from jobpilot.pipeline import parse_jd
                    from jobpilot.storage.db import Storage

                    # 创建网关
                    db_path = Path(__file__).resolve().parents[4] / "jobpilot.db"
                    storage = Storage.open(db_path)
                    gateway = LLMGateway(config, storage)

                    # 创建职位
                    job = JobPosting(
                        id=JobPosting.compute_id("manual", "manual", "web_input", ""),
                        source="manual",
                        company="web_input",
                        title="Online Scoring",
                        description_md=jd_text,
                    )
                    storage.jobs.upsert(job)

                    # 解析 JD
                    parsed_jd = parse_jd(jd_text)

                    # 评分
                    result = score_and_store(
                        gateway, storage, profile, jd_text,
                        parsed_jd=parsed_jd, job_id=job.id,
                    )

                    st.success(t("scoring_completed"))

                    # 显示结果
                    st.header(t("scoring_result"))

                    # 综合分数
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(t("overall_match"), f"{result.overall}/100")
                    with col2:
                        st.metric(t("confidence_label"), f"{result.confidence:.0%}")
                    with col3:
                        st.metric(t("summary_label"), result.summary[:50] + "...")

                    # 维度评分
                    st.subheader(t("dimension_scores_label"))
                    for dim, data in result.dims.items():
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.metric(dim, f"{data.score}/10")
                        with col2:
                            for ev in data.evidence:
                                st.caption(f"📝 {ev.quote}")

                    # 证据链
                    if result.claims:
                        st.subheader(t("evidence_chain_label"))
                        for claim in result.claims[:5]:
                            st.write(f"- **{claim.claim_type}**: {claim.claim_text} ({claim.strength})")

                    # 差距分析
                    if result.gaps:
                        st.subheader(t("gap_analysis_label"))
                        for gap in result.gaps:
                            st.write(f"- **{gap.gap_type}**: {gap.jd_requirement}")
                            if gap.mitigation:
                                st.caption(f"  💡 {t('suggestion_label')}: {gap.mitigation}")

                except Exception as e:
                    err_str = str(e)
                    from jobpilot.llm_gateway.exceptions import BudgetExceeded, GatewaySchemaError
                    if isinstance(e, BudgetExceeded):
                        st.error(t("error_budget_exceeded").format(amount=f"¥{e}"))
                    elif isinstance(e, GatewaySchemaError):
                        st.error(t("error_gateway_schema"))
                    elif "timeout" in err_str.lower() or "timed out" in err_str.lower():
                        st.error(t("error_timeout"))
                    elif "401" in err_str or "auth" in err_str.lower() or "invalid" in err_str.lower():
                        st.error(t("error_auth"))
                    elif "connect" in err_str.lower() or "network" in err_str.lower():
                        st.error(t("error_network"))
                    else:
                        st.error(t("scoring_error").format(error=e))
                    st.exception(e)

    else:
        st.info(t("input_prompt"))
