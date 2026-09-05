"""评测模块测试:指标纯函数 + run_eval 集成(FakeGateway)."""

import pytest

from jobpilot.agents.prompts import RUBRIC_VERSION
from jobpilot.eval.metrics import calibration, compute_metrics, mae, spearman, topk_overlap
from jobpilot.eval.run import EvalError, run_eval
from jobpilot.models.job import JobPosting
from jobpilot.testing import FakeGateway


class TestMetrics:
    def test_spearman_perfect_and_reversed(self):
        assert spearman([10, 20, 30, 40], [1, 2, 3, 4]) == 1.0
        assert spearman([10, 20, 30, 40], [4, 3, 2, 1]) == -1.0

    def test_spearman_insufficient_or_constant(self):
        assert spearman([1, 2], [1, 2]) is None
        assert spearman([5, 5, 5], [1, 2, 3]) is None

    def test_mae(self):
        assert mae([80, 20], [70, 30]) == 10.0
        assert mae([], []) is None

    def test_topk_overlap(self):
        pred = [("a", 90), ("b", 80), ("c", 70)]
        human = [("b", 95), ("a", 85), ("c", 40)]
        assert topk_overlap(pred, human, k=2) == 1.0
        assert topk_overlap(pred, human, k=3) == 1.0

    def test_topk_overlap_partial(self):
        pred = [("a", 90), ("b", 80), ("d", 70)]
        human = [("b", 95), ("a", 85), ("c", 40)]
        assert topk_overlap(pred, human, k=3) == 0.67

    def test_calibration_bins(self):
        bins = calibration([(10, 15), (30, 40), (60, 50), (90, 95)])
        assert bins[0]["n"] == 1 and bins[0]["mean_human"] == 15
        assert bins[3]["mean_human"] == 95


class TestComputeMetrics:
    def test_end_to_end(self):
        pairs = [
            {"job_id": "a", "title": "A", "company": "X", "pred": 90, "human": 80},
            {"job_id": "b", "title": "B", "company": "X", "pred": 60, "human": 55},
            {"job_id": "c", "title": "C", "company": "Y", "pred": 30, "human": 35},
        ]
        m = compute_metrics(pairs, top_k=2)
        assert m["n"] == 3
        assert m["spearman"] == 1.0
        assert m["mae"] == 6.7
        assert m["topk_overlap"] == 1.0


@pytest.fixture()
def eval_db(tmp_path):
    """4 条职位入评测集,人工标注 [80,20,60,40],预置旧版评分."""
    from jobpilot.storage.db import Storage

    storage = Storage.open(tmp_path / "e.db")
    humans = [80, 20, 60, 40]
    for i, h in enumerate(humans):
        jid = f"job{i}".ljust(16, "0")
        storage.jobs.upsert(
            JobPosting(
                id=jid,
                source="manual",
                company=f"C{i}",
                title=f"Role {i}",
                description_md=f"# JD {i}\nPython 开发",
            )
        )
        storage.eval_ds.add(jid)
        # 预置一个旧 rubric 版本的评分 → run_eval 应重评
        storage.conn.execute(
            "INSERT INTO scores(job_id, overall, dims_json, evidence_json, confidence,"
            " summary, rubric_version, model_version, resume_version, review_status, created_at)"
            " VALUES(?, 50, '{}', '[]', 0.5, 'old', 'v0.9', 'old-model', 'r', 'auto', '2026-01-01')",
            (jid,),
        )
        storage.annotations.add(jid, h, "demo")
    storage.conn.commit()
    return storage, humans


class TestRunEval:
    def test_rescores_old_versions_and_writes_report(self, eval_db, tmp_path, cfg):
        storage, humans = eval_db
        gw = FakeGateway(cfg, storage)
        out = tmp_path / "eval-report.md"
        metrics = run_eval(storage, gw, _profile(), out_path=out)

        assert metrics["n"] == 4
        assert metrics["mae"] == mae([75.5] * 4, humans)
        # 旧版本评分被当前 rubric 重评
        for jid in storage.eval_ds.all_ids():
            assert storage.scores.latest_for_job(jid)["rubric_version"] == RUBRIC_VERSION
        # 再跑一次:版本已一致 + 缓存命中 → 不再调用 LLM
        calls_before = len(gw.calls)
        run_eval(storage, gw, _profile(), out_path=out)
        assert len(gw.calls) == calls_before
        text = out.read_text(encoding="utf-8")
        assert "Spearman" in text and "逐条对照" in text

    def test_empty_dataset_raises(self, tmp_path, cfg):
        from jobpilot.storage.db import Storage

        storage = Storage.open(tmp_path / "x.db")
        with pytest.raises(EvalError):
            run_eval(storage, FakeGateway(cfg, storage), _profile(), out_path=tmp_path / "r.md")


def _profile():
    from jobpilot.models.profile import Profile

    return Profile(name="张三", skills=["Python"], years=1, resume_md="简历")
