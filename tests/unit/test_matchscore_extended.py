"""MatchScore 扩展模型单元测试."""

import pytest

from jobpilot.models.claim import (
    Claim,
    ClaimStrength,
    ClaimType,
    EvidenceMatrix,
    Gap,
    GapType,
    TextSpan,
)
from jobpilot.models.score import MatchScore


class TestMatchScoreWithClaims:
    """MatchScore 与 Claim 集成测试."""

    def test_matchscore_with_claims(self):
        """验证 MatchScore 可以包含 Claim."""
        score = MatchScore.from_dims(
            scores={"skills": 8, "experience": 6, "constraints": 9, "growth": 5},
            confidence=0.8,
            summary="测试",
        )

        # 添加 Claim
        score.claims = [
            Claim(
                id="claim_001",
                claim_type=ClaimType.METRIC,
                claim_text="将 API 响应时间从 2s 优化到 200ms",
                resume_span=TextSpan(start=0, end=30, text="优化了 API 响应时间"),
                strength=ClaimStrength.STRONG,
            )
        ]

        assert len(score.claims) == 1
        assert score.claims[0].claim_type == ClaimType.METRIC

    def test_matchscore_with_gaps(self):
        """验证 MatchScore 可以包含 Gap."""
        score = MatchScore.from_dims(
            scores={"skills": 8, "experience": 6, "constraints": 9, "growth": 5},
            confidence=0.8,
            summary="测试",
        )

        # 添加 Gap
        score.gaps = [
            Gap(
                id="gap_001",
                gap_type=GapType.SOFT_GAP,
                jd_requirement="熟悉 Kubernetes",
                jd_span=TextSpan(start=0, end=15, text="熟悉 Kubernetes"),
                mitigation="建议补充 K8s 项目经验",
            )
        ]

        assert len(score.gaps) == 1
        assert score.gaps[0].gap_type == GapType.SOFT_GAP

    def test_matchscore_with_evidence_matrix(self):
        """验证 MatchScore 可以包含 EvidenceMatrix."""
        score = MatchScore.from_dims(
            scores={"skills": 8, "experience": 6, "constraints": 9, "growth": 5},
            confidence=0.8,
            summary="测试",
        )

        # 添加 EvidenceMatrix
        score.evidence_matrix = [
            EvidenceMatrix(
                claim_id="claim_001",
                jd_requirement_id="jd_req_1",
                match_status="matched",
            )
        ]

        assert len(score.evidence_matrix) == 1
        assert score.evidence_matrix[0].match_status == "matched"

    def test_matchscore_default_empty_claims(self):
        """验证默认情况下 claims 为空列表."""
        score = MatchScore.from_dims(
            scores={"skills": 8, "experience": 6, "constraints": 9, "growth": 5},
            confidence=0.8,
            summary="测试",
        )

        assert score.claims == []
        assert score.gaps == []
        assert score.evidence_matrix == []

    def test_matchscore_serialization_with_claims(self):
        """验证包含 Claim 的 MatchScore 可以序列化."""
        score = MatchScore.from_dims(
            scores={"skills": 8, "experience": 6, "constraints": 9, "growth": 5},
            confidence=0.8,
            summary="测试",
        )

        score.claims = [
            Claim(
                id="claim_001",
                claim_type=ClaimType.TECHNICAL,
                claim_text="使用 Python 开发",
                resume_span=TextSpan(start=0, end=20, text="使用 Python 开发"),
                strength=ClaimStrength.STRONG,
            )
        ]

        # 序列化
        json_str = score.model_dump_json()
        assert "claim_001" in json_str
        assert "Technical" in json_str

        # 反序列化
        score2 = MatchScore.model_validate_json(json_str)
        assert len(score2.claims) == 1
        assert score2.claims[0].id == "claim_001"
