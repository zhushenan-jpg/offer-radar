import pytest

from jobpilot.llm_gateway.exceptions import BudgetExceeded, GatewaySchemaError
from jobpilot.llm_gateway.gateway import LLMGateway
from jobpilot.models.score import MatchScore
from tests.conftest import SCORE_PAYLOAD
from tests.fakes import make_client, no_tools_responder, text_completion, tool_call_completion
from tests.test_models import make_dims


def raw_client(responder):
    """无 tools 支持 → 强制走网关手动回退通道."""
    return make_client(no_tools_responder(responder))


class TestJsonIn:
    def test_instructor_path_parses_schema(self, cfg, storage, tool_call_client):
        gw = LLMGateway(cfg, storage, client=tool_call_client)
        s = gw.json_in(MatchScore, "prompt", system="sys", cache_key="k1", module="matcher")
        assert isinstance(s, MatchScore)
        assert s.dims["skills"].score == 8

    def test_cache_roundtrip_no_second_call(self, cfg, storage, tool_call_client):
        gw = LLMGateway(cfg, storage, client=tool_call_client)
        gw.json_in(MatchScore, "prompt", cache_key="k1", module="matcher")
        s2 = gw.json_in(MatchScore, "prompt", cache_key="k1", module="matcher")
        assert len(tool_call_client.chat.completions.calls) == 1
        assert s2.dims["skills"].score == 8
        hits = storage.conn.execute("SELECT cache_hit FROM usage ORDER BY rowid").fetchall()
        assert [h[0] for h in hits] == [0, 1]

    def test_fallback_when_tools_unsupported(self, cfg, storage):
        import json as _json

        content = "<think>思考过程…</think>\n```json\n" + _json.dumps(SCORE_PAYLOAD) + "\n```"
        client = raw_client(lambda kw: text_completion(content, reasoning="reasoning…"))
        gw = LLMGateway(cfg, storage, client=client)
        s = gw.json_in(MatchScore, "prompt", cache_key="k2", module="matcher")
        assert s.dims["constraints"].score == 9

    def test_reasoning_content_ignored_in_tool_path(self, cfg, storage):
        def responder(kwargs):
            c = tool_call_completion(SCORE_PAYLOAD)
            c.choices[0].message.reasoning_content = "先思考…"
            return c

        gw = LLMGateway(cfg, storage, client=make_client(responder))
        s = gw.json_in(MatchScore, "prompt", cache_key="k3", module="matcher")
        assert isinstance(s, MatchScore)

    def test_schema_error_after_retries(self, cfg, storage):
        client = raw_client(lambda kw: text_completion("这不是 JSON"))
        gw = LLMGateway(cfg, storage, client=client)
        with pytest.raises(GatewaySchemaError):
            gw.json_in(MatchScore, "prompt", cache_key="k4", module="matcher")
        # 手动回退通道至少重试 max_retries 次(instructor 内部还可能有额外尝试)
        assert len(client.chat.completions.calls) >= cfg.max_retries

    def test_validation_error_feedback_in_retry(self, cfg, storage):
        """第一次回喂 bad score(15 超界)应触发重试并带上错误信息."""
        import json as _json

        bad = _json.dumps({"dims": make_dims(15, 6, 9, 5), "confidence": 0.8, "summary": "x"})
        calls = {"n": 0}

        def responder(kwargs):
            calls["n"] += 1
            content = _json.dumps(SCORE_PAYLOAD) if calls["n"] > 1 else bad
            return text_completion(content)

        gw = LLMGateway(cfg, storage, client=raw_client(responder))
        s = gw.json_in(MatchScore, "prompt", cache_key="k5", module="matcher")
        assert calls["n"] == 2
        assert s.dims["skills"].score == 8

    def test_budget_exceeded_blocks_call(self, cfg, storage, tool_call_client):
        storage.usage.record("matcher", "glm", 100, 100, cfg.monthly_budget_cny + 1, 0)
        gw = LLMGateway(cfg, storage, client=tool_call_client)
        with pytest.raises(BudgetExceeded):
            gw.json_in(MatchScore, "prompt", cache_key="k6", module="matcher")
        assert len(tool_call_client.chat.completions.calls) == 0

    def test_metering_records_cost(self, cfg, storage, tool_call_client):
        gw = LLMGateway(cfg, storage, client=tool_call_client)
        gw.json_in(MatchScore, "prompt", cache_key="k7", module="matcher")
        row = storage.conn.execute(
            "SELECT prompt_tokens, completion_tokens, cost_cny FROM usage"
        ).fetchone()
        assert row[0] == 100 and row[1] == 50
        assert row[2] > 0


class TestInvalidPayload:
    def test_non_dict_json_raises(self, cfg, storage):
        client = raw_client(lambda kw: text_completion('"just a string"'))
        gw = LLMGateway(cfg, storage, client=client)
        with pytest.raises(GatewaySchemaError):
            gw.json_in(MatchScore, "prompt", cache_key="k8", module="matcher")
