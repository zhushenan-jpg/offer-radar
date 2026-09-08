"""Matcher 与 Claim Extractor 集成测试."""

import pytest
from unittest.mock import Mock, patch

from jobpilot.models.claim import (
    Claim,
    ClaimStrength,
    ClaimType,
    Gap,
    GapType,
    TextSpan,
)
from jobpilot.models.profile import Profile
from jobpilot.models.score import MatchScore


class TestMatcherClaimIntegration:
    """Matcher 与 Claim Extractor 集成测试."""

    @pytest.fixture
    def mock_gateway(self):
        """创建 mock 网关."""
        gateway = Mock()
        gateway.cfg.model = "test-model"
        gateway.json_in = Mock()
        return gateway

    @pytest.fixture
    def mock_storage(self):
        """创建 mock 存储."""
        storage = Mock()
        storage.scores = Mock()
        storage.scores.save = Mock()
        storage.claims = Mock()
        storage.claims.save = Mock()
        return storage

    @pytest.fixture
    def sample_profile(self):
        """示例用户档案."""
        return Profile(
            name="测试用户",
            resume_md="负责后端开发，将 API 响应时间从 2s 优化到 200ms",
            resume_version="v1.0",
            skills=["Python", "Redis"],
        )

    @pytest.fixture
    def sample_score(self):
        """示例评分结果."""
        return MatchScore.from_dims(
            scores={"skills": 8, "experience": 6, "constraints": 9, "growth": 5},
            confidence=0.8,
            summary="整体匹配良好",
        )

    @pytest.fixture
    def sample_claim_result(self):
        """示例 Claim 提取结果."""
        from jobpilot.models.claim import ClaimExtractionResult

        return ClaimExtractionResult(
            id="extract_001",
            job_id="job_001",
            resume_version="v1.0",
            claims=[
                Claim(
                    id="claim_001",
                    claim_type=ClaimType.METRIC,
                    claim_text="将 API 响应时间从 2s 优化到 200ms",
                    resume_span=TextSpan(start=0, end=30, text="优化了 API 响应时间"),
                    strength=ClaimStrength.STRONG,
                )
            ],
            gaps=[
                Gap(
                    id="gap_001",
                    gap_type=GapType.SOFT_GAP,
                    jd_requirement="熟悉 Kubernetes",
                    jd_span=TextSpan(start=0, end=15, text="熟悉 Kubernetes"),
                    mitigation="建议补充 K8s 项目经验",
                )
            ],
            evidence_matrix=[],
            extraction_tokens=100,
            extraction_cost=0.005,
        )

    def test_score_and_store_with_claims(
        self, mock_gateway, mock_storage, sample_profile, sample_score, sample_claim_result
    ):
        """测试评分并提取 Claim."""
        from jobpilot.agents.matcher import score_and_store

        # Mock 评分结果
        mock_gateway.json_in.return_value = sample_score

        # Mock Claim 提取
        with patch("jobpilot.agents.matcher.ClaimExtractor") as MockExtractor:
            MockExtractor.return_value.extract.return_value = sample_claim_result

            result = score_and_store(
                mock_gateway,
                mock_storage,
                sample_profile,
                "测试 JD",
                parsed_jd={"skills": ["Python", "Kubernetes"]},
                job_id="job_001",
                extract_claims=True,
            )

        assert len(result.claims) == 1
        assert result.claims[0].claim_type == ClaimType.METRIC
        assert len(result.gaps) == 1
        assert result.gaps[0].gap_type == GapType.SOFT_GAP

    def test_score_and_store_without_claims(
        self, mock_gateway, mock_storage, sample_profile, sample_score
    ):
        """测试评分不提取 Claim."""
        from jobpilot.agents.matcher import score_and_store

        mock_gateway.json_in.return_value = sample_score

        result = score_and_store(
            mock_gateway,
            mock_storage,
            sample_profile,
            "测试 JD",
            parsed_jd=None,
            job_id="job_001",
            extract_claims=False,
        )

        assert result.claims == []
        assert result.gaps == []

    def test_score_and_store_claims_saved(
        self, mock_gateway, mock_storage, sample_profile, sample_score, sample_claim_result
    ):
        """测试 Claim 保存到存储."""
        from jobpilot.agents.matcher import score_and_store

        mock_gateway.json_in.return_value = sample_score

        with patch("jobpilot.agents.matcher.ClaimExtractor") as MockExtractor:
            MockExtractor.return_value.extract.return_value = sample_claim_result

            score_and_store(
                mock_gateway,
                mock_storage,
                sample_profile,
                "测试 JD",
                parsed_jd={"skills": ["Python", "Kubernetes"]},
                job_id="job_001",
                extract_claims=True,
            )

        # 验证评分保存
        mock_storage.scores.save.assert_called_once()

        # 验证 Claim 保存（通过 ClaimExtractor）
        MockExtractor.return_value.extract.assert_called_once()
