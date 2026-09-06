"""真实 API 冒烟测试(默认跳过,花少量 API 费用):

    pytest -m live

用于验证 .env 配置的端点与模型真实可用。全程 ≤2 次调用(失败自动重试 1 次,
以容忍中转站网络的间歇抖动)。
"""

import time

import pytest

from jobpilot.llm_gateway.gateway import LLMGateway
from jobpilot.models.score import MatchScore
from jobpilot.storage.db import Storage

pytestmark = [pytest.mark.live]


def _with_network_retry(fn, *, attempts: int = 2, wait_s: float = 8.0):
    """中转站网络间歇抖动:失败后等 wait_s 重试一次,仍失败才报错."""
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - 仅 live 测试使用
            last = e
            if attempt < attempts - 1:
                time.sleep(wait_s)
    raise last


@pytest.fixture()
def live_gateway(tmp_path, cfg):
    from jobpilot.config import GatewayConfig

    real_cfg = GatewayConfig()  # 从 .env / 环境变量读取真实端点与密钥
    if not real_cfg.api_key.get_secret_value():
        pytest.skip("未配置 API key")
    return LLMGateway(real_cfg, Storage.open(tmp_path / "live.db"))


def test_real_glm_json_call(live_gateway):
    """真模型对极简 JD 产出合法 MatchScore(结构化输出 + 证据校验链路)."""
    jd = "# 后端实习生\n要求:熟练使用 Python,了解 SQL 与 Git。支持远程实习。"

    def call():
        return live_gateway.json_in(
            MatchScore,
            f"候选人简历:大三学生,Python 1.5 年,FastAPI/SQL 项目经验。\n\n## JD\n{jd}",
            system="你是技术招聘顾问,按 0-10 分输出四维评分与证据。",
            module="live",
        )

    score = _with_network_retry(call)
    assert isinstance(score, MatchScore)
    assert 0 <= score.overall <= 100
    assert all(0 <= d.score <= 10 for d in score.dims.values())


def test_real_text_call(live_gateway):
    def call():
        return live_gateway.text("用一句话说明你是什么模型。", module="live")

    out = _with_network_retry(call)
    assert isinstance(out, str) and len(out) > 0
