"""离线/测试用假网关:接口与 LLMGateway 一致,不产生任何网络调用."""

from jobpilot.config import GatewayConfig
from jobpilot.models.score import MatchScore


class FakeGateway:
    def __init__(self, cfg: GatewayConfig | None = None, storage=None):
        self.cfg = cfg or GatewayConfig(api_key="fake", base_url="fake://local", model="fake-model")
        self.storage = storage
        self.calls: list[dict] = []

    def json_in(self, schema, prompt, *, system="", cache_key=None, module="", validator=None):
        self.calls.append(
            {"schema": schema, "prompt": prompt, "cache_key": cache_key, "module": module}
        )
        if schema is MatchScore:
            return MatchScore.from_dims(
                {"skills": 8, "experience": 6, "constraints": 9, "growth": 7},
                confidence=0.8,
                summary="离线假评分(--fake 模式)",
            )
        raise NotImplementedError(f"FakeGateway 不支持 {schema.__name__}")

    def text(self, prompt, *, system="", module=""):
        self.calls.append({"schema": None, "prompt": prompt, "module": module})
        return "离线假文本"
