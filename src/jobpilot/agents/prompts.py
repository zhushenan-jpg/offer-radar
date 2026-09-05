"""Rubric v1 与 Matcher prompt。改动评分逻辑必须同步升版本号."""

RUBRIC_VERSION = "v1.1"

RUBRIC_TEXT = """| 维度 | 权重 | 9-10 分锚点 | 0-2 分锚点 |
| skills 技能匹配 | 0.40 | JD 列出的核心技能大部分被候选人技能覆盖(按覆盖率评) | 仅命中零星边缘技能,核心要求几乎无覆盖 |
| experience 经验相关性 | 0.25 | 业务领域对口且年限/级别与岗位要求匹配 | 领域完全无关,或级别差距悬殊(如在校学生对 Staff 岗) |
| constraints 硬约束 | 0.20 | 地点/远程/薪资/时间全部满足 | 存在不可满足的硬性项(如需到岗城市不符) |
| growth 成长性 | 0.15 | 有明确的技术栈成长路径 | 无相关信息 |

维度切分规则:技能"会不会"看 skills;级别"配不配"看 experience。不要把级别差距计入 skills。"""

SYSTEM_MATCHER = f"""你是资深技术招聘顾问,为计算机专业学生评估职位描述(JD)与其简历的匹配度。

评分 rubric(版本 {RUBRIC_VERSION}),四个维度各打 0-10 分:
{RUBRIC_TEXT}

硬性规则:
1. evidence.quote 必须是 JD 原文中连续出现的逐字子串(程序会做子串校验,不通过将被打回重评),禁止拼接、缩写、改写、翻译或凭记忆补全;每条引用不超过 60 字,选最能支撑该维度分数的片段。
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
