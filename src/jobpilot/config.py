"""集中配置:全部经环境变量/.env 注入,代码中不出现密钥."""

import os

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_streamlit_secrets():
    """从 Streamlit secrets 加载环境变量."""
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            for key, value in st.secrets.items():
                if key not in os.environ:
                    os.environ[key] = str(value)
    except Exception:
        pass


# 尝试加载 Streamlit secrets
_load_streamlit_secrets()


class GatewayConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_prefix="JOBPLOT_",
    )

    model: str = "mimo-v2.5-pro"
    base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/",
        validation_alias=AliasChoices("OPENAI_BASE_URL", "JOBPLOT_BASE_URL"),
    )
    api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("ZHIPU_API_KEY", "JOBPLOT_API_KEY"),
    )
    temperature: float = 1.0
    top_p: float = 0.95
    max_retries: int = 3
    timeout_s: float = 120.0
    monthly_budget_cny: float = 30.0
    price_input_cny_per_mtok: float = Field(
        default=4.0, validation_alias=AliasChoices("JOBPLOT_PRICE_INPUT_CNY_PER_MTOK")
    )
    price_output_cny_per_mtok: float = Field(
        default=21.0, validation_alias=AliasChoices("JOBPLOT_PRICE_OUTPUT_CNY_PER_MTOK")
    )
    # 监控推送(M4):apprise 渠道 URL(如 mailto://、json://),留空则不推送
    notify_url: str = ""
    # 高分职位即时推送阈值(0-100)
    alert_threshold: int = 75
