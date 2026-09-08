"""Claim 提取工具:从简历中提取可验证声明，与 JD 要求进行匹配，识别差距."""

import hashlib
from typing import Optional

from jobpilot.agents.claim_prompts import CLAIM_EXTRACTION_VERSION, SYSTEM_CLAIM_EXTRACTOR
from jobpilot.llm_gateway.gateway import LLMGateway, make_cache_key
from jobpilot.models.claim import ClaimExtractionResult


def _compute_cache_key(jd_text: str, resume_version: str, model: str) -> str:
    """计算缓存键."""
    content = f"{jd_text}|{resume_version}|{CLAIM_EXTRACTION_VERSION}"
    return make_cache_key(content, model)


class ClaimExtractor:
    """Claim 提取器."""

    def __init__(self, gateway: LLMGateway, storage=None):
        self.gateway = gateway
        self.storage = storage

    def extract(
        self,
        resume_text: str,
        jd_text: str,
        parsed_jd: dict,
        resume_version: str,
        job_id: str,
    ) -> ClaimExtractionResult:
        """执行 Claim 提取.

        Args:
            resume_text: 简历文本
            jd_text: JD 原文
            parsed_jd: Parser 解析后的结构化 JD
            resume_version: 简历版本号
            job_id: 职位 ID

        Returns:
            ClaimExtractionResult: 提取结果
        """
        from jobpilot.agents.claim_prompts import build_claim_extraction_prompt

        # 构建 prompt
        prompt = build_claim_extraction_prompt(resume_text, jd_text, parsed_jd)

        # 计算缓存键
        cache_key = _compute_cache_key(jd_text, resume_version, self.gateway.cfg.model)

        # 调用 LLM
        result = self.gateway.json_in(
            ClaimExtractionResult,
            prompt,
            system=SYSTEM_CLAIM_EXTRACTOR,
            cache_key=cache_key,
            module="claim_extractor",
        )

        # 确保 job_id 和 resume_version 正确
        result.job_id = job_id
        result.resume_version = resume_version

        # 保存到数据库
        if self.storage:
            self.storage.claims.save(result)

        return result


def extract_claims(
    gateway: LLMGateway,
    storage,
    resume_text: str,
    jd_text: str,
    parsed_jd: dict,
    resume_version: str,
    job_id: str,
) -> ClaimExtractionResult:
    """便捷函数:提取 Claim 并保存."""
    extractor = ClaimExtractor(gateway, storage)
    return extractor.extract(resume_text, jd_text, parsed_jd, resume_version, job_id)
