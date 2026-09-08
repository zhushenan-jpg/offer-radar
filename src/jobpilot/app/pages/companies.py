"""目标公司管理页面:添加/删除监控公司."""

import yaml
from pathlib import Path

import streamlit as st

SOURCES_FILE = Path(__file__).resolve().parents[4] / "sources.yaml"


def load_sources() -> list:
    """加载 sources.yaml."""
    if SOURCES_FILE.exists():
        return yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8")) or []
    return []


def save_sources(sources: list) -> None:
    """保存 sources.yaml."""
    SOURCES_FILE.write_text(
        yaml.dump(sources, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def render():
    """渲染目标公司管理页面."""
    st.title("🏢 目标公司管理")
    st.info("管理你想监控的公司，系统会自动采集这些公司的职位信息。")

    # 加载现有公司
    sources = load_sources()

    # 当前公司列表
    st.header("📋 当前监控的公司")

    if sources:
        # 表格展示
        import pandas as pd
        df = pd.DataFrame(sources)
        st.dataframe(df, use_container_width=True)

        # 删除功能
        st.subheader("🗑️ 删除公司")
        company_names = [f"{s['name']} ({s['source']})" for s in sources]
        selected = st.multiselect("选择要删除的公司", company_names)

        if selected and st.button("删除选中公司", type="secondary"):
            indices = [company_names.index(s) for s in selected]
            new_sources = [s for i, s in enumerate(sources) if i not in indices]
            save_sources(new_sources)
            st.success(f"✅ 已删除 {len(selected)} 个公司")
            st.rerun()
    else:
        st.warning("⚠️ 暂未配置目标公司，请在下方添加。")

    # 添加新公司
    st.divider()
    st.header("➕ 添加新公司")

    col1, col2, col3 = st.columns(3)

    with col1:
        new_name = st.text_input("公司名称", placeholder="如：Stripe")

    with col2:
        new_source = st.selectbox(
            "招聘平台",
            ["greenhouse", "lever"],
            help="选择公司使用的招聘平台",
        )

    with col3:
        new_slug = st.text_input(
            "平台标识",
            placeholder="如：stripe",
            help="公司在平台上的标识，通常在职位页面 URL 中可以看到",
        )

    if st.button("➕ 添加公司", type="primary"):
        if new_name and new_slug:
            # 检查是否已存在
            existing_slugs = [s.get("slug") for s in sources]
            if new_slug in existing_slugs:
                st.warning(f"⚠️ 公司 {new_slug} 已存在")
            else:
                sources.append({
                    "source": new_source,
                    "slug": new_slug,
                    "name": new_name,
                })
                save_sources(sources)
                st.success(f"✅ 已添加 {new_name}")
                st.rerun()
        else:
            st.warning("⚠️ 请填写公司名称和平台标识")

    # 批量导入
    st.divider()
    st.header("📥 批量导入")

    with st.expander("查看导入格式示例"):
        st.code("""
# sources.yaml 格式示例
- source: greenhouse
  slug: stripe
  name: Stripe

- source: greenhouse
  slug: airbnb
  name: Airbnb

- source: lever
  slug: netflix
  name: Netflix
        """, language="yaml")

    bulk_text = st.text_area(
        "批量导入（YAML 格式）",
        height=200,
        placeholder="""- source: greenhouse
  slug: stripe
  name: Stripe

- source: lever
  slug: netflix
  name: Netflix""",
    )

    if st.button("📥 导入"):
        if bulk_text:
            try:
                new_sources = yaml.safe_load(bulk_text)
                if isinstance(new_sources, list):
                    # 合并去重
                    existing_slugs = [s.get("slug") for s in sources]
                    added = 0
                    for s in new_sources:
                        if s.get("slug") not in existing_slugs:
                            sources.append(s)
                            existing_slugs.append(s.get("slug"))
                            added += 1
                    save_sources(sources)
                    st.success(f"✅ 成功导入 {added} 个新公司")
                    st.rerun()
                else:
                    st.error("❌ 格式错误，请使用 YAML 列表格式")
            except Exception as e:
                st.error(f"❌ 导入失败: {e}")

    # 常用公司推荐
    st.divider()
    st.header("💡 推荐公司")

    st.caption("以下是一些常用的科技公司，点击即可添加：")

    recommended = [
        {"name": "Stripe", "source": "greenhouse", "slug": "stripe"},
        {"name": "Airbnb", "source": "greenhouse", "slug": "airbnb"},
        {"name": "Coinbase", "source": "greenhouse", "slug": "coinbase"},
        {"name": "Netflix", "source": "lever", "slug": "netflix"},
        {"name": "Spotify", "source": "lever", "slug": "spotify"},
    ]

    existing_slugs = [s.get("slug") for s in sources]

    cols = st.columns(5)
    for i, company in enumerate(recommended):
        with cols[i]:
            if company["slug"] in existing_slugs:
                st.button(
                    f"✅ {company['name']}",
                    disabled=True,
                    key=f"rec_{i}",
                )
            else:
                if st.button(
                    f"➕ {company['name']}",
                    key=f"add_{i}",
                ):
                    sources.append(company)
                    save_sources(sources)
                    st.success(f"✅ 已添加 {company['name']}")
                    st.rerun()
