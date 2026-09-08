"""Gap Advisor 工具:基于 Gap 分析，生成简历修改建议和 HR 开场白."""

from typing import Optional

from jobpilot.agents.gap_prompts import GAP_ADVISOR_VERSION, SYSTEM_GAP_ADVISOR
from jobpilot.llm_gateway.gateway import LLMGateway, make_cache_key
from jobpilot.models.resume_patch import ResumePatch


def _compute_cache_key(job_id: str, claims_hash: str, gaps_hash: str, model: str) -> str:
    """计算缓存键."""
    content = f"{job_id}|{claims_hash}|{gaps_hash}|{GAP_ADVISOR_VERSION}"
    return make_cache_key(content, model)


def _hash_claims_gaps(claims: list[dict], gaps: list[dict]) -> str:
    """计算 claims 和 gaps 的哈希."""
    import hashlib
    import json

    content = json.dumps({"claims": claims, "gaps": gaps}, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class GapAdvisor:
    """Gap Advisor."""

    def __init__(self, gateway: LLMGateway, storage=None):
        self.gateway = gateway
        self.storage = storage

    def generate_patch(
        self,
        resume_text: str,
        job_posting_summary: str,
        claims: list[dict],
        gaps: list[dict],
        job_id: str,
    ) -> ResumePatch:
        """生成简历补丁.

        Args:
            resume_text: 简历原文
            job_posting_summary: JD 摘要
            claims: Claim 列表（dict 格式）
            gaps: Gap 列表（dict 格式）
            job_id: 职位 ID

        Returns:
            ResumePatch: 简历补丁
        """
        from jobpilot.agents.gap_prompts import build_gap_advisor_prompt

        # 构建 prompt
        prompt = build_gap_advisor_prompt(resume_text, job_posting_summary, claims, gaps)

        # 计算缓存键
        claims_hash = _hash_claims_gaps(claims, gaps)
        gaps_hash = _hash_claims_gaps([], gaps)
        cache_key = _compute_cache_key(job_id, claims_hash, gaps_hash, self.gateway.cfg.model)

        # 调用 LLM
        result = self.gateway.json_in(
            ResumePatch,
            prompt,
            system=SYSTEM_GAP_ADVISOR,
            cache_key=cache_key,
            module="gap_advisor",
        )

        # 确保 job_id 正确
        result.job_id = job_id

        # 保存到数据库
        if self.storage:
            self.storage.patches.save(result)

        return result


def generate_resume_patch(
    gateway: LLMGateway,
    storage,
    resume_text: str,
    job_posting_summary: str,
    claims: list[dict],
    gaps: list[dict],
    job_id: str,
) -> ResumePatch:
    """便捷函数:生成简历补丁并保存."""
    advisor = GapAdvisor(gateway, storage)
    return advisor.generate_patch(resume_text, job_posting_summary, claims, gaps, job_id)
