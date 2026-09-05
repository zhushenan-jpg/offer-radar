"""集中配置:全部经环境变量/.env 注入,代码中不出现密钥."""

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    model: str = "glm-5.3-flash"
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
