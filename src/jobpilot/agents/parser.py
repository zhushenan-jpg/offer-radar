"""Parser Agent:基于 LLM 的结构化 JD 解析.

设计文档 §6.1 架构中的独立 Parser Agent，将非结构化 JD 文本解析为结构化数据.
替代 pipeline.py 中的 regex parse_jd，提供更精准的技能、级别、薪资等提取。
"""

from pydantic import BaseModel, Field

from jobpilot.llm_gateway.gateway import LLMGateway, make_cache_key

PARSER_VERSION = "1.0"

SYSTEM_PARSER = """你是一位资深的招聘分析师。你的任务是将职位描述（JD）解析为结构化数据。

提取规则：
1. 技能：提取所有技术技能（编程语言、框架、工具、平台）和软技能
2. 要求：提取硬性要求（学历、年限、证书）和软性要求
3. 职责：提取主要工作职责
4. 薪资：如果 JD 中提到薪资范围，提取出来
5. 级别：判断职位级别（实习/初级/中级/高级/Lead）
6. 远程：是否支持远程工作

只从 JD 原文中提取，不要推断或编造。如果某项信息 JD 中未提及，留空列表或 null。"""


class ParsedJD(BaseModel):
    """结构化 JD 解析结果."""

    skills: list[str] = Field(default_factory=list, description="技术技能列表")
    soft_skills: list[str] = Field(default_factory=list, description="软技能列表")
    requirements: list[str] = Field(default_factory=list, description="硬性要求列表")
    responsibilities: list[str] = Field(default_factory=list, description="工作职责列表")
    level: str | None = Field(default=None, description="职位级别: intern/junior/mid/senior/lead")
    remote: bool | None = Field(default=None, description="是否支持远程")
    salary_min: int | None = Field(default=None, description="最低薪资(元/月)")
    salary_max: int | None = Field(default=None, description="最高薪资(元/月)")
    education: str | None = Field(default=None, description="学历要求")
    years_min: float | None = Field(default=None, description="最低工作年限")
    languages: list[str] = Field(default_factory=list, description="自然语言要求(如英语)")


SYSTEM_PROMPT = SYSTEM_PARSER


def parse_jd_llm(gateway: LLMGateway, jd_text: str, job_id: str = "") -> ParsedJD:
    """使用 LLM 解析 JD 为结构化数据.

    Args:
        gateway: LLM 网关
        jd_text: JD 原文
        job_id: 职位 ID（用于缓存）

    Returns:
        ParsedJD: 结构化解析结果
    """
    # 计算缓存键
    import hashlib

    text_hash = hashlib.sha256(jd_text.encode()).hexdigest()[:16]
    cache_key = make_cache_key(f"parser|{text_hash}", gateway.cfg.model) if job_id else None

    prompt = f"""请解析以下职位描述，输出结构化 JSON：

---
{jd_text[:4000]}
---

严格按照 schema 输出，不要遗漏任何字段。"""

    result = gateway.json_in(
        ParsedJD,
        prompt,
        system=SYSTEM_PARSER,
        cache_key=cache_key,
        module="parser",
    )

    return result


def parse_jd_with_fallback(gateway: LLMGateway, jd_text: str, job_id: str = "") -> dict:
    """LLM 解析优先，失败时回退到 regex 解析.

    兼容 pipeline.parse_jd 的返回格式（dict），同时增加 LLM 提取的额外字段。
    """
    try:
        parsed = parse_jd_llm(gateway, jd_text, job_id)
        return {
            "skills": parsed.skills,
            "requirements": parsed.requirements,
            "responsibilities": parsed.responsibilities,
            "level": parsed.level,
            "remote": parsed.remote,
            "salary_min": parsed.salary_min,
            "salary_max": parsed.salary_max,
            "education": parsed.education,
            "years_min": parsed.years_min,
            "languages": parsed.languages,
            "soft_skills": parsed.soft_skills,
            "raw_text": jd_text,
            "parser": "llm",
        }
    except Exception:
        # 回退到 regex 解析
        from jobpilot.pipeline import parse_jd

        result = parse_jd(jd_text)
        result["parser"] = "regex"
        return result
