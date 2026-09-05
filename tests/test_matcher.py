"""Matcher 集成测试:缓存 key 绑定版本、评分入库与复核标记."""

import pytest

from jobpilot.agents.matcher import score_and_store, score_job
from jobpilot.models.job import JobPosting
from jobpilot.models.profile import Profile
from jobpilot.models.score import DIMS, MatchScore
from jobpilot.testing import FakeGateway

JD = "# 后端实习\n要求熟悉 Python 与 SQL。"


def make_profile(resume_md="学生简历内容", **desired):
    return Profile(name="张三", skills=["Python"], years=1, resume_md=resume_md, **desired)


def seed_job(storage, job_id="a" * 16):
    """scores.job_id 有外键约束,先落一条 job."""
    storage.jobs.upsert(
        JobPosting(id=job_id, source="manual", company="manual", title="t", description_md=JD)
    )


class TestScoreJob:
    def test_returns_matchscore_with_recomputed_overall(self, cfg):
        gw = FakeGateway(cfg)
        score, key = score_job(gw, make_profile(), JD, job_id="a" * 16)
        assert isinstance(score, MatchScore)
        assert set(score.dims) == set(DIMS)
        assert 0 <= score.overall <= 100
        assert len(key) == 64

    def test_cache_key_varies_with_job_and_resume(self, cfg):
        gw = FakeGateway(cfg)
        _, k1 = score_job(gw, make_profile(), JD, job_id="a" * 16)
        _, k2 = score_job(gw, make_profile(), JD, job_id="b" * 16)
        _, k3 = score_job(gw, make_profile(resume_md="换了简历"), JD, job_id="a" * 16)
        assert len({k1, k2, k3}) == 3

    def test_prompt_contains_resume_and_jd_and_rubric(self, cfg):
        gw = FakeGateway(cfg)
        score_job(gw, make_profile(), JD, job_id="a" * 16)
        prompt = gw.calls[0]["prompt"]
        assert "学生简历内容" in prompt and "后端实习" in prompt
        assert gw.calls[0]["module"] == "matcher"


class TestScoreAndStore:
    def test_persists_with_versions(self, cfg, storage):
        gw = FakeGateway(cfg)
        prof = make_profile()
        seed_job(storage)
        score = score_and_store(gw, storage, prof, JD, job_id="a" * 16)
        row = storage.scores.latest_for_job("a" * 16)
        assert row["overall"] == pytest.approx(score.overall)
        assert row["rubric_version"] == "v1.0"
        assert row["model_version"] == cfg.model
        assert row["resume_version"] == prof.resume_version

    def test_low_confidence_marked_review(self, cfg, storage, monkeypatch):
        gw = FakeGateway(cfg)
        low = MatchScore.from_dims(
            {"skills": 1, "experience": 1, "constraints": 1, "growth": 1},
            confidence=0.3,
            summary="信息不足",
        )
        monkeypatch.setattr(gw, "json_in", lambda *a, **kw: low)
        seed_job(storage)
        score_and_store(gw, storage, make_profile(), JD, job_id="a" * 16)
        assert storage.scores.latest_for_job("a" * 16)["review_status"] == "review"
