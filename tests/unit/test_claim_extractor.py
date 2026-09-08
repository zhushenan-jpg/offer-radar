"""Claim 提取工具单元测试."""

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
from jobpilot.tools.claim_extractor import ClaimExtractor, _compute_cache_key


class TestComputeCacheKey:
    """缓存键计算测试."""

    def test_cache_key_deterministic(self):
        """验证相同输入产生相同缓存键."""
        key1 = _compute_cache_key("test jd", "v1.0", "model-a")
        key2 = _compute_cache_key("test jd", "v1.0", "model-a")
        assert key1 == key2

    def test_cache_key_different_inputs(self):
        """验证不同输入产生不同缓存键."""
        key1 = _compute_cache_key("test jd 1", "v1.0", "model-a")
        key2 = _compute_cache_key("test jd 2", "v1.0", "model-a")
        assert key1 != key2

    def test_cache_key_includes_version(self):
        """验证缓存键包含版本号."""
        key1 = _compute_cache_key("test jd", "v1.0", "model-a")
        key2 = _compute_cache_key("test jd", "v2.0", "model-a")
        assert key1 != key2


class TestClaimExtractor:
    """Claim 提取器测试."""

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
        storage.claims = Mock()
        storage.claims.save = Mock()
        return storage

    @pytest.fixture
    def sample_result(self):
        """示例提取结果."""
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
                    jd_evidence="要求有性能优化经验",
                    jd_span=TextSpan(start=100, end=120, text="具备性能优化经验"),
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

    def test_extract_success(self, mock_gateway, mock_storage, sample_result):
        """测试成功提取 Claim."""
        mock_gateway.json_in.return_value = sample_result

        extractor = ClaimExtractor(mock_gateway, mock_storage)
        result = extractor.extract(
            resume_text="负责后端开发，将 API 响应时间从 2s 优化到 200ms",
            jd_text="要求有性能优化经验，熟悉 Kubernetes",
            parsed_jd={"skills": ["Python", "Kubernetes"]},
            resume_version="v1.0",
            job_id="job_001",
        )

        assert len(result.claims) == 1
        assert result.claims[0].claim_type == ClaimType.METRIC
        assert len(result.gaps) == 1
        assert result.gaps[0].gap_type == GapType.SOFT_GAP
        assert result.job_id == "job_001"

    def test_extract_calls_gateway(self, mock_gateway, mock_storage, sample_result):
        """测试调用网关."""
        mock_gateway.json_in.return_value = sample_result

        extractor = ClaimExtractor(mock_gateway, mock_storage)
        extractor.extract(
            resume_text="test resume",
            jd_text="test jd",
            parsed_jd={},
            resume_version="v1.0",
            job_id="job_001",
        )

        mock_gateway.json_in.assert_called_once()
        call_args = mock_gateway.json_in.call_args
        assert call_args[1]["module"] == "claim_extractor"

    def test_extract_saves_to_storage(self, mock_gateway, mock_storage, sample_result):
        """测试保存到存储."""
        mock_gateway.json_in.return_value = sample_result

        extractor = ClaimExtractor(mock_gateway, mock_storage)
        extractor.extract(
            resume_text="test resume",
            jd_text="test jd",
            parsed_jd={},
            resume_version="v1.0",
            job_id="job_001",
        )

        mock_storage.claims.save.assert_called_once_with(sample_result)

    def test_extract_without_storage(self, mock_gateway, sample_result):
        """测试无存储时不保存."""
        mock_gateway.json_in.return_value = sample_result

        extractor = ClaimExtractor(mock_gateway, None)
        result = extractor.extract(
            resume_text="test resume",
            jd_text="test jd",
            parsed_jd={},
            resume_version="v1.0",
            job_id="job_001",
        )

        assert result is not None

    def test_extract_sets_job_id(self, mock_gateway, mock_storage, sample_result):
        """测试设置 job_id."""
        mock_gateway.json_in.return_value = sample_result

        extractor = ClaimExtractor(mock_gateway, mock_storage)
        result = extractor.extract(
            resume_text="test resume",
            jd_text="test jd",
            parsed_jd={},
            resume_version="v1.0",
            job_id="job_999",
        )

        assert result.job_id == "job_999"
