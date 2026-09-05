"""M4 组件测试:通知、调度任务、PDF 简历解析、浏览器兜底采集."""

import pytest

from jobpilot.collectors.base import CollectorError
from jobpilot.collectors.browser import BrowserCollector
from jobpilot.config import GatewayConfig
from jobpilot.models.job import JobPosting
from jobpilot.models.score import MatchScore
from jobpilot.notify import compose_alert_message, send_notification
from jobpilot.resume_pdf import parse_resume
from jobpilot.scheduler.jobs import build_scheduler, daily_incremental, high_score_alerts
from jobpilot.testing import FakeGateway


def _scored_job(storage, title="Backend Engineer", overall=88.0, url="https://x/j/1"):
    job = JobPosting(
        id=JobPosting.compute_id("greenhouse", "Stripe", title, "Remote"),
        source="greenhouse",
        company="Stripe",
        title=title,
        location="Remote",
        remote=True,
        url=url,
        description_md="# JD\nPython",
    )
    storage.jobs.upsert(job)
    dims = (
        {"skills": 9, "experience": 8, "constraints": 9, "growth": 8}
        if overall >= 75
        else {"skills": 2, "experience": 1, "constraints": 3, "growth": 2}
    )
    storage.scores.save(
        job.id,
        MatchScore.from_dims(dims, confidence=0.9, summary="评分"),
        rubric_version="v1.1",
        model_version="m",
        resume_version="r",
    )
    return job


class TestNotify:
    def test_no_url_is_noop(self):
        assert send_notification("hello") is False

    def test_bad_scheme_returns_false(self):
        assert send_notification("hello", notify_url="notascheme://x") is False

    def test_compose_alert_message(self):
        msg = compose_alert_message(
            [
                {
                    "company": "Stripe",
                    "title": "Backend Engineer",
                    "overall": 88,
                    "url": "https://x/j/1",
                }
            ],
            threshold=75,
        )
        assert "Stripe" in msg and "88" in msg and "≥75" in msg


class TestHighScoreAlerts:
    def test_today_high_scores_detected(self, storage):
        _scored_job(storage, overall=88.0)
        _scored_job(storage, title="Low Job", overall=40.0)
        alerts = high_score_alerts(storage, threshold=75)
        assert len(alerts) == 1
        assert alerts[0]["overall"] == 86.0


class TestDailyIncremental:
    def test_runs_pipeline_and_alerts(self, storage, monkeypatch):
        _scored_job(storage)
        calls = {}

        async def fake_collect(storage_, sources, client=None, cfg=None):
            calls["crawl"] = True
            return {"Stripe(stripe)": 1}

        monkeypatch.setattr("jobpilot.scheduler.jobs.collect_all", fake_collect)
        monkeypatch.setattr("jobpilot.scheduler.jobs.clean_pending", lambda s: 1)
        monkeypatch.setattr("jobpilot.scheduler.jobs.score_pending", lambda s, p, g: 1)
        cfg = GatewayConfig(api_key="k", base_url="x")
        summary = daily_incremental(
            storage,
            _profile(),
            [],
            FakeGateway(cfg, storage),
            notify_url="",
            threshold=75,
        )
        assert summary["alerts"] == 1 and calls.get("crawl")
        assert summary["scored"] == 1


def _profile():
    from jobpilot.models.profile import Profile

    return Profile(name="张三", skills=["Python"], years=1, resume_md="简历")


class TestScheduler:
    def test_three_jobs_registered(self, storage, tmp_path):
        sched = build_scheduler(
            storage, _profile(), [], FakeGateway(GatewayConfig(api_key="k", base_url="x"), storage)
        )
        jobs = {j.id: j.trigger for j in sched.get_jobs()}
        assert set(jobs) == {"weekly-full", "daily-incremental", "budget-patrol"}


class TestResumePdf:
    def make_pdf(
        self,
        tmp_path,
        text="Zhang San - Python Developer. Skills: Python, FastAPI, SQL. Three years of backend experience with Docker and Linux servers.",
    ):
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 6, text)
        path = tmp_path / "resume.pdf"
        pdf.output(str(path))
        return path

    def test_text_pdf_uses_free_path(self, tmp_path):
        from jobpilot.resume_pdf import parse_resume

        gw = FakeGateway(GatewayConfig(api_key="k", base_url="x"))
        md, channel = parse_resume(gw, self.make_pdf(tmp_path))
        assert channel == "text"
        assert "Python" in md
        assert len(gw.calls) == 0  # 文本抽取零模型调用

    def test_scanned_pdf_falls_back_to_vision(self, tmp_path, monkeypatch):
        from jobpilot import resume_pdf

        monkeypatch.setattr(resume_pdf, "extract_text", lambda p: "")
        monkeypatch.setattr(
            resume_pdf,
            "render_page_images",
            lambda p, max_pages=3, resolution=120: ["data:image/png;base64,QUJD"],
        )
        gw = FakeGateway(GatewayConfig(api_key="k", base_url="x"))
        _, channel = parse_resume(gw, tmp_path / "scan.pdf")
        assert channel == "vision"
        assert gw.calls[0]["images"] == ["data:image/png;base64,QUJD"]

    def test_update_profile_yaml(self, tmp_path):
        import yaml

        from jobpilot.resume_pdf import update_profile_yaml

        p = tmp_path / "profile.yaml"
        p.write_text(
            "name: 张三\nskills: [Python]\nyears: 1\nresume_md: 旧简历\n", encoding="utf-8"
        )
        update_profile_yaml(p, "新的简历内容")
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert data["resume_md"] == "新的简历内容"
        assert len(data["resume_version"]) == 12


class TestBrowserCollector:
    def test_fetch_parses_runner_items(self):
        runner_items = [
            {
                "title": "Backend Engineer",
                "location": "Remote",
                "url": "https://c.example/j/1",
                "description_md": "Python 开发",
            },
            {"title": "", "location": "", "url": "", "description_md": ""},  # 无标题跳过
        ]
        col = BrowserCollector(client=object(), runner=lambda url: runner_items)
        import asyncio

        jobs = asyncio.run(col.fetch("https://c.example/jobs", "Example Co"))
        assert len(jobs) == 1
        assert jobs[0].source == "browser"
        assert jobs[0].remote is True
        assert jobs[0].description_md == "Python 开发"

    def test_missing_browser_use_raises_collector_error(self):
        col = BrowserCollector(client=object(), runner=None, cfg=None)
        # 未注入 runner 且 browser-use 未安装 → CollectorError
        import asyncio

        with pytest.raises(CollectorError):
            asyncio.run(col.fetch("https://example.com", "X"))

    def test_registered_in_registry(self):
        from jobpilot.collectors import get_collector

        assert get_collector("browser", object(), cfg=None).__class__.__name__ == "BrowserCollector"
