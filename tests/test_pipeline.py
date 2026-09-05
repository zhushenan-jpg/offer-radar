"""周报渲染 + 流水线端到端测试(crawl 走 respx,评分走 FakeGateway)."""

import re

import httpx
import pytest
import respx

from jobpilot.config import GatewayConfig
from jobpilot.models.profile import Profile
from jobpilot.pipeline import run_report
from jobpilot.storage.db import Storage
from jobpilot.testing import FakeGateway
from tests.golden_loader import load_golden

pytestmark = pytest.mark.asyncio


@pytest.fixture()
def profile():
    return Profile(name="张三", skills=["Python"], years=1, resume_md="学生简历")


@respx.mock
async def test_run_report_produces_markdown(tmp_path, profile):
    storage = Storage.open(tmp_path / "p.db")
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs").mock(
        return_value=httpx.Response(200, json=load_golden("greenhouse_jobs.json"))
    )
    sources = [{"source": "greenhouse", "slug": "stripe", "name": "Stripe"}]
    gw = FakeGateway(GatewayConfig(api_key="fake", base_url="fake://x"), storage)

    report_path = await run_report(
        storage,
        profile,
        sources,
        gateway=gw,
        use_crew=False,
        out_dir=tmp_path / "reports",
        db_path=tmp_path / "p.db",
    )

    text = report_path.read_text(encoding="utf-8")
    assert re.search(r"20\d\d-W\d\d", report_path.name)
    assert "本周成本" in text
    assert "Stripe" in text
    # 评分已入库,状态流转 new -> scored
    assert storage.conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0] == 2
    assert (
        storage.conn.execute("SELECT COUNT(*) FROM jobs WHERE status='scored'").fetchone()[0] == 2
    )
    # 清洗产物落库
    assert (
        storage.conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE description_clean_md != ''"
        ).fetchone()[0]
        == 2
    )


@respx.mock
async def test_dead_source_skipped(tmp_path, profile):
    storage = Storage.open(tmp_path / "p.db")
    respx.get("https://boards-api.greenhouse.io/v1/boards/dead/jobs").mock(
        return_value=httpx.Response(404, json={})
    )
    sources = [{"source": "greenhouse", "slug": "dead", "name": "Dead Co"}]
    gw = FakeGateway(GatewayConfig(api_key="fake", base_url="fake://x"), storage)
    report_path = await run_report(
        storage,
        profile,
        sources,
        gateway=gw,
        use_crew=False,
        out_dir=tmp_path / "reports",
        db_path=tmp_path / "p.db",
    )
    text = report_path.read_text(encoding="utf-8")
    assert "0" in text  # 空周报也要能渲染
    assert storage.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


@respx.mock
async def test_crawl_is_incremental(tmp_path, profile):
    """重复跑批:同一职位不重复入库、不重复评分(缓存/去重生效)."""
    storage = Storage.open(tmp_path / "p.db")
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs").mock(
        return_value=httpx.Response(200, json=load_golden("greenhouse_jobs.json"))
    )
    sources = [{"source": "greenhouse", "slug": "stripe", "name": "Stripe"}]
    gw = FakeGateway(GatewayConfig(api_key="fake", base_url="fake://x"), storage)
    kw = {"gateway": gw, "use_crew": False, "out_dir": tmp_path / "reports", "db_path": tmp_path / "p.db"}
    await run_report(storage, profile, sources, **kw)
    first_scores = storage.conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
    await run_report(storage, profile, sources, **kw)
    assert storage.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 2
    assert storage.conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0] == first_scores
