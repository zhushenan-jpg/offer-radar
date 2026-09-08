"""Interview Brief 数据模型:面试预测与准备材料."""

from typing import Optional

from pydantic import BaseModel, Field


class PredictedQuestion(BaseModel):
    """预测的面试问题."""

    id: str = Field(..., description="问题 ID")
    question_text: str = Field(min_length=1, description="问题内容")
    claim_type: str = Field(..., description="关联的 Claim 类型")
    related_claim_ids: list[str] = Field(default_factory=list)
    probability: float = Field(ge=0, le=1, description="预测概率")
    source: str = Field(..., description="来源：jd_direct/jd_inferred/company_culture")


class FollowUp(BaseModel):
    """追问协议."""

    question_id: str
    followup_text: str = Field(min_length=1, description="追问内容")
    detection_target: str = Field(min_length=1, description="检测目标")
    red_flags: list[str] = Field(default_factory=list, description="危险信号")


class WeakAreaDrill(BaseModel):
    """弱项练习."""

    id: str = Field(..., description="练习 ID")
    target_claim_id: str
    drill_questions: list[str] = Field(default_factory=list)
    expected_evidence: str = Field(min_length=1, description="期望的回答证据")
    common_mistakes: list[str] = Field(default_factory=list)


class InterviewBrief(BaseModel):
    """面试速览."""

    id: str = Field(..., description="速览 ID")
    job_id: str
    company_overview: str = Field(default="", description="公司背景")
    tech_stack: list[str] = Field(default_factory=list)
    predicted_questions: list[PredictedQuestion] = Field(default_factory=list)
    followup_protocol: list[FollowUp] = Field(default_factory=list)
    weak_area_drills: list[WeakAreaDrill] = Field(default_factory=list)
    evidence_summary: dict[str, list[str]] = Field(
        default_factory=dict, description="按 Claim 类型分组的 Claim ID"
    )
    brief_markdown: str = Field(default="", description="一页纸面试速览（Markdown）")
    generation_tokens: int = Field(0)
    generation_cost: float = Field(0.0)
