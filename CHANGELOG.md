# Changelog

All notable changes to OfferRadar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [2.0.0] - 2026-09-21

### Added
- **AI Resume Optimization** (`resume_optimize` page): Gap Advisor integration generates bullet rewrites, missing evidence suggestions, and HR openers
- **Interview Simulation** (`interview_sim` page): Interactive AI-powered mock interview with multi-turn Q&A
- **Job Recommendations** (`recommendations` page): Prioritize unscored jobs from high-scoring companies
- **Salary Analysis** (`salary` page): Extract salary ranges from JDs, group by company
- **Researcher Tool** (`tools/researcher_tool.py`): DuckDuckGo search + LLM company research, integrated into InterviewPrep
- **Parser Agent** (`agents/parser.py`): LLM-based structured JD extraction (skills, level, salary, requirements)
- **4-Agent Crew**: Scout → Parser → Matcher → Reporter orchestration
- **Human Review Queue** (`review` page): Review low-confidence scores, approve or override with human score
- **Evaluation Annotation** (`annotation` page): Visual 50-item eval dataset annotation with progress tracking
- **CSV Export**: Download scored jobs as CSV from the job list page
- **API Key Validation**: Verify API Key before saving in Settings (models.list probe)
- **Cost Benchmark Script** (`scripts/cost_benchmark.py`): Quantify token savings from rule-based cleaning and cache hits
- **Profile Template** (`profile.example.yaml`): Template for new users

### Changed
- **i18n Overhaul**: Route by locale-independent keys, migrate 60+ hardcoded strings to translation system
- **Error Handling**: Distinguish timeout, auth, network errors with user-friendly messages
- **Collection Progress**: Per-company progress bar during job collection
- **Dependencies Updated**: instructor, streamlit, apprise, and other packages to latest compatible versions

### Fixed
- Language switching now preserves current page and applies immediately
- All Streamlit pages fully support Chinese/English switching

### Tests
- 192 tests passing (up from 172)
- New test files: `test_parser.py`, `test_researcher_tool.py`, `test_review_queue.py`, `test_notify.py`, `test_eval_dataset.py`

---

## [1.1.0] - 2026-09-15

### Added
- Extended skills: Claim Extractor, Gap Advisor, Interview Prep
- Browser-based UI: All operations via Streamlit (8 pages)
- i18n support (Chinese/English)
- Monitoring dashboard with cost tracking
- Streamlit Cloud deployment configuration

### Changed
- Unified application entry point (`app.py`)
- Demo database for public deployment

---

## [1.0.0] - 2026-09-08

### Added
- **Core Pipeline**: Greenhouse + Lever API collectors → JD cleaning → 4-dimension rubric scoring → weekly report
- **LLM Gateway**: Centralized API access with caching, token metering, monthly budget guard
- **Matcher Agent**: Skills/experience/constraints/growth scoring with evidence chain validation
- **Anti-Hallucination Gate**: Evidence quotes must be verbatim from JD
- **Evaluation Platform**: Spearman correlation, MAE, Top-k overlap, calibration curves
- **SQLite Storage**: WAL mode, 11 tables, 9 DAO repos
- **CLI**: 7 commands (score, report, eval-seed, eval-annotate, eval-run, watch, parse-resume)
- **Streamlit Dashboard**: 8 pages with real-time monitoring
- **Scheduled Monitoring**: APScheduler (weekly full, daily incremental, budget patrol)
- **Push Notifications**: appprise (100+ channels) + SMTP email
- **PDF Resume Parsing**: Text extraction + vision fallback
- **Docker Deployment**: Dockerfile + docker-compose.yml
- **GitHub Actions CI**: Python 3.11/3.12, Ruff linting, test coverage

### Technical
- Python 3.11+, crewAI 1.15.x, SQLite (WAL), Streamlit, APScheduler 3.x
- Model-agnostic: any OpenAI-compatible endpoint (default: mimo-v2.5-pro)

---

## [0.1.0] - 2026-09-06

### Added
- Initial project scaffold
- Design documentation (`docs/01-需求分析与概要设计.md`)
- Project structure and configuration
