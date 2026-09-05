"""面板冒烟测试:真实启动 streamlit 子进程,验证 health 与页面可访问."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

APP = Path(__file__).resolve().parents[1] / "src" / "jobpilot" / "app" / "dashboard.py"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture()
def demo_db(tmp_path):
    """一条带评分的职位,足够面板渲染."""
    from jobpilot.models.job import JobPosting
    from jobpilot.models.score import MatchScore
    from jobpilot.storage.db import Storage

    storage = Storage.open(tmp_path / "dash.db")
    job = JobPosting(
        id=JobPosting.compute_id("manual", "manual", "Backend Intern", ""),
        source="manual",
        company="manual",
        title="Backend Intern",
        description_md="# JD\nPython 开发",
    )
    storage.jobs.upsert(job)
    score = MatchScore.from_dims(
        {"skills": 8, "experience": 6, "constraints": 9, "growth": 7},
        confidence=0.8,
        summary="ok",
    )
    storage.scores.save(job.id, score, rubric_version="v1.1", model_version="m", resume_version="r")
    return storage, tmp_path


@pytest.mark.skipif(os.environ.get("SKIP_DASHBOARD_SMOKE"), reason="manual skip")
def test_dashboard_smoke(demo_db):
    pytest.importorskip("streamlit")
    storage, _ = demo_db
    port = _free_port()
    env = {
        **os.environ,
        "JOBPLOT_DB": str(storage.conn.execute("PRAGMA database_list").fetchone()[2]),
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP),
            "--server.headless",
            "true",
            "--server.port",
            str(port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # trust_env=False:httpx 默认配置与 streamlit 1.63 新代理层不兼容(502)
        client = httpx.Client(trust_env=False)
        base = f"http://127.0.0.1:{port}"
        deadline = time.time() + 90
        healthy = False
        while time.time() < deadline:
            try:
                if client.get(f"{base}/_stcore/health", timeout=3).text.strip() == "ok":
                    healthy = True
                    break
            except httpx.HTTPError:
                time.sleep(1)
        assert healthy, "streamlit 未在 90s 内就绪"
        page = client.get(base, timeout=10)
        assert page.status_code == 200
        client.close()
    finally:
        proc.terminate()
        proc.wait(timeout=15)
