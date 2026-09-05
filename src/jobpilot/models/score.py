"""匹配评分模型:overall 由代码按权重重算,不信任模型自报."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

DimKey = Literal["skills", "experience", "constraints", "growth"]
DIMS: tuple[DimKey, ...] = ("skills", "experience", "constraints", "growth")
RUBRIC_WEIGHTS: dict[str, float] = {
    "skills": 0.40,
    "experience": 0.25,
    "constraints": 0.20,
    "growth": 0.15,
}


class Evidence(BaseModel):
    dim: DimKey
    quote: str = Field(
        min_length=2,
        max_length=240,
        description="JD 原文片段,逐字引用,建议 ≤60 字",
    )
    reason: str = Field(min_length=2)


class DimScore(BaseModel):
    score: int = Field(ge=0, le=10)
    evidence: list[Evidence] = Field(min_length=1)


class MatchScore(BaseModel):
    # overall 是派生值:由 _recompute_overall 按权重重算,LLM 无需输出,恒填 0
    overall: float = Field(default=0, ge=0, le=100)
    dims: dict[DimKey, DimScore]
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _recompute_overall(self) -> "MatchScore":
        missing = set(DIMS) - set(self.dims)
        if missing:
            raise ValueError(f"缺少维度: {sorted(missing)}")
        self.overall = round(sum(RUBRIC_WEIGHTS[k] * self.dims[k].score for k in DIMS) * 10, 1)
        return self

    @classmethod
    def from_dims(
        cls,
        scores: dict[DimKey, int],
        *,
        confidence: float,
        summary: str,
    ) -> "MatchScore":
        """测试/离线模式便捷构造:每个维度自动补一条占位证据."""
        return cls(
            overall=0,
            dims={
                k: DimScore(
                    score=v,
                    evidence=[Evidence(dim=k, quote=f"占位证据-{k}", reason="离线模式")],
                )
                for k, v in scores.items()
            },
            confidence=confidence,
            summary=summary,
        )
