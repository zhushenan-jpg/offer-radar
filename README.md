# OfferRadar

> OfferRadar · 求职机会雷达

多 Agent 求职调研助手:监控目标公司职位发布 → 简历-JD 匹配评分(带证据链)→ 公司调研 → 求职周报。LLM 层模型无关(任何 OpenAI 兼容端点),当前默认使用 mimo-v2.5-pro。

**只辅助决策:不自动投递、不爬 LinkedIn、不绕过反爬。**

- 需求与概要设计:[docs/01-需求分析与概要设计.md](docs/01-需求分析与概要设计.md)
- 详细设计:[docs/02-详细设计.md](docs/02-详细设计.md)

## 快速开始(M1)

```bash
# ---- Windows ----
py -3.12 -m venv .venv
.venv\Scripts\pip install -e ".[dev,m2,m3]"
copy .env.example .env                    # 填入 API key(任意 OpenAI 兼容端点)
copy profile.example.yaml profile.yaml    # 换成你的真实简历

# ---- macOS / Linux ----
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev,m2,m3]"
cp .env.example .env
cp profile.example.yaml profile.yaml

# 离线演示(内置假 LLM,不花 API 钱)
.venv/Scripts/jobpilot score --file examples/jobs/jd_backend_intern.md --profile profile.example.yaml --fake

# 真实调用
.venv/Scripts/jobpilot score --file examples/jobs/jd_backend_intern.md --profile profile.yaml

# 测试(全部 mock,不花 API 钱)
.venv/Scripts/pytest
# 真 API 冒烟(花 1 次调用,需先配好 .env)
.venv/Scripts/pytest -m live

# 评测闭环:抽样 → 人工标注 → 一致性指标(rubric/prompt 变更后重跑即回归)
.venv/Scripts/jobpilot eval-seed --n 8
.venv/Scripts/jobpilot eval-annotate --job-id <id> --score <0-100>
.venv/Scripts/jobpilot eval-run                # 生成 docs/eval-report.md

# 求职雷达面板
.venv/Scripts/streamlit run src/jobpilot/app/dashboard.py

# 定时监控:每日 07:30 增量+高分推送 / 周五 21:00 周全量(错峰) / 08:00 预算巡检
.venv/Scripts/jobpilot watch                # 或 --once 立即跑一次增量

# PDF 简历解析(文本型零成本抽取,扫描件走视觉模型)
.venv/Scripts/jobpilot parse-resume --file 我的简历.pdf
```

> macOS / Linux 用户:上述命令中的 `.venv/Scripts/` 对应 `.venv/bin/`,`copy` 对应 `cp`;`jobpilot` 命令也可用 `python -m jobpilot` 调用。

## 部署(Streamlit Community Cloud)

面板是纯只读演示,不需要任何 API 密钥:

1. 生成并提交演示库:`python scripts/export_demo_db.py`(输出 `deploy/demo_jobpilot.db`);
2. 仓库推送到 GitHub;
3. [share.streamlit.io](https://share.streamlit.io) → New app → 选仓库,Main file 填 `src/jobpilot/app/dashboard.py`。

## 当前状态

- [x] M1:包骨架、数据模型、SQLite 存储、LLM 网关(缓存/计量/预算)、Rubric v1 评分、CLI
- [x] M2:ATS 采集器(Greenhouse/Lever)+ JD 清洗 + 去重 + crewAI 编排 + Markdown 周报(`jobpilot report`)
- [x] M3:评测台(Spearman/MAE/Top-k/校准)+ 成本统计 + Streamlit 面板 + 部署物
- [x] M4:定时监控(`jobpilot watch`,错峰跑批 + 高分推送 + 预算巡检)+ PDF 简历解析(`parse-resume`)+ browser-use 兜底采集器(可选依赖)

## 周报示例

`docs/reports/` 下有一份真实采集(2158 条职位,8 家公司)+ 离线假评分的样例周报 `2026-W36.md`。
