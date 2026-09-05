"""采集器测试:respx 拦截 HTTP,金样文件来自真实 API 响应结构."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from jobpilot.collectors.base import CollectorError
from jobpilot.collectors.greenhouse import GreenhouseCollector
from jobpilot.collectors.lever import LeverCollector

GOLDEN = Path(__file__).parent / "golden"
GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"
LEVER_URL = "https://api.lever.co/v0/postings/plaid"


@pytest.fixture()
def client():
    return httpx.AsyncClient(timeout=10)


@pytest.mark.asyncio
class TestGreenhouse:
    @respx.mock
    async def test_fetch_normalizes(self, client):
        payload = json.loads((GOLDEN / "greenhouse_jobs.json").read_text(encoding="utf-8"))
        respx.get(GREENHOUSE_URL).mock(return_value=httpx.Response(200, json=payload))
        jobs = await GreenhouseCollector(client).fetch("stripe", "Stripe")
        assert len(jobs) == 2
        j = jobs[0]
        assert j.source == "greenhouse" and j.company == "Stripe"
        assert j.title == "Backend Engineer Intern"
        assert j.location == "Remote, US" and j.remote is True
        assert "About the role" in j.description_md
        assert "<h3>" not in j.description_md  # HTML 已转 markdown
        assert "Free lunch" in j.description_md
        assert jobs[1].remote is False

    @respx.mock
    async def test_unknown_slug_raises_collector_error(self, client):
        respx.get("https://boards-api.greenhouse.io/v1/boards/dead-slug/jobs").mock(
            return_value=httpx.Response(404, json={})
        )
        with pytest.raises(CollectorError):
            await GreenhouseCollector(client).fetch("dead-slug", "Dead")


@pytest.mark.asyncio
class TestLever:
    @respx.mock
    async def test_fetch_normalizes(self, client):
        payload = json.loads((GOLDEN / "lever_jobs.json").read_text(encoding="utf-8"))
        respx.get(LEVER_URL).mock(return_value=httpx.Response(200, json=payload))
        jobs = await LeverCollector(client).fetch("plaid", "Plaid")
        assert len(jobs) == 2
        j = jobs[0]
        assert j.source == "lever"
        assert j.title == "Site Reliability Engineer, Intern"
        assert j.remote is True
        assert "Strong Python skills" in j.description_md

    @respx.mock
    async def test_rate_limit_raises_collector_error(self, client):
        respx.get(LEVER_URL).mock(return_value=httpx.Response(429))
        with pytest.raises(CollectorError):
            await LeverCollector(client).fetch("plaid", "Plaid")
