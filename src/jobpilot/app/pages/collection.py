"""一键采集页面:触发职位采集."""

import asyncio
import sys
from pathlib import Path

import streamlit as st

_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def render():
    """渲染一键采集页面."""
    st.title("🔄 一键采集")
    st.info("从目标公司采集最新职位信息。")

    # 检查配置
    from pathlib import Path
    sources_file = Path(__file__).resolve().parents[4] / "sources.yaml"
    if not sources_file.exists():
        st.warning("⚠️ 请先在「目标公司」页面配置要监控的公司。")
        return

    import yaml
    sources = yaml.safe_load(sources_file.read_text(encoding="utf-8")) or []
    if not sources:
        st.warning("⚠️ 暂未配置目标公司，请先添加。")
        return

    # 显示当前配置
    st.header("📋 当前配置")

    import pandas as pd
    df = pd.DataFrame(sources)
    st.dataframe(df, use_container_width=True)

    st.write(f"共配置了 **{len(sources)}** 家公司")

    # 采集选项
    st.header("⚙️ 采集选项")

    col1, col2 = st.columns(2)

    with col1:
        mode = st.radio(
            "采集模式",
            ["增量采集（仅新职位）", "全量采集（所有职位）"],
            help="增量采集只获取新发布的职位，全量采集会更新所有职位信息",
        )

    with col2:
        limit = st.number_input(
            "采集数量限制",
            min_value=0,
            max_value=1000,
            value=0,
            help="0 表示不限制",
        )

    # 开始采集
    st.divider()

    if st.button("🚀 开始采集", type="primary", use_container_width=True):
        with st.spinner("正在采集职位信息..."):
            try:
                from jobpilot.pipeline import collect_all, clean_pending, SourceCfg
                from jobpilot.storage.db import Storage

                db_path = Path(__file__).resolve().parents[4] / "jobpilot.db"
                storage = Storage.open(db_path)

                # 转换 sources 格式
                source_cfgs = [SourceCfg.model_validate(s) for s in sources]

                # 执行采集
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if limit > 0:
                    # 限制模式：只采集前 N 个公司
                    source_cfgs = source_cfgs[:limit]

                summary = loop.run_until_complete(
                    collect_all(storage, source_cfgs)
                )
                loop.close()

                # 清洗新职位
                cleaned = clean_pending(storage)

                # 显示结果
                st.success("✅ 采集完成！")

                st.header("📊 采集结果")

                for source, count in summary.items():
                    if count >= 0:
                        st.write(f"- **{source}**: 新增 {count} 条职位")
                    else:
                        st.write(f"- **{source}**: ⚠️ 采集失败")

                st.write(f"\n已清洗 **{cleaned}** 条新职位")

            except Exception as e:
                st.error(f"❌ 采集失败: {e}")
                st.exception(e)

    # 采集说明
    st.divider()
    st.header("📖 说明")

    with st.expander("如何添加更多公司？"):
        st.markdown("""
        1. 访问「🏢 目标公司」页面
        2. 输入公司名称、选择平台（Greenhouse 或 Lever）
        3. 输入公司在平台上的标识（slug）
        4. 点击「添加公司」

        **如何找到公司的 slug？**
        - 访问公司的招聘页面
        - 查看 URL，例如：`https://boards.greenhouse.io/stripe`
        - 其中 `stripe` 就是 slug
        """)

    with st.expander("采集频率建议"):
        st.markdown("""
        - **日常使用**: 每周采集 1-2 次即可
        - **求职高峰期**: 可以每天采集
        - **全量采集**: 适合初次使用或需要更新所有职位信息
        - **增量采集**: 适合日常使用，只获取新职位
        """)
