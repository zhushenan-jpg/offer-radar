"""Gap Advisor 工具单元测试."""

import pytest
from unittest.mock import Mock, patch

from jobpilot.models.resume_patch import (
    BulletRewrite,
    HROpener,
    MissingEvidence,
    ResumePatch,
)
from jobpilot.tools.gap_advisor import GapAdvisor, _compute_cache_key, _hash_claims_gaps


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


class TestHashClaimsGaps:
    """哈希计算测试."""

    def test_hash_deterministic(self):
        """验证相同输入产生相同哈希."""
        claims = [{"id": "claim_001", "claim_type": "Metric"}]
        gaps = [{"id": "gap_001", "gap_type": "soft_gap"}]
        hash1 = _hash_claims_gaps(claims, gaps)
        hash2 = _hash_claims_gaps(claims, gaps)
        assert hash1 == hash2

    def test_hash_different_inputs(self):
        """验证不同输入产生不同哈希."""
        claims1 = [{"id": "claim_001"}]
        claims2 = [{"id": "claim_002"}]
        hash1 = _hash_claims_gaps(claims1, [])
        hash2 = _hash_claims_gaps(claims2, [])
        assert hash1 != hash2


class TestGapAdvisor:
    """Gap Advisor 测试."""

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
        storage.patches = Mock()
        storage.patches.save = Mock()
        return storage

    @pytest.fixture
    def sample_patch(self):
        """示例简历补丁."""
        return ResumePatch(
            id="patch_001",
            job_id="job_001",
            bullet_rewrites=[
                BulletRewrite(
                    id="rewrite_001",
                    original_text="负责后端开发",
                    suggested_rewrite="主导后端 API 设计与开发，优化性能提升 50%",
                    matched_jd_requirement="有后端开发经验",
                    claim_id="claim_001",
                )
            ],
            missing_evidence=[
                MissingEvidence(
                    id="evidence_001",
                    gap_id="gap_001",
                    suggested_activity="做一个 Kubernetes 部署项目",
                    priority="high",
                )
            ],
            hr_opener=HROpener(
                job_id="job_001",
                opener_text="我是一名有 3 年后端开发经验的工程师...",
                highlight_claim_ids=["claim_001"],
            ),
            patch_markdown="## 改写建议\n...",
            generation_tokens=100,
            generation_cost=0.05,
        )

    def test_generate_patch_success(self, mock_gateway, mock_storage, sample_patch):
        """测试成功生成简历补丁."""
        mock_gateway.json_in.return_value = sample_patch

        advisor = GapAdvisor(mock_gateway, mock_storage)
        result = advisor.generate_patch(
            resume_text="负责后端开发",
            job_posting_summary="要求有后端开发经验",
            claims=[{"id": "claim_001", "claim_type": "Metric"}],
            gaps=[{"id": "gap_001", "gap_type": "soft_gap"}],
            job_id="job_001",
        )

        assert len(result.bullet_rewrites) == 1
        assert result.bullet_rewrites[0].original_text == "负责后端开发"
        assert len(result.missing_evidence) == 1
        assert result.hr_opener is not None

    def test_generate_patch_calls_gateway(self, mock_gateway, mock_storage, sample_patch):
        """测试调用网关."""
        mock_gateway.json_in.return_value = sample_patch

        advisor = GapAdvisor(mock_gateway, mock_storage)
        advisor.generate_patch(
            resume_text="test resume",
            job_posting_summary="test jd",
            claims=[],
            gaps=[],
            job_id="job_001",
        )

        mock_gateway.json_in.assert_called_once()
        call_args = mock_gateway.json_in.call_args
        assert call_args[1]["module"] == "gap_advisor"

    def test_generate_patch_saves_to_storage(self, mock_gateway, mock_storage, sample_patch):
        """测试保存到存储."""
        mock_gateway.json_in.return_value = sample_patch

        advisor = GapAdvisor(mock_gateway, mock_storage)
        advisor.generate_patch(
            resume_text="test resume",
            job_posting_summary="test jd",
            claims=[],
            gaps=[],
            job_id="job_001",
        )

        mock_storage.patches.save.assert_called_once_with(sample_patch)

    def test_generate_patch_without_storage(self, mock_gateway, sample_patch):
        """测试无存储时不保存."""
        mock_gateway.json_in.return_value = sample_patch

        advisor = GapAdvisor(mock_gateway, None)
        result = advisor.generate_patch(
            resume_text="test resume",
            job_posting_summary="test jd",
            claims=[],
            gaps=[],
            job_id="job_001",
        )

        assert result is not None

    def test_generate_patch_sets_job_id(self, mock_gateway, mock_storage, sample_patch):
        """测试设置 job_id."""
        mock_gateway.json_in.return_value = sample_patch

        advisor = GapAdvisor(mock_gateway, mock_storage)
        result = advisor.generate_patch(
            resume_text="test resume",
            job_posting_summary="test jd",
            claims=[],
            gaps=[],
            job_id="job_999",
        )

        assert result.job_id == "job_999"
