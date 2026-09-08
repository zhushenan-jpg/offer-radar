"""Resume Patch 数据模型单元测试."""

import pytest
from pydantic import ValidationError

from jobpilot.models.resume_patch import (
    BulletRewrite,
    HROpener,
    MissingEvidence,
    ResumePatch,
)


class TestBulletRewrite:
    """Bullet 改写建议测试."""

    def test_valid_bullet_rewrite(self):
        """验证有效 Bullet 改写建议."""
        rewrite = BulletRewrite(
            id="rewrite_001",
            original_text="负责后端开发",
            suggested_rewrite="主导后端 API 设计与开发，优化性能提升 50%",
            matched_jd_requirement="有后端开发经验",
            claim_id="claim_001",
        )
        assert rewrite.id == "rewrite_001"
        assert rewrite.original_text == "负责后端开发"

    def test_bullet_rewrite_empty_text(self):
        """验证空文本."""
        with pytest.raises(ValidationError):
            BulletRewrite(
                id="rewrite_001",
                original_text="",
                suggested_rewrite="test",
                matched_jd_requirement="test",
                claim_id="claim_001",
            )


class TestMissingEvidence:
    """缺失证据建议测试."""

    def test_valid_missing_evidence(self):
        """验证有效缺失证据建议."""
        evidence = MissingEvidence(
            id="evidence_001",
            gap_id="gap_001",
            suggested_activity="做一个 Kubernetes 部署项目",
            priority="high",
        )
        assert evidence.id == "evidence_001"
        assert evidence.priority == "high"


class TestHROpener:
    """HR 开场白测试."""

    def test_valid_hr_opener(self):
        """验证有效 HR 开场白."""
        opener = HROpener(
            job_id="job_001",
            opener_text="我是一名有 3 年后端开发经验的工程师...",
            highlight_claim_ids=["claim_001", "claim_002"],
        )
        assert opener.job_id == "job_001"
        assert len(opener.highlight_claim_ids) == 2

    def test_hr_opener_empty_text(self):
        """验证空文本."""
        with pytest.raises(ValidationError):
            HROpener(
                job_id="job_001",
                opener_text="",
            )


class TestResumePatch:
    """简历补丁测试."""

    def test_valid_resume_patch(self):
        """验证有效简历补丁."""
        patch = ResumePatch(
            id="patch_001",
            job_id="job_001",
            bullet_rewrites=[
                BulletRewrite(
                    id="rewrite_001",
                    original_text="负责后端开发",
                    suggested_rewrite="主导后端 API 设计",
                    matched_jd_requirement="有后端开发经验",
                    claim_id="claim_001",
                )
            ],
            missing_evidence=[
                MissingEvidence(
                    id="evidence_001",
                    gap_id="gap_001",
                    suggested_activity="做 K8s 项目",
                    priority="high",
                )
            ],
            hr_opener=HROpener(
                job_id="job_001",
                opener_text="我是一名工程师...",
            ),
            patch_markdown="## 改写建议\n...",
            generation_tokens=100,
            generation_cost=0.05,
        )
        assert len(patch.bullet_rewrites) == 1
        assert len(patch.missing_evidence) == 1
        assert patch.hr_opener is not None

    def test_empty_resume_patch(self):
        """验证空简历补丁."""
        patch = ResumePatch(
            id="patch_002",
            job_id="job_002",
        )
        assert len(patch.bullet_rewrites) == 0
        assert len(patch.missing_evidence) == 0
        assert patch.hr_opener is None
        assert patch.patch_markdown == ""

    def test_resume_patch_serialization(self):
        """验证简历补丁序列化."""
        patch = ResumePatch(
            id="patch_001",
            job_id="job_001",
            bullet_rewrites=[
                BulletRewrite(
                    id="rewrite_001",
                    original_text="负责后端开发",
                    suggested_rewrite="主导后端 API 设计",
                    matched_jd_requirement="有后端开发经验",
                    claim_id="claim_001",
                )
            ],
        )

        # 序列化
        json_str = patch.model_dump_json()
        assert "patch_001" in json_str
        assert "负责后端开发" in json_str

        # 反序列化
        patch2 = ResumePatch.model_validate_json(json_str)
        assert patch2.id == "patch_001"
        assert len(patch2.bullet_rewrites) == 1
