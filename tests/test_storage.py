from datetime import UTC, datetime, timedelta

from jobpilot.models.job import JobPosting
from jobpilot.models.score import MatchScore
from tests.test_models import make_dims


def make_job(job_id="a" * 16, title="Backend Intern"):
    return JobPosting(
        id=job_id,
        source="manual",
        company="manual",
        title=title,
        location="Remote",
        description_md="# JD\n内容",
    )


def make_score(confidence=0.8):
    return MatchScore(dims=make_dims(), confidence=confidence, summary="ok", overall=0)


class TestSchema:
    def test_wal_mode(self, storage):
        mode = storage.conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_tables_exist(self, storage):
        rows = storage.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {r[0] for r in rows}
        assert {
            "companies",
            "jobs",
            "scores",
            "llm_cache",
            "usage",
            "annotations",
            "reports",
        } <= names


class TestJobRepo:
    def test_upsert_idempotent(self, storage):
        job = make_job()
        storage.jobs.upsert(job)
        job.title = "Backend Intern II"
        storage.jobs.upsert(job)
        rows = storage.conn.execute("SELECT title, last_seen FROM jobs").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "Backend Intern II"

    def test_get_roundtrip(self, storage):
        job = make_job()
        storage.jobs.upsert(job)
        loaded = storage.jobs.get(job.id)
        assert loaded.title == job.title
        assert loaded.source == "manual"
        assert loaded.description_md == job.description_md

    def test_get_missing_returns_none(self, storage):
        assert storage.jobs.get("z" * 16) is None


class TestScoreRepo:
    def test_save_and_latest(self, storage):
        job = make_job()
        storage.jobs.upsert(job)
        storage.scores.save(
            job.id,
            make_score(),
            rubric_version="v1.0",
            model_version="glm-5.3-flash",
            resume_version="r1",
        )
        row = storage.scores.latest_for_job(job.id)
        assert row["overall"] == pytest_overall()
        assert row["rubric_version"] == "v1.0"

    def test_low_confidence_marked_review(self, storage):
        job = make_job()
        storage.jobs.upsert(job)
        storage.scores.save(
            job.id,
            make_score(confidence=0.4),
            rubric_version="v1.0",
            model_version="m",
            resume_version="r",
        )
        assert storage.scores.latest_for_job(job.id)["review_status"] == "review"


def pytest_overall():
    dims = make_dims()
    return round(
        sum(
            w * dims[k]["score"]
            for k, w in {
                "skills": 0.4,
                "experience": 0.25,
                "constraints": 0.2,
                "growth": 0.15,
            }.items()
        )
        * 10,
        1,
    )


class TestUsageRepo:
    def test_month_cost_only_current_month(self, storage):
        now = datetime.now(UTC)
        old = now - timedelta(days=45)
        storage.usage.record("matcher", "glm", 100, 50, 1.0, 0, ts=now.isoformat())
        storage.usage.record("matcher", "glm", 100, 50, 2.0, 0, ts=old.isoformat())
        assert storage.usage.month_cost() == 1.0

    def test_month_cost_by_module(self, storage):
        storage.usage.record("matcher", "glm", 10, 5, 1.0, 0)
        storage.usage.record("parser", "glm", 10, 5, 0.5, 0)
        by = storage.usage.month_cost_by_module()
        assert by == {"matcher": 1.0, "parser": 0.5}


class TestCacheRepo:
    def test_put_get(self, storage):
        storage.cache.put("k1", '{"a": 1}')
        assert storage.cache.get("k1") == '{"a": 1}'
        assert storage.cache.get("nope") is None
