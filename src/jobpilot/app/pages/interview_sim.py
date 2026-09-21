"""面试模拟页面:基于公司调研和 JD 进行交互式面试问答."""

import json
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

SYSTEM_INTERVIEWER = """你是一位资深技术面试官。根据以下信息进行模拟面试：
1. 每次只问一个问题
2. 问题类型交替：技术题、行为题、系统设计题
3. 候选人回答后，给出简短评价（1-2句）和改进建议
4. 然后继续下一个问题
5. 用中文提问和评价

保持专业、友好、有建设性。"""


def render():
    """渲染面试模拟页面."""
    st.title(t("interview_sim_title"))
    st.info(t("interview_sim_info"))

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

    # 选择职位
    rows = storage.jobs.scored_with_scores()
    if not rows:
        st.warning(t("no_jobs_warning"))
        return

    options = [f"{r['company']} -- {r['title']} ({r['overall']}/100)" for r in rows]
    selected = st.selectbox(t("select_job"), options, key="interview_job_select")

    if not selected:
        return

    idx = options.index(selected)
    job_info = rows[idx]
    job_id = job_info["job_id"]

    # 显示面试准备摘要
    brief = storage.briefs.get(job_id)
    if brief:
        with st.expander(t("interview_prep_brief"), expanded=False):
            st.write(f"**{t('predicted_questions')}**: {', '.join(brief.predicted_questions[:5]) if brief.predicted_questions else '-'}")
            if brief.weak_points:
                st.write(f"**{t('weak_points')}**: {', '.join(brief.weak_points[:3])}")

    st.divider()

    # 初始化会话状态
    if "interview_messages" not in st.session_state:
        st.session_state.interview_messages = []
    if "interview_active" not in st.session_state:
        st.session_state.interview_active = False

    # 控制按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("start_interview"), type="primary", use_container_width=True):
            st.session_state.interview_messages = []
            st.session_state.interview_active = True
            # 生成第一个问题
            job = storage.jobs.get(job_id)
            jd_text = storage.jobs.get_clean(job_id) or (job.description_md if job else "")

            context = f"""职位: {job_info['company']} - {job_info['title']}
JD 摘要: {jd_text[:1500]}
候选人技能: {', '.join(profile.skills[:10])}
候选人经验: {profile.years} 年

请开始面试，提出第一个问题。"""

            try:
                from jobpilot.config import GatewayConfig
                from jobpilot.llm_gateway.gateway import LLMGateway

                cfg = GatewayConfig()
                gateway = LLMGateway(cfg, storage)

                first_question = gateway.text(
                    context,
                    system=SYSTEM_INTERVIEWER,
                    module="interview_sim",
                )
                st.session_state.interview_messages.append({
                    "role": "assistant",
                    "content": first_question,
                })
                st.rerun()
            except Exception as e:
                st.error(t("error_unknown").format(error=e))

    with col2:
        if st.button(t("end_interview"), type="secondary", use_container_width=True):
            st.session_state.interview_active = False
            st.session_state.interview_messages = []
            st.rerun()

    # 显示对话历史
    if st.session_state.interview_messages:
        for msg in st.session_state.interview_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # 用户输入回答
    if st.session_state.interview_active:
        user_input = st.chat_input(t("type_your_answer"))
        if user_input:
            # 显示用户回答
            st.session_state.interview_messages.append({
                "role": "user",
                "content": user_input,
            })

            # 生成面试官回复
            try:
                from jobpilot.config import GatewayConfig
                from jobpilot.llm_gateway.gateway import LLMGateway

                cfg = GatewayConfig()
                gateway = LLMGateway(cfg, storage)

                # 构建对话历史
                messages = [{"role": "system", "content": SYSTEM_INTERVIEWER}]
                for msg in st.session_state.interview_messages:
                    messages.append({"role": msg["role"], "content": msg["content"]})

                from openai import OpenAI
                client = OpenAI(
                    base_url=cfg.base_url,
                    api_key=cfg.api_key.get_secret_value(),
                    timeout=60.0,
                )
                completion = client.chat.completions.create(
                    model=cfg.model,
                    messages=messages,
                    temperature=cfg.temperature,
                )
                reply = completion.choices[0].message.content or ""

                st.session_state.interview_messages.append({
                    "role": "assistant",
                    "content": reply,
                })
                st.rerun()
            except Exception as e:
                st.error(t("error_unknown").format(error=e))
