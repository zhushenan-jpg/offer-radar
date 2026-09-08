---
name: jobpilot-conventions
description: OfferRadar(多 Agent 求职助手)项目的结构、技术栈与开发约定地图。凡在本工作区做 OfferRadar 相关工作——写代码、修 bug、跑测试、继续开发、讨论架构——都必须先加载本 skill,避免重新探索项目或偏离已定的设计决策。
---

# OfferRadar 项目约定

## 这是什么项目

多 Agent 求职调研助手:Greenhouse/Lever 官方 API 采集职位 → crewAI 四 Agent(Scout/Parser/Matcher/Reporter)→ 匹配评分 + 周报。LLM 层模型无关(OpenAI 兼容端点),当前默认 mimo-v2.5-pro(经用户中转站;2026-09-06 起,详见设计文档 §0)。**定位是辅助决策,永不自动投递,永不爬 LinkedIn。**

## 权威文档(改动前先查,不要凭记忆)

- `docs/01-需求分析与概要设计.md` — 需求分析(FR1-FR10、MoSCoW)、五层架构、数据模型、组件清单(2026-09-06 已逐仓核实)、里程碑 M1-M4。**这是唯一权威来源,与代码冲突时以文档为准并更新文档。**

## 技术栈(已定,勿重新选型)

- Python 3.11+;编排 crewAI(锁 1.15.x);调研 gpt-researcher(当库用,锁版本);浏览器兜底 browser-use(二期才装)
- LLM:openai-python + 自写薄网关 `llm_gateway/`(统一 base_url、Schema 校验重试、缓存、token 计量)——**项目内禁止绕过网关直连 API**
- 存储 SQLite(WAL)+ pydantic 模型;调度 APScheduler(锁 3.x);界面 Streamlit + typer;通知 apprise;结构化输出 instructor
- 评分必须带 `rubric_version/resume_version/model_version` 落库,并引用 JD 原文作证据

## 计划的目录结构(M1 脚手架按此创建)

```
jobpilot/
├── docs/                    # 已有:01-需求分析与概要设计.md
├── src/jobpilot/
│   ├── collectors/          # Greenhouse/Lever 采集器,统一 JobPosting 模型
│   ├── agents/              # crewAI 四 Agent 的定义与 prompt
│   ├── tools/               # researcher_tool、browser_tool(二期)、db_tool
│   ├── llm_gateway/         # GLM 接入/校验/缓存/计量,唯一 LLM 入口
│   ├── storage/             # SQLite DAO
│   ├── scheduler/           # APScheduler 错峰跑批
│   ├── eval/                # 标注集、Spearman/校准指标、回归评测
│   └── app/                 # CLI(typer)+ Streamlit
├── tests/
├── profile.yaml             # 用户简历与求职意向(gitignore 模板除外)
└── .env                     # ZHIPU_API_KEY 等,绝不提交
```

## 工作约定

- 测试先行(pytest):llm_gateway 与 collectors 必须有单测,LLM 调用在测试中一律 mock,不打真 API。
- 每个里程碑完成前:跑全部测试 + 按里程碑出口标准逐条验证(M1=结构化评分 JSON 正确产出;M2=一条命令产出周报;M3=有评测数字和公开 URL)。
- 成本敏感:新增 LLM 调用前先想清楚能否用缓存/批量/规则替代,并把 token 计量接进网关。
- 提交信息用英文短句,body 说明取舍;`.env`、`*.db`、`profile.yaml` 进 `.gitignore`。
