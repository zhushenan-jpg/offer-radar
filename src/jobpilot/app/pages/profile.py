"""简历编辑页面:在线编辑个人信息和简历."""

import yaml
from pathlib import Path

import streamlit as st

PROFILE_FILE = Path(__file__).resolve().parents[4] / "profile.yaml"


def load_profile() -> dict:
    """加载 profile.yaml."""
    if PROFILE_FILE.exists():
        return yaml.safe_load(PROFILE_FILE.read_text(encoding="utf-8")) or {}
    return {}


def save_profile(data: dict) -> None:
    """保存 profile.yaml."""
    PROFILE_FILE.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def render():
    """渲染简历编辑页面."""
    st.title("📝 我的简历")
    st.info("编辑你的个人信息和简历内容，用于职位匹配评分。")

    # 加载现有数据
    profile = load_profile()

    # 基础信息
    st.header("👤 基础信息")

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input(
            "姓名",
            value=profile.get("name", ""),
            placeholder="输入你的姓名",
        )

        years = st.number_input(
            "工作年限",
            min_value=0.0,
            max_value=30.0,
            value=float(profile.get("years", 0)),
            step=0.5,
        )

    with col2:
        education = st.text_input(
            "学历",
            value=profile.get("education", ""),
            placeholder="如：本科、硕士",
        )

        skills = st.text_area(
            "技能（每行一个）",
            value="\n".join(profile.get("skills", [])),
            height=100,
            placeholder="Python\nJava\nReact\nSQL",
        )

    # 简历内容
    st.header("📄 简历内容")

    resume_md = st.text_area(
        "简历（Markdown 格式）",
        value=profile.get("resume_md", ""),
        height=400,
        placeholder="""# 你的名字

## 教育背景
XX大学 计算机科学与技术 本科 (2022-2026)

## 技能
- Python, Java, JavaScript
- React, Vue.js
- MySQL, Redis

## 项目经历

### 项目名称 (2024.09 - 2024.12)
- 项目描述
- 使用技术
- 取得成果

## 实习经历
公司名称 职位 (2025.07 - 2025.09)
- 工作内容
- 取得成果""",
    )

    # 求职意向
    st.header("🎯 求职意向")

    desired = profile.get("desired", {})

    col1, col2 = st.columns(2)

    with col1:
        roles = st.text_area(
            "期望岗位（每行一个）",
            value="\n".join(desired.get("roles", [])),
            height=80,
            placeholder="后端开发\n全栈开发\n软件工程师",
        )

        cities = st.text_area(
            "期望城市（每行一个）",
            value="\n".join(desired.get("cities", [])),
            height=80,
            placeholder="北京\n上海\n深圳\n远程",
        )

    with col2:
        remote_ok = st.checkbox(
            "接受远程",
            value=desired.get("remote_ok", True),
        )

        salary_min = st.number_input(
            "最低薪资（元/月，0 表示不限）",
            min_value=0,
            value=desired.get("salary_min") or 0,
        )

        salary_max = st.number_input(
            "最高薪资（元/月，0 表示不限）",
            min_value=0,
            value=desired.get("salary_max") or 0,
        )

    # 保存按钮
    st.divider()

    if st.button("💾 保存简历", type="primary", use_container_width=True):
        # 处理技能列表
        skills_list = [s.strip() for s in skills.split("\n") if s.strip()]

        # 处理岗位列表
        roles_list = [r.strip() for r in roles.split("\n") if r.strip()]

        # 处理城市列表
        cities_list = [c.strip() for c in cities.split("\n") if c.strip()]

        new_profile = {
            "name": name,
            "skills": skills_list,
            "years": years,
            "education": education,
            "resume_md": resume_md,
            "desired": {
                "roles": roles_list,
                "cities": cities_list,
                "remote_ok": remote_ok,
                "salary_min": salary_min if salary_min > 0 else None,
                "salary_max": salary_max if salary_max > 0 else None,
            },
        }

        save_profile(new_profile)
        st.success("✅ 简历已保存！")

    # 预览
    if resume_md:
        with st.expander("👁️ 简历预览", expanded=False):
            st.markdown(resume_md)
