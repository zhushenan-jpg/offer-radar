"""Interview Prep prompt 模板。改动预测逻辑必须同步升版本号."""

INTERVIEW_PREP_VERSION = "v1.0"

SYSTEM_INTERVIEW_PREP = """你是一个面试预测专家。请基于 JD、公司调研和候选人 Claim，生成面试准备材料。

工作原则：
1. 预测问题要具体，不能是泛泛的（如"介绍一下自己"）
2. 追问要能检测 Claim 的真实性，不能是简单的"还有吗"
3. 弱项练习要给出具体的学习方向，不能是"多学习"
4. brief_markdown 要简洁，控制在一页纸内（约 500 字）
5. 只输出符合 schema 的 JSON"""


def build_interview_prep_prompt(
    job_posting_summary: str,
    company_research: str,
    claims_json: list[dict],
    gaps_json: list[dict],
    resume_text: str,
) -> str:
    """构建 Interview Prep prompt."""
    import json

    claims_str = json.dumps(claims_json, ensure_ascii=False, indent=2)
    gaps_str = json.dumps(gaps_json, ensure_ascii=False, indent=2)

    return f"""## JD 信息
{job_posting_summary}

## 公司调研
{company_research}

## 候选人 Claim
{claims_str}

## 候选人 Gap
{gaps_str}

## 简历原文
{resume_text}

## 任务
1. 预测高频面试问题（按 Claim 类型分类）：
   - jd_direct：从 JD 明确要求中提取的问题
   - jd_inferred：从 JD 推断的问题
   - company_culture：公司文化相关问题

2. 为每个问题设计追问协议：
   - 对 Metric 类 Claim，追问具体数字和计算方法
   - 对 Ownership 类 Claim，追问个人贡献和决策过程
   - 对 Technical 类 Claim，追问技术细节和踩坑经历
   - 每个问题设计 2-3 个追问
   - 标注危险信号（red_flags）

3. 对弱项 Claim 生成专项练习题：
   - 对 strength=weak 的 Claim，生成巩固练习题
   - 对 strength=missing 的 Claim，生成学习方向和练习题

4. 输出一页纸面试速览（brief_markdown）：
   - 公司背景（精简到 100 字）
   - 技术栈（列出 5-10 个关键技术）
   - 预测问题（按重要性排序，Top 5）
   - 证据摘要（按 Claim 类型分组）
   - 弱项提示

请输出符合 schema 的 JSON。"""
