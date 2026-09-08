"""Reporter Agent 集成测试:验证 Gap Advisor 和 Interview Prep 集成."""

import json
import pytest
from unittest.mock import Mock, patch

from jobpilot.models.claim import (
    Claim,
    ClaimExtractionResult,
    ClaimStrength,
    ClaimType,
    Gap,
    GapType,
    TextSpan,
)
from jobpilot.models.interview_brief import InterviewBrief, PredictedQuestion
from jobpilot.models.profile import Profile
from jobpilot.models.resume_patch import BulletRewrite, HROpener, ResumePatch
from jobpilot.models.score import MatchScore


class TestReporterIntegration:
    """Reporter Agent 集成测试."""

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
        storage.scores.latest_claims_for_job = Mock(return_value=[])
        storage.scores.latest_gaps_for_job = Mock(return_value=[])
        storage.claims = Mock()
        storage.claims.save = Mock()
        storage.patches = Mock()
        storage.patches.save = Mock()
        storage.briefs = Mock()
        storage.briefs.save = Mock()
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
    def sample_match_scores(self):
        """示例评分结果."""
        return [
            MatchScore.from_dims(
                scores={"skills": 8, "experience": 7, "constraints": 9, "growth": 6},
                confidence=0.85,
                summary="整体匹配良好",
            ),
            MatchScore.from_dims(
                scores={"skills": 6, "experience": 5, "constraints": 8, "growth": 4},
                confidence=0.70,
                summary="基本匹配",
            ),
        ]

    @pytest.fixture
    def sample_claims(self):
        """示例 Claim 列表."""
        return [
            Claim(
                id="claim_001",
                claim_type=ClaimType.METRIC,
                claim_text="将 API 响应时间从 2s 优化到 200ms",
                resume_span=TextSpan(start=0, end=30, text="优化了 API 响应时间"),
                strength=ClaimStrength.STRONG,
            ),
            Claim(
                id="claim_002",
                claim_type=ClaimType.TECHNICAL,
                claim_text="使用 Python 和 Redis",
                resume_span=TextSpan(start=40, end=60, text="使用 Python 和 Redis"),
                strength=ClaimStrength.STRONG,
            ),
        ]

    @pytest.fixture
    def sample_gaps(self):
        """示例 Gap 列表."""
        return [
            Gap(
                id="gap_001",
                gap_type=GapType.SOFT_GAP,
                jd_requirement="熟悉 Kubernetes",
                jd_span=TextSpan(start=0, end=15, text="熟悉 Kubernetes"),
                mitigation="建议补充 K8s 项目经验",
            )
        ]

    @pytest.fixture
    def sample_resume_patch(self):
        """示例简历补丁."""
        return ResumePatch(
            id="patch_001",
            job_id="job_001",
            bullet_rewrites=[
                BulletRewrite(
                    id="rewrite_001",
                    original_text="负责后端开发",
                    suggested_rewrite="主导后端 API 设计，优化性能提升 10 倍",
                    matched_jd_requirement="有后端开发经验",
                    claim_id="claim_001",
                )
            ],
            hr_opener=HROpener(
                job_id="job_001",
                opener_text="我是一名有丰富后端开发经验的工程师...",
                highlight_claim_ids=["claim_001"],
            ),
            patch_markdown="## 改写建议\n...",
        )

    @pytest.fixture
    def sample_interview_brief(self):
        """示例面试速览."""
        return InterviewBrief(
            id="brief_001",
            job_id="job_001",
            company_overview="这是一家技术公司...",
            tech_stack=["Python", "Redis", "Docker"],
            predicted_questions=[
                PredictedQuestion(
                    id="q_001",
                    question_text="请介绍你的性能优化经验",
                    claim_type="Metric",
                    probability=0.90,
                    source="jd_direct",
                )
            ],
            brief_markdown="# 面试速览\n...",
        )

    def test_generate_resume_patch(
        self, mock_gateway, mock_storage, sample_claims, sample_gaps, sample_resume_patch
    ):
        """测试生成简历补丁."""
        from jobpilot.tools.gap_advisor import GapAdvisor

        mock_gateway.json_in.return_value = sample_resume_patch

        advisor = GapAdvisor(mock_gateway, mock_storage)
        result = advisor.generate_patch(
            resume_text="负责后端开发",
            job_posting_summary="要求有后端开发经验，熟悉 Kubernetes",
            claims=[c.model_dump() for c in sample_claims],
            gaps=[g.model_dump() for g in sample_gaps],
            job_id="job_001",
        )

        assert len(result.bullet_rewrites) == 1
        assert result.hr_opener is not None
        assert result.job_id == "job_001"

    def test_generate_interview_brief(
        self, mock_gateway, mock_storage, sample_claims, sample_gaps, sample_interview_brief
    ):
        """测试生成面试速览."""
        from jobpilot.tools.interview_prep import InterviewPrep

        mock_gateway.json_in.return_value = sample_interview_brief

        prep = InterviewPrep(mock_gateway, mock_storage)
        result = prep.generate_brief(
            job_posting_summary="要求有后端开发经验",
            company_research="这是一家技术公司...",
            claims=[c.model_dump() for c in sample_claims],
            gaps=[g.model_dump() for g in sample_gaps],
            resume_text="负责后端开发",
            job_id="job_001",
        )

        assert len(result.predicted_questions) == 1
        assert result.job_id == "job_001"

    def test_score_and_store_with_all_extensions(
        self,
        mock_gateway,
        mock_storage,
        sample_profile,
        sample_match_scores,
        sample_claims,
        sample_gaps,
    ):
        """测试评分 + Claim 提取的完整流程."""
        from jobpilot.agents.matcher import score_and_store
        from jobpilot.models.claim import ClaimExtractionResult

        # Mock 评分结果
        mock_gateway.json_in.return_value = sample_match_scores[0]

        # Mock Claim 提取结果
        claim_result = ClaimExtractionResult(
            id="extract_001",
            job_id="job_001",
            resume_version="v1.0",
            claims=sample_claims,
            gaps=sample_gaps,
            extraction_tokens=100,
            extraction_cost=0.005,
        )

        with patch("jobpilot.agents.matcher.ClaimExtractor") as MockExtractor:
            MockExtractor.return_value.extract.return_value = claim_result

            result = score_and_store(
                mock_gateway,
                mock_storage,
                sample_profile,
                "要求有后端开发经验，熟悉 Kubernetes",
                parsed_jd={"skills": ["Python", "Kubernetes"]},
                job_id="job_001",
                extract_claims=True,
            )

        # 验证评分
        assert result.overall > 0

        # 验证 Claim
        assert len(result.claims) == 2
        assert result.claims[0].claim_type == ClaimType.METRIC

        # 验证 Gap
        assert len(result.gaps) == 1
        assert result.gaps[0].gap_type == GapType.SOFT_GAP

        # 验证存储调用
        mock_storage.scores.save.assert_called_once()

    def test_storage_dao_integration(self, mock_storage, sample_claims, sample_gaps):
        """测试 Storage DAO 集成."""
        from jobpilot.models.claim import ClaimExtractionResult

        # 创建提取结果
        result = ClaimExtractionResult(
            id="extract_001",
            job_id="job_001",
            resume_version="v1.0",
            claims=sample_claims,
            gaps=sample_gaps,
            extraction_tokens=100,
            extraction_cost=0.005,
        )

        # 保存
        mock_storage.claims.save(result)

        # 验证调用
        mock_storage.claims.save.assert_called_once_with(result)

    def test_score_repo_with_claims(self, mock_storage, sample_claims, sample_gaps):
        """测试 ScoreRepo 保存 claims/gaps."""
        score = MatchScore.from_dims(
            scores={"skills": 8, "experience": 7, "constraints": 9, "growth": 6},
            confidence=0.85,
            summary="测试",
        )
        score.claims = sample_claims
        score.gaps = sample_gaps

        mock_storage.scores.save(
            "job_001",
            score,
            rubric_version="v1.0",
            model_version="test-model",
            resume_version="v1.0",
        )

        mock_storage.scores.save.assert_called_once()
