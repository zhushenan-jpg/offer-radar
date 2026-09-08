"""Interview Prep 工具:基于 JD、公司调研和候选人 Claim，生成面试准备材料."""

from typing import Optional

from jobpilot.agents.interview_prompts import INTERVIEW_PREP_VERSION, SYSTEM_INTERVIEW_PREP
from jobpilot.llm_gateway.gateway import LLMGateway, make_cache_key
from jobpilot.models.interview_brief import InterviewBrief


def _compute_cache_key(
    job_id: str, claims_hash: str, company_research_hash: str, model: str
) -> str:
    """计算缓存键."""
    content = f"{job_id}|{claims_hash}|{company_research_hash}|{INTERVIEW_PREP_VERSION}"
    return make_cache_key(content, model)


def _hash_data(data: str) -> str:
    """计算数据哈希."""
    import hashlib

    return hashlib.sha256(data.encode()).hexdigest()[:16]


class InterviewPrep:
    """Interview Prep."""

    def __init__(self, gateway: LLMGateway, storage=None):
        self.gateway = gateway
        self.storage = storage

    def generate_brief(
        self,
        job_posting_summary: str,
        company_research: str,
        claims: list[dict],
        gaps: list[dict],
        resume_text: str,
        job_id: str,
    ) -> InterviewBrief:
        """生成面试速览.

        Args:
            job_posting_summary: JD 摘要
            company_research: 公司调研报告
            claims: Claim 列表（dict 格式）
            gaps: Gap 列表（dict 格式）
            resume_text: 简历原文
            job_id: 职位 ID

        Returns:
            InterviewBrief: 面试速览
        """
        from jobpilot.agents.interview_prompts import build_interview_prep_prompt

        # 构建 prompt
        prompt = build_interview_prep_prompt(
            job_posting_summary, company_research, claims, gaps, resume_text
        )

        # 计算缓存键
        claims_hash = _hash_data(str(claims))
        company_hash = _hash_data(company_research)
        cache_key = _compute_cache_key(
            job_id, claims_hash, company_hash, self.gateway.cfg.model
        )

        # 调用 LLM
        result = self.gateway.json_in(
            InterviewBrief,
            prompt,
            system=SYSTEM_INTERVIEW_PREP,
            cache_key=cache_key,
            module="interview_prep",
        )

        # 确保 job_id 正确
        result.job_id = job_id

        # 保存到数据库
        if self.storage:
            self.storage.briefs.save(result)

        return result


def generate_interview_brief(
    gateway: LLMGateway,
    storage,
    job_posting_summary: str,
    company_research: str,
    claims: list[dict],
    gaps: list[dict],
    resume_text: str,
    job_id: str,
) -> InterviewBrief:
    """便捷函数:生成面试速览并保存."""
    prep = InterviewPrep(gateway, storage)
    return prep.generate_brief(
        job_posting_summary, company_research, claims, gaps, resume_text, job_id
    )
