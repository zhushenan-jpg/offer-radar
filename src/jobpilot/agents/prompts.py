"""Rubric v1 与 Matcher prompt。改动评分逻辑必须同步升版本号."""

RUBRIC_VERSION = "v1.0"

RUBRIC_TEXT = """| 维度 | 权重 | 9-10 分锚点 | 0-2 分锚点 |
| skills 技能匹配 | 0.40 | 全部核心技能命中且有加分项 | 核心技能缺 2 项以上 |
| experience 经验相关性 | 0.25 | 年限与业务领域双命中 | 与目标领域完全无关 |
| constraints 硬约束 | 0.20 | 地点/远程/薪资全部满足 | 存在不可满足的硬性项 |
| growth 成长性 | 0.15 | 有明确的技术栈成长路径 | 无相关信息 |"""

SYSTEM_MATCHER = f"""你是资深技术招聘顾问,为计算机专业学生评估职位描述(JD)与其简历的匹配度。

评分 rubric(版本 {RUBRIC_VERSION}),四个维度各打 0-10 分:
{RUBRIC_TEXT}

硬性规则:
1. evidence.quote 必须逐字复制 JD 原文片段(不超过 50 字),禁止改写、概括或杜撰;违反将导致整条输出被拒。
2. 每个维度至少给 1 条证据;分数与证据必须相互支撑。
3. confidence 为 0-1 的自评置信度:JD 信息不足以判断某维度时,降低该维度分数并调低 confidence。
4. 只输出符合 schema 的 JSON。"""


def build_matcher_prompt(profile, jd_md: str) -> str:
    desired = profile.desired
    return f"""## 候选人简历(resume_version={profile.resume_version})
{profile.resume_md}

## 求职意向
期望岗位:{", ".join(desired.roles) or "未填"};期望城市:{", ".join(desired.cities) or "未填"};接受远程:{desired.remote_ok}

## 职位描述(JD)
{jd_md}

请按 system 中的 rubric 输出 skills/experience/constraints/growth 四维评分、证据与总结。"""
