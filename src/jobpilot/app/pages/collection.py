"""一键采集页面:触发职位采集."""

import asyncio
import sys
from pathlib import Path

import streamlit as st

_SRC = Path(__file__).resolve().parents[3]
_APP_DIR = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from i18n import t, get_language


def render():
    """渲染一键采集页面."""
    st.title(t("collection_title"))
    st.info(t("collection_info"))

    # 检查配置
    from pathlib import Path
    sources_file = Path(__file__).resolve().parents[4] / "sources.yaml"
    if not sources_file.exists():
        st.warning(t("configure_companies_first"))
        return

    import yaml
    sources = yaml.safe_load(sources_file.read_text(encoding="utf-8")) or []
    if not sources:
        st.warning(t("no_companies_configured"))
        return

    # 显示当前配置
    st.header(t("current_config"))

    import pandas as pd
    df = pd.DataFrame(sources)
    st.dataframe(df, use_container_width=True)

    st.write(t("companies_configured").format(count=len(sources)))

    # 采集选项
    st.header(t("collection_options"))

    col1, col2 = st.columns(2)

    with col1:
        mode = st.radio(
            "Collection Mode",
            [t("incremental"), t("full")],
        )

    with col2:
        limit = st.number_input(
            t("collection_limit"),
            min_value=0,
            max_value=1000,
            value=0,
            help=t("collection_limit_help"),
        )

    # 开始采集
    st.divider()

    if st.button(t("start_collection"), type="primary", use_container_width=True):
        try:
            from jobpilot.pipeline import clean_pending, SourceCfg
            from jobpilot.collectors import get_collector
            from jobpilot.collectors.dedup import dedupe_jobs
            from jobpilot.storage.db import Storage
            import httpx

            db_path = Path(__file__).resolve().parents[4] / "jobpilot.db"
            storage = Storage.open(db_path)

            # 转换 sources 格式
            source_cfgs = [SourceCfg.model_validate(s) for s in sources]
            if limit > 0:
                source_cfgs = source_cfgs[:limit]

            total = len(source_cfgs)
            summary = {}

            # 进度条
            progress_bar = st.progress(0, text=t("collection_progress").format(current=0, total=total))

            # 逐公司采集（显示进度）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = httpx.AsyncClient(timeout=30, headers={"User-Agent": "OfferRadar/1.0"})

            for i, src in enumerate(source_cfgs):
                progress_bar.progress(
                    (i) / total,
                    text=t("collection_progress").format(current=i + 1, total=total),
                )
                try:
                    collector = get_collector(src.source, client)
                    jobs = loop.run_until_complete(collector.fetch(src.slug, src.name))
                    kept, _removed = dedupe_jobs(jobs)
                    new = 0
                    for job in kept:
                        is_new = storage.jobs.get(job.id) is None
                        storage.jobs.upsert(job)
                        if is_new:
                            new += 1
                    summary[src.label()] = new
                except Exception as e:
                    summary[src.label()] = -1

            loop.run_until_complete(client.aclose())
            loop.close()

            progress_bar.progress(1.0, text=t("collection_done"))

            # 清洗新职位
            cleaned = clean_pending(storage)

            # 显示结果
            st.success(t("collection_success"))
            st.header(t("collection_result"))

            for source, count in summary.items():
                if count >= 0:
                    st.write(f"- **{source}**: {t('new_jobs_count').format(count=count)}")
                else:
                    st.write(f"- **{source}**: {t('collection_failed_source')}")

            st.write(f"\n{t('cleaned_count').format(count=cleaned)}")

        except Exception as e:
            err_str = str(e)
            if "connect" in err_str.lower() or "timeout" in err_str.lower() or "network" in err_str.lower():
                st.error(t("error_collection_network"))
            elif "json" in err_str.lower() or "parse" in err_str.lower() or "decode" in err_str.lower():
                st.error(t("error_collection_parse"))
            else:
                st.error(t("collection_failed").format(error=e))
            st.exception(e)

    # 采集说明
    st.divider()
    st.header(t("how_to_add"))

    with st.expander(t("how_to_add_expand")):
        st.markdown(t("how_to_add_content"))

    with st.expander(t("collection_frequency")):
        st.markdown(t("collection_frequency_content"))
