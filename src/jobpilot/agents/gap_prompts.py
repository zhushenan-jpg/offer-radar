"""Gap Advisor prompt 模板。改动建议逻辑必须同步升版本号."""

GAP_ADVISOR_VERSION = "v1.0"

SYSTEM_GAP_ADVISOR = """你是一个简历优化顾问。请基于 Gap 分析，生成具体的简历修改建议。

工作原则：
1. Bullet 改写必须基于真实经历，不能虚构
2. 改写要突出与 JD 要求的匹配点，保留原有 Claim 的真实性
3. HR 开场白要简洁有力，突出与职位最相关的 2-3 个亮点
4. 缺失证据建议要具体可操作，不能是泛泛的建议
5. 只输出符合 schema 的 JSON"""


def build_gap_advisor_prompt(
    resume_text: str,
    job_posting_summary: str,
    claims_json: list[dict],
    gaps_json: list[dict],
) -> str:
    """构建 Gap Advisor prompt."""
    import json

    claims_str = json.dumps(claims_json, ensure_ascii=False, indent=2)
    gaps_str = json.dumps(gaps_json, ensure_ascii=False, indent=2)

    return f"""## 简历原文
{resume_text}

## JD 信息
{job_posting_summary}

## Gap 分析
{gaps_str}

## 现有 Claim
{claims_str}

## 任务
1. 对每个 soft_gap，给出简历 Bullet 改写建议：
   - 找到简历中与 gap 相关的经历
   - 改写表述，突出与 JD 要求的匹配点
   - 如果无法改写（差距太大），说明原因

2. 对缺失证据，给出具体补充建议：
   - 对 high priority 的 gap，建议具体的项目/活动
   - 对 medium/low priority 的 gap，建议学习方向

3. 生成针对该职位的 HR 开场白：
   - 选择 2-3 个与 JD 最相关的 strong Claim
   - 生成一段话（100-150 字），突出个人优势与职位匹配度

请输出符合 schema 的 JSON。"""
