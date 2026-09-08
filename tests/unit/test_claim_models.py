"""Claim 数据模型单元测试."""

import pytest
from pydantic import ValidationError

from jobpilot.models.claim import (
    Claim,
    ClaimExtractionResult,
    ClaimStrength,
    ClaimType,
    EvidenceMatrix,
    Gap,
    GapType,
    TextSpan,
)


class TestClaimType:
    """Claim 类型枚举测试."""

    def test_claim_type_values(self):
        """验证 5 种 Claim 类型值正确."""
        assert ClaimType.OWNERSHIP == "Ownership"
        assert ClaimType.METRIC == "Metric"
        assert ClaimType.TECHNICAL == "Technical"
        assert ClaimType.ARCHITECTURE == "Architecture"
        assert ClaimType.RESULT == "Result"

    def test_claim_type_from_string(self):
        """验证从字符串创建 Claim 类型."""
        assert ClaimType("Ownership") == ClaimType.OWNERSHIP
        assert ClaimType("Metric") == ClaimType.METRIC

    def test_claim_type_invalid(self):
        """验证无效 Claim 类型抛出异常."""
        with pytest.raises(ValueError):
            ClaimType("InvalidType")


class TestClaimStrength:
    """Claim 强度枚举测试."""

    def test_strength_values(self):
        """验证 3 种强度值正确."""
        assert ClaimStrength.STRONG == "strong"
        assert ClaimStrength.WEAK == "weak"
        assert ClaimStrength.MISSING == "missing"


class TestGapType:
    """Gap 类型枚举测试."""

    def test_gap_type_values(self):
        """验证 2 种 Gap 类型值正确."""
        assert GapType.HARD_BLOCK == "hard_block"
        assert GapType.SOFT_GAP == "soft_gap"


class TestTextSpan:
    """文本定位测试."""

    def test_valid_span(self):
        """验证有效文本定位."""
        span = TextSpan(start=0, end=10, text="hello world")
        assert span.start == 0
        assert span.end == 10
        assert span.text == "hello world"

    def test_span_start_negative(self):
        """验证起始位置为负数."""
        with pytest.raises(ValidationError):
            TextSpan(start=-1, end=10, text="test")

    def test_span_empty_text(self):
        """验证空文本."""
        with pytest.raises(ValidationError):
            TextSpan(start=0, end=10, text="")


class TestClaim:
    """Claim 模型测试."""

    def test_valid_claim(self):
        """验证有效 Claim."""
        claim = Claim(
            id="claim_001",
            claim_type=ClaimType.METRIC,
            claim_text="将 API 响应时间从 2s 优化到 200ms",
            resume_span=TextSpan(start=0, end=30, text="优化了 API 响应时间"),
            jd_evidence="要求有性能优化经验",
            jd_span=TextSpan(start=100, end=120, text="具备性能优化经验"),
            strength=ClaimStrength.STRONG,
        )
        assert claim.id == "claim_001"
        assert claim.claim_type == ClaimType.METRIC
        assert claim.strength == ClaimStrength.STRONG

    def test_claim_without_jd_evidence(self):
        """验证无 JD 证据的 Claim."""
        claim = Claim(
            id="claim_002",
            claim_type=ClaimType.TECHNICAL,
            claim_text="使用 Python 开发后端",
            resume_span=TextSpan(start=0, end=20, text="使用 Python 开发"),
            strength=ClaimStrength.WEAK,
        )
        assert claim.jd_evidence is None
        assert claim.jd_span is None

    def test_claim_missing_required_field(self):
        """验证缺少必填字段."""
        with pytest.raises(ValidationError):
            Claim(
                claim_type=ClaimType.METRIC,
                claim_text="test",
                # 缺少 id, resume_span, strength
            )


class TestGap:
    """Gap 模型测试."""

    def test_hard_block_gap(self):
        """验证硬性门槛 Gap."""
        gap = Gap(
            id="gap_001",
            gap_type=GapType.HARD_BLOCK,
            jd_requirement="必须有 3 年以上 Python 经验",
            jd_span=TextSpan(start=0, end=20, text="必须有 3 年以上"),
            related_claims=[],
            mitigation=None,
        )
        assert gap.gap_type == GapType.HARD_BLOCK
        assert gap.mitigation is None

    def test_soft_gap_with_mitigation(self):
        """验证软性差距 Gap 有弥补建议."""
        gap = Gap(
            id="gap_002",
            gap_type=GapType.SOFT_GAP,
            jd_requirement="熟悉 Kubernetes",
            jd_span=TextSpan(start=0, end=15, text="熟悉 Kubernetes"),
            related_claims=["claim_003"],
            mitigation="建议补充一个 K8s 相关项目",
        )
        assert gap.gap_type == GapType.SOFT_GAP
        assert gap.mitigation is not None


class TestEvidenceMatrix:
    """证据矩阵测试."""

    def test_valid_evidence_matrix(self):
        """验证有效证据矩阵."""
        matrix = EvidenceMatrix(
            claim_id="claim_001",
            jd_requirement_id="jd_req_1",
            match_status="matched",
        )
        assert matrix.claim_id == "claim_001"
        assert matrix.match_status == "matched"


class TestClaimExtractionResult:
    """Claim 提取结果测试."""

    def test_valid_result(self):
        """验证有效提取结果."""
        result = ClaimExtractionResult(
            id="extract_001",
            job_id="job_001",
            resume_version="v1.0",
            claims=[
                Claim(
                    id="claim_001",
                    claim_type=ClaimType.METRIC,
                    claim_text="test",
                    resume_span=TextSpan(start=0, end=4, text="test"),
                    strength=ClaimStrength.STRONG,
                )
            ],
            gaps=[
                Gap(
                    id="gap_001",
                    gap_type=GapType.SOFT_GAP,
                    jd_requirement="test",
                    jd_span=TextSpan(start=0, end=4, text="test"),
                    mitigation="test",
                )
            ],
            evidence_matrix=[],
            extraction_tokens=100,
            extraction_cost=0.005,
        )
        assert len(result.claims) == 1
        assert len(result.gaps) == 1
        assert result.extraction_tokens == 100

    def test_empty_result(self):
        """验证空提取结果."""
        result = ClaimExtractionResult(
            id="extract_002",
            job_id="job_002",
            resume_version="v1.0",
        )
        assert len(result.claims) == 0
        assert len(result.gaps) == 0
        assert result.extraction_tokens == 0
