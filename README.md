# OfferRadar

[![CI](https://github.com/zhushenan-jpg/offer-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/zhushenan-jpg/offer-radar/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

> OfferRadar · 求职机会雷达 | English: [README.en.md](README.en.md)

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
>
> 需要 Python 3.11 或 3.12(3.13 暂不支持:通知组件 apprise 依赖的 `imghdr` 已被移除)。`pytest -m live` 需要可访问中转站/官方端点的稳定网络,失败会自动重试一次。

## 部署(Streamlit Community Cloud)

面板是纯只读演示,不需要任何 API 密钥:

1. 生成并提交演示库:`python scripts/export_demo_db.py`(输出 `deploy/demo_jobpilot.db`);
2. 仓库推送到 GitHub;
3. [share.streamlit.io](https://share.streamlit.io) → New app → 选仓库,Main file 填 `src/jobpilot/app/dashboard.py`。

## 扩展技能 (M5-M7)

基于 ASu-skills 设计，新增三个 MVP 扩展技能：

### Claim Evidence Extractor (证据链提取器)

从简历中提取可验证声明（Claim），与 JD 要求进行匹配，识别差距。

```python
from jobpilot.tools.claim_extractor import ClaimExtractor

extractor = ClaimExtractor(gateway, storage)
result = extractor.extract(
    resume_text="负责后端开发，将 API 响应时间从 2s 优化到 200ms",
    jd_text="要求有性能优化经验",
    parsed_jd={"skills": ["Python"]},
    resume_version="v1.0",
    job_id="job_001",
)
# result.claims: 提取的 Claim 列表
# result.gaps: 识别的 Gap 列表
```

### Gap Advisor (简历差距顾问)

针对高分但证据不足的职位，生成具体的简历修改建议和 HR 开场白。

```python
from jobpilot.tools.gap_advisor import GapAdvisor

advisor = GapAdvisor(gateway, storage)
patch = advisor.generate_patch(
    resume_text="负责后端开发",
    job_posting_summary="要求有后端开发经验",
    claims=[...],
    gaps=[...],
    job_id="job_001",
)
# patch.bullet_rewrites: 改写建议
# patch.hr_opener: HR 开场白
# patch.patch_markdown: 可合并的增量内容
```

### Interview Prep Generator (面试预测器)

高分职位自动生成面试准备材料。

```python
from jobpilot.tools.interview_prep import InterviewPrep

prep = InterviewPrep(gateway, storage)
brief = prep.generate_brief(
    job_posting_summary="要求熟悉 Python 和微服务",
    company_research="这是一家技术公司...",
    claims=[...],
    gaps=[...],
    resume_text="负责后端开发",
    job_id="job_001",
)
# brief.predicted_questions: 预测问题
# brief.followup_protocol: 追问协议
# brief.brief_markdown: 一页纸面试速览
```

### 监控面板

```bash
# 启动监控面板
streamlit run src/jobpilot/app/monitoring.py
```

### 邮件告警配置

```bash
# .env 文件
ALERT_EMAIL_ENABLED=true
ALERT_SMTP_HOST=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_SMTP_USER=your-email@gmail.com
ALERT_SMTP_PASS=your-password
ALERT_RECIPIENTS=recipient@example.com
```

## 当前状态

- [x] M1:包骨架、数据模型、SQLite 存储、LLM 网关(缓存/计量/预算)、Rubric v1 评分、CLI
- [x] M2:ATS 采集器(Greenhouse/Lever)+ JD 清洗 + 去重 + crewAI 编排 + Markdown 周报(`jobpilot report`)
- [x] M3:评测台(Spearman/MAE/Top-k/校准)+ 成本统计 + Streamlit 面板 + 部署物
- [x] M4:定时监控(`jobpilot watch`,错峰跑批 + 高分推送 + 预算巡检)+ PDF 简历解析(`parse-resume`)+ browser-use 兜底采集器(可选依赖)
- [x] M5:Claim Evidence Extractor - 证据链提取器
- [x] M6:Gap Advisor - 简历差距顾问
- [x] M7:Interview Prep Generator - 面试预测器

## 周报示例

`docs/reports/` 下有一份真实采集(2158 条职位,8 家公司)+ 离线假评分的样例周报 `2026-W36.md`。
