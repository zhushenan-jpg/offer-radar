"""审核队列存储层单元测试."""

import pytest

from jobpilot.models.job import JobPosting
from jobpilot.models.score import DIMS, DimScore, Evidence, MatchScore
from jobpilot.storage.db import Storage


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    return Storage.open(db_path)


def _make_job(job_id):
    return JobPosting(
        id=job_id,
        source="manual",
        company="TestCo",
        title="Engineer",
        description_md="Test JD content for unit testing purposes.",
    )


def _make_score(overall=75, confidence=0.8):
    dims = {}
    for d in DIMS:
        dims[d] = DimScore(
            score=7,
            evidence=[Evidence(dim=d, quote="test evidence from JD", reason="matches requirement")],
        )
    return MatchScore(
        overall=overall,
        dims=dims,
        confidence=confidence,
        summary="Test summary",
        claims=[],
        gaps=[],
        evidence_matrix=[],
    )


def _job_id(n):
    return JobPosting.compute_id("manual", f"test{n}", f"Title{n}", "")


class TestReviewStatus:
    def test_auto_status_when_high_confidence(self, storage):
        jid = _job_id(1)
        storage.jobs.upsert(_make_job(jid))
        storage.scores.save(
            jid, _make_score(overall=80, confidence=0.9),
            rubric_version="v1", model_version="m1", resume_version="r1",
        )
        row = storage.scores.latest_for_job(jid)
        assert row["review_status"] == "auto"

    def test_review_status_when_low_confidence(self, storage):
        jid = _job_id(2)
        storage.jobs.upsert(_make_job(jid))
        storage.scores.save(
            jid, _make_score(overall=50, confidence=0.3),
            rubric_version="v1", model_version="m1", resume_version="r1",
        )
        row = storage.scores.latest_for_job(jid)
        assert row["review_status"] == "review"

    def test_update_review_status(self, storage):
        jid = _job_id(3)
        storage.jobs.upsert(_make_job(jid))
        storage.scores.save(
            jid, _make_score(overall=60, confidence=0.4),
            rubric_version="v1", model_version="m1", resume_version="r1",
        )
        storage.scores.update_review_status(jid, "approved")
        row = storage.scores.latest_for_job(jid)
        assert row["review_status"] == "approved"

    def test_pending_review(self, storage):
        jid_high = _job_id(4)
        storage.jobs.upsert(_make_job(jid_high))
        storage.scores.save(
            jid_high, _make_score(confidence=0.9),
            rubric_version="v1", model_version="m1", resume_version="r1",
        )
        jid_low = _job_id(5)
        storage.jobs.upsert(_make_job(jid_low))
        storage.scores.save(
            jid_low, _make_score(confidence=0.3),
            rubric_version="v1", model_version="m1", resume_version="r1",
        )
        pending = storage.scores.pending_review()
        assert len(pending) == 1
        assert pending[0]["job_id"] == jid_low

    def test_pending_review_excludes_approved(self, storage):
        jid = _job_id(6)
        storage.jobs.upsert(_make_job(jid))
        storage.scores.save(
            jid, _make_score(confidence=0.3),
            rubric_version="v1", model_version="m1", resume_version="r1",
        )
        storage.scores.update_review_status(jid, "approved")
        pending = storage.scores.pending_review()
        assert len(pending) == 0
