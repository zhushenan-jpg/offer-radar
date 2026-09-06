"""总体测试阶段补充的健壮性用例."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from jobpilot.app.cli import app
from jobpilot.collectors.dedup import dedupe_jobs
from jobpilot.llm_gateway.exceptions import GatewayError
from jobpilot.llm_gateway.gateway import LLMGateway, extract_json
from jobpilot.models.job import JobPosting

runner = CliRunner()


class TestNoKeyFriendlyError:
    def test_gateway_raises_with_hint(self):
        from jobpilot.config import GatewayConfig

        cfg = GatewayConfig(api_key="")
        with pytest.raises(GatewayError) as ei:
            LLMGateway(cfg)
        assert ".env" in str(ei.value) and "ZHIPU_API_KEY" in str(ei.value)

    def test_cli_real_mode_exits_1_with_message(self, tmp_path, monkeypatch):
        """真实模式 + 无 key:CLI 应退出码 1 + 中文提示,而非异常堆栈."""
        from jobpilot import config as config_module

        real_cls = config_module.GatewayConfig

        class EmptyKeyConfig(real_cls):
            def __init__(self, **kw):
                kw["api_key"] = ""
                super().__init__(**kw)

        monkeypatch.setattr(config_module, "GatewayConfig", EmptyKeyConfig)
        result = runner.invoke(
            app,
            [
                "score",
                "--file",
                str(Path(__file__).parents[1] / "examples" / "jobs" / "jd_backend_intern.md"),
                "--profile",
                str(Path(__file__).parents[1] / "profile.example.yaml"),
                "--db",
                str(tmp_path / "r.db"),
            ],
        )
        assert result.exit_code == 1
        assert "ZHIPU_API_KEY" in result.output


class TestExtractJson:
    def test_double_encoded_json(self):
        import json

        inner = json.dumps({"a": 1})
        wrapped = json.dumps(inner)  # 把 JSON 对象再包一层字符串
        assert extract_json(wrapped) == inner

    def test_think_block_and_fence(self):
        text = '<think>思考</think>\n```json\n{"b": 2}\n```'
        assert extract_json(text) == '{"b": 2}'


class TestDedupEdge:
    def test_empty_list(self):
        assert dedupe_jobs([]) == ([], 0)

    def test_unicode_titles(self):
        def job(title, company):
            return JobPosting(
                id=JobPosting.compute_id("greenhouse", company, title, "北京"),
                source="greenhouse",
                company=company,
                title=title,
                location="北京",
                description_md="JD",
            )

        kept, removed = dedupe_jobs([job("后端开发工程师", "A"), job("后端开发工程师(北京)", "A")])
        assert len(kept) == 2 and removed == 0  # 不同标题不算重复

    def test_source_stays_within_literal(self):
        j = JobPosting(id="b" * 16, source="browser", company="c", title="t", description_md="d")
        assert j.source == "browser"


class TestCliErrorPaths:
    def test_eval_run_insufficient_annotations(self, tmp_path):
        result = runner.invoke(
            app,
            [
                "eval-run",
                "--db", str(tmp_path / "empty.db"),
                "--profile", str(Path(__file__).parents[1] / "profile.example.yaml"),
                "--fake",
            ],
        )
        assert result.exit_code == 1
        assert "评测集为空" in result.output

    def test_score_missing_file_rejected(self, tmp_path):
        result = runner.invoke(
            app,
            [
                "score",
                "--file",
                str(tmp_path / "nope.md"),
                "--profile",
                str(Path(__file__).parents[1] / "profile.example.yaml"),
                "--fake",
            ],
        )
        assert result.exit_code != 0
