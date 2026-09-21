"""researcher_tool 单元测试."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot.tools.researcher_tool import ResearcherTool, _search_company


class TestSearchCompany:
    @patch("duckduckgo_search.DDGS")
    def test_search_returns_results(self, mock_ddgs_cls):
        mock_ddgs = MagicMock()
        mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = [
            {"title": "Stripe", "body": "Tech company", "href": "https://example.com"},
        ]
        result = _search_company("Stripe")
        assert "Stripe" in result

    def test_search_empty_results(self):
        with patch("duckduckgo_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = []
            result = _search_company("Stripe")
            assert "搜索未返回" in result

    @patch("duckduckgo_search.DDGS", side_effect=Exception("network"))
    def test_search_exception(self, _):
        result = _search_company("Stripe")
        assert "搜索出错" in result


class TestResearcherTool:
    def _make_tool(self, cache_return=None):
        mock_gateway = MagicMock()
        mock_gateway.cfg.model = "test-model"
        mock_storage = MagicMock()
        mock_storage.cache.get.return_value = cache_return
        return ResearcherTool(mock_gateway, mock_storage)

    def test_cached_result_returned(self):
        tool = self._make_tool(cache_return="cached report")
        result = tool.research("Stripe")
        assert result == "cached report"
        tool.gateway.text.assert_not_called()

    @patch("jobpilot.tools.researcher_tool._search_company", return_value="search results")
    def test_research_calls_llm(self, _):
        tool = self._make_tool(cache_return=None)
        tool.gateway.text.return_value = "research report"
        result = tool.research("Stripe", "Backend Engineer")
        assert result == "research report"
        tool.gateway.text.assert_called_once()
        tool.storage.cache.put.assert_called_once()
