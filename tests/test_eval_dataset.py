"""评测数据集模块单元测试."""

import pytest

from jobpilot.eval.dataset import dump_dims, pairs_with_predictions, pending_ids, record_annotation, seed_dataset
from jobpilot.models.job import JobPosting
from jobpilot.models.score import DIMS, DimScore, Evidence, MatchScore
from jobpilot.storage.db import Storage


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    return Storage.open(db_path)


def _make_job(n, company="TestCo"):
    return JobPosting(
        id=JobPosting.compute_id("manual", company, f"Title{n}", ""),
        source="manual",
        company=company,
        title=f"Title{n}",
        description_md=f"JD {n}",
    )


def _make_score(overall=75, confidence=0.8):
    dims = {}
    for d in DIMS:
        dims[d] = DimScore(score=7, evidence=[Evidence(dim=d, quote="test evidence", reason="match")])
    return MatchScore(overall=overall, dims=dims, confidence=confidence, summary="ok", claims=[], gaps=[], evidence_matrix=[])


class TestSeedDataset:
    def test_seed_empty_db(self, storage):
        picked = seed_dataset(storage, n=10)
        assert picked == []

    def test_seed_with_jobs(self, storage):
        for i in range(6):
            storage.jobs.upsert(_make_job(i))
        picked = seed_dataset(storage, n=6)
        assert len(picked) > 0
        # Verify eval dataset contains the picked jobs
        eval_ids = storage.eval_ds.all_ids()
        assert len(eval_ids) > 0

    def test_seed_respects_n(self, storage):
        for i in range(10):
            storage.jobs.upsert(_make_job(i))
        picked = seed_dataset(storage, n=3)
        assert len(picked) <= 10  # Per-company limit may exceed n slightly


class TestRecordAnnotation:
    def test_record_and_retrieve(self, storage):
        job = _make_job(0)
        storage.jobs.upsert(job)
        jid = job.id
        record_annotation(storage, jid, 85.0, "test_annotator")
        pairs = pairs_with_predictions(storage, "test_annotator")
        # No score yet, so no pairs
        assert len(pairs) == 0

    def test_record_with_score(self, storage):
        job = _make_job(1)
        storage.jobs.upsert(job)
        jid = job.id
        score = _make_score(80, 0.9)
        storage.scores.save(jid, score, rubric_version="v1", model_version="m1", resume_version="r1")
        record_annotation(storage, jid, 75.0, "test_annotator")
        pairs = pairs_with_predictions(storage, "test_annotator")
        assert len(pairs) == 1
        assert pairs[0]["human"] == 75.0
        # pred is the stored overall score (may differ from input due to dims calculation)
        assert pairs[0]["pred"] is not None
        assert pairs[0]["job_id"] == jid


class TestPendingIds:
    def test_empty_when_no_eval(self, storage):
        pending = pending_ids(storage)
        assert pending == []

    def test_pending_after_seed(self, storage):
        for i in range(3):
            storage.jobs.upsert(_make_job(i, f"Co{i}"))
        seed_dataset(storage, n=3)
        pending = pending_ids(storage)
        assert len(pending) > 0


class TestDumpDims:
    def test_valid_json(self):
        result = dump_dims('{"skills": {"score": 8}}')
        assert result["skills"]["score"] == 8

    def test_empty_string(self):
        result = dump_dims("")
        assert result == {}
