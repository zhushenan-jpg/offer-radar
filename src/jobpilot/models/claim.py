"""Claim 证据链数据模型:从简历中提取的可验证声明与 JD 差距分析."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    """Claim 五分类."""

    OWNERSHIP = "Ownership"  # 个人负责/主导
    METRIC = "Metric"  # 可量化指标
    TECHNICAL = "Technical"  # 技术能力/工具
    ARCHITECTURE = "Architecture"  # 系统设计/架构
    RESULT = "Result"  # 成果/影响


class ClaimStrength(str, Enum):
    """证据强度."""

    STRONG = "strong"  # 强证据:明确、具体、可验证
    WEAK = "weak"  # 弱证据:模糊、笼统、缺乏细节
    MISSING = "missing"  # 缺失:无证据


class GapType(str, Enum):
    """Gap 分类."""

    HARD_BLOCK = "hard_block"  # 硬性门槛不满足(如学历、必须技能)
    SOFT_GAP = "soft_gap"  # 软性差距(如加分项、经验不足)


class TextSpan(BaseModel):
    """文本定位."""

    start: int = Field(ge=0, description="起始字符位置")
    end: int = Field(ge=0, description="结束字符位置")
    text: str = Field(min_length=1, description="原文内容")


class Claim(BaseModel):
    """可验证声明."""

    id: str = Field(..., description="Claim ID，格式：claim_{job_id}_{序号}")
    claim_type: ClaimType
    claim_text: str = Field(min_length=1, description="声明内容")
    resume_span: TextSpan = Field(..., description="简历原文定位")
    jd_evidence: Optional[str] = Field(None, description="JD 中对应的证据")
    jd_span: Optional[TextSpan] = Field(None, description="JD 原文定位")
    strength: ClaimStrength


class Gap(BaseModel):
    """JD 要求与简历的差距."""

    id: str = Field(..., description="Gap ID，格式：gap_{job_id}_{序号}")
    gap_type: GapType
    jd_requirement: str = Field(min_length=1, description="JD 中的要求原文")
    jd_span: TextSpan = Field(..., description="JD 原文定位")
    related_claims: list[str] = Field(default_factory=list, description="关联的 Claim ID 列表")
    mitigation: Optional[str] = Field(None, description="弥补建议（soft_gap 时必填）")


class EvidenceMatrix(BaseModel):
    """证据矩阵:Claim 与 JD 要求的映射关系."""

    claim_id: str
    jd_requirement_id: str
    match_status: str = Field(..., description="匹配状态：matched/partial/missing")


class ClaimExtractionResult(BaseModel):
    """Claim 提取结果."""

    id: str = Field(..., description="提取结果 ID")
    job_id: str
    resume_version: str
    claims: list[Claim] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    evidence_matrix: list[EvidenceMatrix] = Field(default_factory=list)
    extraction_tokens: int = Field(0, description="提取消耗的 token 数")
    extraction_cost: float = Field(0.0, description="提取消耗的费用（元）")
