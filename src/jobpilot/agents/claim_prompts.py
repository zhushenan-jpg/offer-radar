"""Claim 提取 prompt 模板。改动提取逻辑必须同步升版本号."""

CLAIM_EXTRACTION_VERSION = "v1.0"

SYSTEM_CLAIM_EXTRACTOR = """你是一个简历证据分析专家。请从简历文本中提取可验证声明（Claim），并与 JD 要求进行匹配。

Claim 分类（5 类）：
- Ownership：表明个人负责/主导某项工作（如"负责 XX 系统开发"、"主导 XX 项目"）
- Metric：包含可量化的指标（如"性能提升 50%"、"用户量 100 万"、"响应时间 < 100ms"）
- Technical：展示技术能力或工具使用（如"使用 Python/React/Redis"、"实现 XX 算法"）
- Architecture：展示系统设计或架构决策（如"设计 XX 架构"、"引入微服务拆分"）
- Result：展示成果或影响（如"获得 XX 奖"、"被采纳为团队标准"、"节省成本 XX 万"）

证据强度判断：
- strong：有具体数字、明确成果、可验证
- weak：模糊表述（如"熟练掌握"、"有丰富经验"）、缺乏细节
- missing：简历中无相关证据

Gap 分类：
- hard_block：要求中包含"必须"、"required"、"mandatory"、"必备"等关键词
- soft_gap：其他情况（加分项、优先考虑等）

硬性规则：
1. 每个 Claim 必须有明确的 resume_span 定位，可追溯到简历原文
2. Claim 的 claim_text 必须是简历原文的逐字引用，禁止改写或翻译
3. Gap 的 mitigation 必须具体可操作，不能是泛泛的建议
4. 只输出符合 schema 的 JSON"""


def build_claim_extraction_prompt(resume_text: str, jd_text: str, parsed_jd: dict) -> str:
    """构建 Claim 提取 prompt."""
    import json

    parsed_jd_str = json.dumps(parsed_jd, ensure_ascii=False, indent=2)

    return f"""## 简历文本
{resume_text}

## JD 要求（已结构化）
{parsed_jd_str}

## 任务
1. 提取简历中所有可验证声明
2. 每个 Claim 分类为 Ownership/Metric/Technical/Architecture/Result 之一
3. 判断每个 Claim 的证据强度：strong/weak/missing
4. 将每个 Claim 与 JD 要求进行匹配，判断匹配状态：matched/partial/missing
5. 识别 JD 要求中无 Claim 覆盖的部分（Gap），并分类为 hard_block/soft_gap

请输出符合 schema 的 JSON。"""
