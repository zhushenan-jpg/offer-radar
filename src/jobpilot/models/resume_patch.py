"""Resume Patch 数据模型:简历改写建议与 HR 开场白."""

from typing import Optional

from pydantic import BaseModel, Field


class BulletRewrite(BaseModel):
    """简历 Bullet 改写建议."""

    id: str = Field(..., description="改写建议 ID")
    original_text: str = Field(min_length=1, description="简历原文")
    suggested_rewrite: str = Field(min_length=1, description="改写建议")
    matched_jd_requirement: str = Field(min_length=1, description="匹配的 JD 要求")
    claim_id: str = Field(..., description="关联的 Claim ID")


class MissingEvidence(BaseModel):
    """缺失证据建议."""

    id: str = Field(..., description="建议 ID")
    gap_id: str = Field(..., description="关联的 Gap ID")
    suggested_activity: str = Field(min_length=1, description="建议补充的活动/项目")
    priority: str = Field(..., description="优先级：high/medium/low")


class HROpener(BaseModel):
    """HR 开场白."""

    job_id: str
    opener_text: str = Field(min_length=1, max_length=500, description="一段话开场白")
    highlight_claim_ids: list[str] = Field(default_factory=list, description="突出的 Claim ID 列表")


class ResumePatch(BaseModel):
    """简历补丁."""

    id: str = Field(..., description="补丁 ID")
    job_id: str
    bullet_rewrites: list[BulletRewrite] = Field(default_factory=list)
    missing_evidence: list[MissingEvidence] = Field(default_factory=list)
    hr_opener: Optional[HROpener] = None
    patch_markdown: str = Field(default="", description="可合并的增量内容（Markdown）")
    generation_tokens: int = Field(0)
    generation_cost: float = Field(0.0)
