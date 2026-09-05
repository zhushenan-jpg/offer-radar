import pytest

from jobpilot.config import GatewayConfig
from jobpilot.storage.db import Storage
from tests.fakes import make_client, tool_call_completion

SCORE_PAYLOAD = {
    "dims": {
        "skills": {
            "score": 8,
            "evidence": [
                {"dim": "skills", "quote": "熟练使用 Python 与 FastAPI", "reason": "核心技能命中"}
            ],
        },
        "experience": {
            "score": 6,
            "evidence": [
                {"dim": "experience", "quote": "有校园项目经验", "reason": "项目经验相关"}
            ],
        },
        "constraints": {
            "score": 9,
            "evidence": [{"dim": "constraints", "quote": "支持远程实习", "reason": "满足地点约束"}],
        },
        "growth": {
            "score": 5,
            "evidence": [{"dim": "growth", "quote": "接触高并发场景", "reason": "成长路径一般"}],
        },
    },
    "confidence": 0.8,
    "summary": "整体匹配良好",
}


@pytest.fixture()
def cfg():
    return GatewayConfig(api_key="test-key", base_url="http://localhost:9999/v1")


@pytest.fixture()
def storage(tmp_path):
    return Storage.open(tmp_path / "test.db")


@pytest.fixture()
def tool_call_client():
    return make_client(lambda kwargs: tool_call_completion(SCORE_PAYLOAD))


@pytest.fixture()
def score_payload():
    return SCORE_PAYLOAD
