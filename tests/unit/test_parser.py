"""parser (LLM JD 解析) 单元测试."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot.agents.parser import ParsedJD, parse_jd_llm, parse_jd_with_fallback


class TestParsedJDModel:
    def test_default_values(self):
        parsed = ParsedJD()
        assert parsed.skills == []
        assert parsed.level is None
        assert parsed.remote is None
        assert parsed.salary_min is None

    def test_with_values(self):
        parsed = ParsedJD(
            skills=["Python", "FastAPI"],
            level="mid",
            remote=True,
            salary_min=15000,
            salary_max=25000,
            years_min=3.0,
        )
        assert parsed.skills == ["Python", "FastAPI"]
        assert parsed.level == "mid"
        assert parsed.remote is True
        assert parsed.salary_min == 15000


class TestParseJdLLM:
    def test_parse_calls_gateway(self):
        mock_gateway = MagicMock()
        mock_gateway.cfg.model = "test-model"
        expected = ParsedJD(skills=["Python"], level="junior")
        mock_gateway.json_in.return_value = expected

        result = parse_jd_llm(mock_gateway, "Job: Python Developer", "job-1")

        assert result.skills == ["Python"]
        assert result.level == "junior"
        mock_gateway.json_in.assert_called_once()


class TestParseJdWithFallback:
    @patch("jobpilot.agents.parser.parse_jd_llm")
    def test_llm_success(self, mock_parse):
        mock_parse.return_value = ParsedJD(skills=["Go"], level="senior")
        result = parse_jd_with_fallback(MagicMock(), "JD text", "job-1")
        assert result["skills"] == ["Go"]
        assert result["parser"] == "llm"

    @patch("jobpilot.agents.parser.parse_jd_llm", side_effect=Exception("LLM failed"))
    @patch("jobpilot.pipeline.parse_jd")
    def test_fallback_to_regex(self, mock_regex, _):
        mock_regex.return_value = {"skills": ["Java"], "requirements": [], "raw_text": "JD"}
        result = parse_jd_with_fallback(MagicMock(), "JD text", "job-1")
        assert result["skills"] == ["Java"]
        assert result["parser"] == "regex"
