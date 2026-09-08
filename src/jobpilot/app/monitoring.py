"""OfferRadar 扩展技能监控面板 (Streamlit).

监控指标:
- Claim 提取统计
- Gap Advisor 统计
- Interview Prep 统计
- 成本分析
- 性能指标
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from jobpilot.storage.db import Storage

DB = Path(os.environ.get("JOBPLOT_DB", "jobpilot.db"))


def get_storage() -> Storage:
    """获取存储实例."""
    return Storage.open(DB)


def get_claim_stats(storage: Storage) -> dict:
    """获取 Claim 提取统计."""
    try:
        rows = storage.conn.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(extraction_tokens) as total_tokens,
                   SUM(extraction_cost) as total_cost
            FROM claim_extractions
            WHERE created_at > datetime('now', '-7 days')
            """
        ).fetchone()
        return {
            "total": rows[0] or 0,
            "total_tokens": rows[1] or 0,
            "total_cost": rows[2] or 0.0,
        }
    except Exception:
        return {"total": 0, "total_tokens": 0, "total_cost": 0.0}


def get_patch_stats(storage: Storage) -> dict:
    """获取 Gap Advisor 统计."""
    try:
        rows = storage.conn.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(generation_tokens) as total_tokens,
                   SUM(generation_cost) as total_cost
            FROM resume_patches
            WHERE created_at > datetime('now', '-7 days')
            """
        ).fetchone()
        return {
            "total": rows[0] or 0,
            "total_tokens": rows[1] or 0,
            "total_cost": rows[2] or 0.0,
        }
    except Exception:
        return {"total": 0, "total_tokens": 0, "total_cost": 0.0}


def get_brief_stats(storage: Storage) -> dict:
    """获取 Interview Prep 统计."""
    try:
        rows = storage.conn.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(generation_tokens) as total_tokens,
                   SUM(generation_cost) as total_cost
            FROM interview_briefs
            WHERE created_at > datetime('now', '-7 days')
            """
        ).fetchone()
        return {
            "total": rows[0] or 0,
            "total_tokens": rows[1] or 0,
            "total_cost": rows[2] or 0.0,
        }
    except Exception:
        return {"total": 0, "total_tokens": 0, "total_cost": 0.0}


def get_cost_by_module(storage: Storage) -> dict:
    """获取各模块成本."""
    try:
        rows = storage.conn.execute(
            """
            SELECT module, SUM(cost_cny) as cost
            FROM usage
            WHERE ts > datetime('now', '-30 days')
            GROUP BY module
            """
        ).fetchall()
        return {row[0]: row[1] for row in rows}
    except Exception:
        return {}


def get_score_distribution(storage: Storage) -> pd.DataFrame:
    """获取评分分布."""
    try:
        rows = storage.conn.execute(
            """
            SELECT overall, COUNT(*) as count
            FROM scores
            GROUP BY ROUND(overall/10)*10
            ORDER BY overall
            """
        ).fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["分数段", "数量"])
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def main():
    """监控面板主函数."""
    st.set_page_config(
        page_title="OfferRadar 监控面板",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 OfferRadar 扩展技能监控")

    # 获取存储
    storage = get_storage()

    # 概览指标
    st.header("📈 概览 (最近 7 天)")

    claim_stats = get_claim_stats(storage)
    patch_stats = get_patch_stats(storage)
    brief_stats = get_brief_stats(storage)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Claim 提取",
            claim_stats["total"],
            help="提取的 Claim 数量",
        )

    with col2:
        st.metric(
            "简历补丁",
            patch_stats["total"],
            help="生成的简历补丁数量",
        )

    with col3:
        st.metric(
            "面试速览",
            brief_stats["total"],
            help="生成的面试速览数量",
        )

    with col4:
        total_cost = (
            claim_stats["total_cost"]
            + patch_stats["total_cost"]
            + brief_stats["total_cost"]
        )
        st.metric(
            "总成本",
            f"¥{total_cost:.2f}",
            help="扩展技能总成本",
        )

    # 成本分析
    st.header("💰 成本分析 (最近 30 天)")

    cost_by_module = get_cost_by_module(storage)

    if cost_by_module:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("各模块成本")
            for module, cost in cost_by_module.items():
                st.write(f"- {module}: ¥{cost:.2f}")

        with col2:
            st.subheader("扩展技能成本明细")
            st.write(f"- Claim 提取: ¥{claim_stats['total_cost']:.2f}")
            st.write(f"- Gap Advisor: ¥{patch_stats['total_cost']:.2f}")
            st.write(f"- Interview Prep: ¥{brief_stats['total_cost']:.2f}")
    else:
        st.info("暂无成本数据")

    # 评分分布
    st.header("📊 评分分布")

    score_df = get_score_distribution(storage)

    if not score_df.empty:
        st.bar_chart(score_df.set_index("分数段"))
    else:
        st.info("暂无评分数据")

    # 最近活动
    st.header("🕒 最近活动")

    try:
        recent_claims = storage.conn.execute(
            """
            SELECT job_id, resume_version, extraction_tokens, extraction_cost, created_at
            FROM claim_extractions
            ORDER BY created_at DESC
            LIMIT 10
            """
        ).fetchall()

        if recent_claims:
            df = pd.DataFrame(
                recent_claims,
                columns=["职位 ID", "简历版本", "Token 数", "成本", "创建时间"],
            )
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无 Claim 提取记录")
    except Exception as e:
        st.error(f"获取最近活动失败: {e}")

    # 页脚
    st.divider()
    st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption(f"数据库: {DB}")


if __name__ == "__main__":
    main()
