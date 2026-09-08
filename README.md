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

## 快速开始（全浏览器操作）

```bash
# 1. 安装依赖
py -3.12 -m venv .venv
.venv\Scripts\pip install -e ".[dev,m2,m3]"

# 2. 启动应用（浏览器自动打开）
.venv\Scripts\streamlit run src/jobpilot/app/app.py
```

**启动后在浏览器中操作：**

1. 点击 **⚙️ 设置** → 输入 API Key → 保存
2. 点击 **📝 我的简历** → 编辑个人信息 → 保存
3. 点击 **📊 在线评分** → 粘贴 JD 文本 → 点击评分

**就这么简单！无需编辑任何配置文件。**

---

## 其他启动方式

### Docker 启动
```bash
docker compose up -d
# 浏览器访问 http://localhost:8501
```

### 命令行方式（高级用户）
```bash
# 离线演示
.venv/Scripts/jobpilot score --file examples/jobs/jd_backend_intern.md --profile profile.example.yaml --fake

# 真实调用
.venv/Scripts/jobpilot score --file examples/jobs/jd_backend_intern.md --profile profile.yaml

# 定时监控
.venv/Scripts/jobpilot watch
```

> 需要 Python 3.11 或 3.12。详细使用说明请参考 [用户使用手册](docs/用户使用手册.md)。

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
