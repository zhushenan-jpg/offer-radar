import pytest
from pydantic import ValidationError

from jobpilot.models.job import JobPosting
from jobpilot.models.profile import Profile, load_profile
from jobpilot.models.score import DIMS, RUBRIC_WEIGHTS, MatchScore


def make_dims(skills=8, experience=6, constraints=9, growth=5):
    def ev(dim):
        return [{"dim": dim, "quote": f"quote-{dim}", "reason": "理由"}]

    return {
        "skills": {"score": skills, "evidence": ev("skills")},
        "experience": {"score": experience, "evidence": ev("experience")},
        "constraints": {"score": constraints, "evidence": ev("constraints")},
        "growth": {"score": growth, "evidence": ev("growth")},
    }


class TestMatchScore:
    def test_overall_recomputed_from_dims(self):
        s = MatchScore(dims=make_dims(8, 6, 9, 5), confidence=0.8, summary="ok", overall=0)
        expected = (0.4 * 8 + 0.25 * 6 + 0.2 * 9 + 0.15 * 5) * 10
        assert s.overall == pytest.approx(expected, abs=0.1)

    def test_overall_ignores_model_claim(self):
        s = MatchScore(dims=make_dims(0, 0, 0, 0), confidence=0.1, summary="ok", overall=99)
        assert s.overall == 0.0

    def test_missing_dim_rejected(self):
        dims = make_dims()
        dims.pop("growth")
        with pytest.raises(ValidationError):
            MatchScore(dims=dims, confidence=0.5, summary="ok", overall=0)

    def test_dim_without_evidence_rejected(self):
        dims = make_dims()
        dims["skills"]["evidence"] = []
        with pytest.raises(ValidationError):
            MatchScore(dims=dims, confidence=0.5, summary="ok", overall=0)

    def test_weights_sum_to_one(self):
        assert pytest.approx(sum(RUBRIC_WEIGHTS.values())) == 1.0
        assert set(RUBRIC_WEIGHTS) == set(DIMS)


class TestJobPosting:
    def test_compute_id_stable_and_normalized(self):
        a = JobPosting.compute_id("manual", "Stripe", "Backend  Intern ", "San Francisco")
        b = JobPosting.compute_id("manual", "stripe", "backend intern", "san francisco")
        assert a == b
        assert len(a) == 16

    def test_source_literal(self):
        with pytest.raises(ValidationError):
            JobPosting(
                id="x" * 16,
                source="linkedin",
                company="c",
                title="t",
                location="l",
                description_md="d",
            )


class TestProfile:
    def test_resume_version_auto(self):
        p = Profile(name="张三", skills=["Python"], years=1.0, resume_md="简历内容")
        assert len(p.resume_version) == 12

    def test_load_profile_yaml(self, tmp_path):
        f = tmp_path / "profile.yaml"
        f.write_text(
            "name: 张三\nskills: [Python]\nyears: 1\nresume_md: 内容\n"
            "desired:\n  roles: [后端]\n  remote_ok: true\n",
            encoding="utf-8",
        )
        p = load_profile(f)
        assert p.desired.roles == ["后端"]
