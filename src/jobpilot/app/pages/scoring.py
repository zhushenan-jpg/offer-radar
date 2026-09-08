"""在线评分页面:粘贴 JD 文本直接评分."""

import sys
from pathlib import Path

import streamlit as st

_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def render():
    """渲染在线评分页面."""
    st.title("📊 在线评分")
    st.info("粘贴职位描述（JD），立即获得匹配评分和分析。")

    # 检查配置
    from jobpilot.config import GatewayConfig
    from jobpilot.models.profile import load_profile

    profile_path = Path(__file__).resolve().parents[4] / "profile.yaml"
    if not profile_path.exists():
        st.warning("⚠️ 请先在「我的简历」页面配置个人信息。")
        return

    config = GatewayConfig()
    if not config.api_key.get_secret_value():
        st.warning("⚠️ 请先在「设置」页面配置 API Key。")
        return

    # JD 输入
    st.header("📝 输入职位描述")

    tab1, tab2 = st.tabs(["粘贴文本", "上传文件"])

    jd_text = ""

    with tab1:
        jd_text = st.text_area(
            "粘贴 JD 内容",
            height=300,
            placeholder="""职位名称：后端开发实习生

公司简介：
我们是一家专注于云计算的科技公司...

岗位职责：
1. 负责后端 API 设计与开发
2. 参与系统架构设计和优化
3. 编写技术文档

任职要求：
1. 熟悉 Python 或 Java
2. 了解 MySQL、Redis 等数据库
3. 有 Docker 使用经验优先
4. 每周至少 4 天，实习 3 个月以上""",
        )

    with tab2:
        uploaded_file = st.file_uploader(
            "上传 JD 文件",
            type=["md", "txt", "pdf"],
            help="支持 Markdown、TXT 或 PDF 格式",
        )

        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                st.info("PDF 文件解析中...")
                # TODO: 集成 PDF 解析
                st.warning("PDF 解析功能开发中，请使用文本粘贴方式。")
            else:
                jd_text = uploaded_file.read().decode("utf-8")
                st.success(f"✅ 已上传: {uploaded_file.name}")

    # 评分按钮
    st.divider()

    if jd_text:
        if st.button("🚀 开始评分", type="primary", use_container_width=True):
            with st.spinner("正在分析 JD 并评分..."):
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
                        title="在线评分",
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

                    st.success("✅ 评分完成！")

                    # 显示结果
                    st.header("📊 评分结果")

                    # 综合分数
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("综合匹配", f"{result.overall}/100")
                    with col2:
                        st.metric("置信度", f"{result.confidence:.0%}")
                    with col3:
                        st.metric("评价", result.summary[:50] + "...")

                    # 维度评分
                    st.subheader("维度评分")
                    for dim, data in result.dims.items():
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.metric(dim, f"{data.score}/10")
                        with col2:
                            for ev in data.evidence:
                                st.caption(f"📝 {ev.quote}")

                    # 证据链
                    if result.claims:
                        st.subheader("🔍 证据链")
                        for claim in result.claims[:5]:
                            st.write(f"- **{claim.claim_type}**: {claim.claim_text} ({claim.strength})")

                    # 差距分析
                    if result.gaps:
                        st.subheader("⚠️ 差距分析")
                        for gap in result.gaps:
                            st.write(f"- **{gap.gap_type}**: {gap.jd_requirement}")
                            if gap.mitigation:
                                st.caption(f"  💡 建议: {gap.mitigation}")

                except Exception as e:
                    st.error(f"❌ 评分失败: {e}")
                    st.exception(e)

    else:
        st.info("💡 请在上方输入或上传职位描述（JD）")
