"""简历编辑页面:在线编辑个人信息和简历."""

import sys
from pathlib import Path

import yaml
import streamlit as st

# 添加 i18n 模块路径
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from i18n import t

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
    st.title(t("profile_title"))
    st.info(t("profile_info"))

    # 加载现有数据
    profile = load_profile()

    # 基础信息
    st.header(t("basic_info"))

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input(
            t("name"),
            value=profile.get("name", ""),
            placeholder=t("name_placeholder"),
        )

        years = st.number_input(
            t("work_years"),
            min_value=0.0,
            max_value=30.0,
            value=float(profile.get("years", 0)),
            step=0.5,
        )

    with col2:
        education = st.text_input(
            t("education"),
            value=profile.get("education", ""),
        )

        skills = st.text_area(
            t("skills"),
            value="\n".join(profile.get("skills", [])),
            height=100,
            placeholder=t("skills_placeholder"),
        )

    # 简历内容
    st.header(t("resume_content"))

    resume_md = st.text_area(
        t("resume_label"),
        value=profile.get("resume_md", ""),
        height=400,
        placeholder=t("resume_placeholder"),
    )

    # 求职意向
    st.header(t("job_preferences"))

    desired = profile.get("desired", {})

    col1, col2 = st.columns(2)

    with col1:
        roles = st.text_area(
            t("desired_roles"),
            value="\n".join(desired.get("roles", [])),
            height=80,
            placeholder=t("desired_roles_placeholder"),
        )

        cities = st.text_area(
            t("desired_cities"),
            value="\n".join(desired.get("cities", [])),
            height=80,
            placeholder=t("desired_cities_placeholder"),
        )

    with col2:
        remote_ok = st.checkbox(
            t("remote_ok"),
            value=desired.get("remote_ok", True),
        )

        salary_min = st.number_input(
            t("salary_min"),
            min_value=0,
            value=desired.get("salary_min") or 0,
        )

        salary_max = st.number_input(
            t("salary_max"),
            min_value=0,
            value=desired.get("salary_max") or 0,
        )

    # 保存按钮
    st.divider()

    if st.button(t("save_profile"), type="primary", use_container_width=True):
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
        st.success(t("profile_saved"))

    # 预览
    if resume_md:
        with st.expander(t("resume_preview"), expanded=False):
            st.markdown(resume_md)
