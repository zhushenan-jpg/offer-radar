"""Interview Prep 工具单元测试."""

import pytest
from unittest.mock import Mock, patch

from jobpilot.models.interview_brief import (
    FollowUp,
    InterviewBrief,
    PredictedQuestion,
    WeakAreaDrill,
)
from jobpilot.tools.interview_prep import InterviewPrep, _compute_cache_key, _hash_data


class TestComputeCacheKey:
    """缓存键计算测试."""

    def test_cache_key_deterministic(self):
        """验证相同输入产生相同缓存键."""
        key1 = _compute_cache_key("job_001", "hash1", "hash2", "model-a")
        key2 = _compute_cache_key("job_001", "hash1", "hash2", "model-a")
        assert key1 == key2

    def test_cache_key_different_inputs(self):
        """验证不同输入产生不同缓存键."""
        key1 = _compute_cache_key("job_001", "hash1", "hash2", "model-a")
        key2 = _compute_cache_key("job_002", "hash1", "hash2", "model-a")
        assert key1 != key2


class TestHashData:
    """哈希计算测试."""

    def test_hash_deterministic(self):
        """验证相同输入产生相同哈希."""
        hash1 = _hash_data("test data")
        hash2 = _hash_data("test data")
        assert hash1 == hash2

    def test_hash_different_inputs(self):
        """验证不同输入产生不同哈希."""
        hash1 = _hash_data("data 1")
        hash2 = _hash_data("data 2")
        assert hash1 != hash2


class TestInterviewPrep:
    """Interview Prep 测试."""

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
        storage.briefs = Mock()
        storage.briefs.save = Mock()
        return storage

    @pytest.fixture
    def sample_brief(self):
        """示例面试速览."""
        return InterviewBrief(
            id="brief_001",
            job_id="job_001",
            company_overview="这是一家云计算公司...",
            tech_stack=["Python", "Kubernetes", "Docker"],
            predicted_questions=[
                PredictedQuestion(
                    id="q_001",
                    question_text="请介绍微服务经验",
                    claim_type="Architecture",
                    probability=0.85,
                    source="jd_direct",
                )
            ],
            followup_protocol=[
                FollowUp(
                    question_id="q_001",
                    followup_text="是你独立设计的吗？",
                    detection_target="验证 Ownership",
                    red_flags=["用'我们'代替'我'"],
                )
            ],
            weak_area_drills=[
                WeakAreaDrill(
                    id="drill_001",
                    target_claim_id="gap_001",
                    drill_questions=["K8s 核心概念"],
                    expected_evidence="能说出核心概念",
                    common_mistakes=["只背概念"],
                )
            ],
            evidence_summary={"Architecture": ["claim_001"]},
            brief_markdown="# 面试速览\n...",
            generation_tokens=200,
            generation_cost=0.10,
        )

    def test_generate_brief_success(self, mock_gateway, mock_storage, sample_brief):
        """测试成功生成面试速览."""
        mock_gateway.json_in.return_value = sample_brief

        prep = InterviewPrep(mock_gateway, mock_storage)
        result = prep.generate_brief(
            job_posting_summary="要求熟悉 Python 和微服务",
            company_research="这是一家云计算公司...",
            claims=[{"id": "claim_001", "claim_type": "Architecture"}],
            gaps=[{"id": "gap_001", "gap_type": "soft_gap"}],
            resume_text="负责后端开发",
            job_id="job_001",
        )

        assert len(result.predicted_questions) == 1
        assert result.predicted_questions[0].probability == 0.85
        assert len(result.followup_protocol) == 1
        assert len(result.weak_area_drills) == 1

    def test_generate_brief_calls_gateway(self, mock_gateway, mock_storage, sample_brief):
        """测试调用网关."""
        mock_gateway.json_in.return_value = sample_brief

        prep = InterviewPrep(mock_gateway, mock_storage)
        prep.generate_brief(
            job_posting_summary="test jd",
            company_research="test research",
            claims=[],
            gaps=[],
            resume_text="test resume",
            job_id="job_001",
        )

        mock_gateway.json_in.assert_called_once()
        call_args = mock_gateway.json_in.call_args
        assert call_args[1]["module"] == "interview_prep"

    def test_generate_brief_saves_to_storage(self, mock_gateway, mock_storage, sample_brief):
        """测试保存到存储."""
        mock_gateway.json_in.return_value = sample_brief

        prep = InterviewPrep(mock_gateway, mock_storage)
        prep.generate_brief(
            job_posting_summary="test jd",
            company_research="test research",
            claims=[],
            gaps=[],
            resume_text="test resume",
            job_id="job_001",
        )

        mock_storage.briefs.save.assert_called_once_with(sample_brief)

    def test_generate_brief_without_storage(self, mock_gateway, sample_brief):
        """测试无存储时不保存."""
        mock_gateway.json_in.return_value = sample_brief

        prep = InterviewPrep(mock_gateway, None)
        result = prep.generate_brief(
            job_posting_summary="test jd",
            company_research="test research",
            claims=[],
            gaps=[],
            resume_text="test resume",
            job_id="job_001",
        )

        assert result is not None

    def test_generate_brief_sets_job_id(self, mock_gateway, mock_storage, sample_brief):
        """测试设置 job_id."""
        mock_gateway.json_in.return_value = sample_brief

        prep = InterviewPrep(mock_gateway, mock_storage)
        result = prep.generate_brief(
            job_posting_summary="test jd",
            company_research="test research",
            claims=[],
            gaps=[],
            resume_text="test resume",
            job_id="job_999",
        )

        assert result.job_id == "job_999"
