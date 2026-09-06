# OfferRadar

[![CI](https://github.com/zhushenan-jpg/offer-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/zhushenan-jpg/offer-radar/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

> Multi-agent job-search radar | 中文文档:[README.md](README.md)

OfferRadar is a multi-agent job-search research assistant: it monitors job postings
from your target companies → scores resume–JD fit with verbatim evidence chains →
researches companies → produces a weekly digest. The LLM layer is model-agnostic
(any OpenAI-compatible endpoint); it currently defaults to `mimo-v2.5-pro`.

**Decision support only: it never auto-applies, never scrapes LinkedIn, and never
bypasses anti-crawling measures.**

- Requirements & system design (Chinese): [docs/01-需求分析与概要设计.md](docs/01-需求分析与概要设计.md)
- Detailed design (Chinese): [docs/02-详细设计.md](docs/02-详细设计.md)

## Architecture

```
Greenhouse / Lever official job-board APIs (compliant, no scraping)
        │
        ▼
collectors (async, dedup via rapidfuzz fingerprints, boilerplate stripping)
        │
        ▼
crewAI crew: Scout → Parser → Matcher → Reporter        ── tools: gpt-researcher,
        │                                                  browser-use (optional)
        ▼
LLM Gateway (single entry point: instructor-validated structured output,
             evidence-verbatim hard gate with feedback retry, result cache,
             per-call token metering, monthly budget hard stop)
        │
        ▼
SQLite (jobs / scores / annotations / usage accounting)  ──▶  Weekly report (Jinja2)
                                                          └─▶  Streamlit dashboard
Scheduler (APScheduler): Fri 21:00 full run, daily 07:30 incremental
+ high-score push notifications, daily 08:00 budget patrol
```

Every match score carries 4-dimension ratings (skills / experience / constraints /
growth) with quotes **copied verbatim from the JD** — a programmatic anti-hallucination
gate re-validates each quote and feeds violations back for one corrective re-score.
Rubric and resume versions are part of every cache key, so changing the rubric
invalidates caches automatically and re-running the eval suite becomes a regression test.

## Quick start

```bash
# ---- Windows ----
py -3.12 -m venv .venv
.venv\Scripts\pip install -e ".[dev,m2,m3]"
copy .env.example .env                    # put in your API key (any OpenAI-compatible endpoint)
copy profile.example.yaml profile.yaml    # replace with your real resume

# ---- macOS / Linux ----
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev,m2,m3]"
cp .env.example .env
cp profile.example.yaml profile.yaml
```

> macOS / Linux: replace `.venv/Scripts/` with `.venv/bin/` and `copy` with `cp`
> in the commands below; `jobpilot` can also be invoked as `python -m jobpilot`.

```bash
# Offline demo (built-in fake LLM, zero API cost)
jobpilot score --file examples/jobs/jd_backend_intern.md --profile profile.example.yaml --fake

# Real scoring
jobpilot score --file examples/jobs/jd_backend_intern.md --profile profile.yaml

# Tests (all mocked, zero API cost)
pytest
# Real-API smoke (2 calls, needs .env)
pytest -m live

# Eval loop: sample -> human annotations -> agreement metrics
# (re-running after any rubric/prompt change is a regression test)
jobpilot eval-seed --n 8
jobpilot eval-annotate --job-id <id> --score <0-100>
jobpilot eval-run                # writes docs/eval-report.md

# Radar dashboard
streamlit run src/jobpilot/app/dashboard.py

# Scheduled monitoring: daily 07:30 incremental + high-score push,
# Fri 21:00 weekly full run (off-peak pricing), daily 08:00 budget patrol
jobpilot watch                # or --once for a single incremental run

# PDF resume parsing (free text extraction; vision fallback for scanned PDFs)
jobpilot parse-resume --file my_resume.pdf
```

## Deployment (Streamlit Community Cloud)

The dashboard is a read-only demo and needs no API keys:

1. Build and commit the demo database: `python scripts/export_demo_db.py` (writes `deploy/demo_jobpilot.db`);
2. Push the repository to GitHub;
3. [share.streamlit.io](https://share.streamlit.io) → New app → pick the repo,
   set the main file to `src/jobpilot/app/dashboard.py`.

## Status

- [x] M1: package skeleton, data models, SQLite storage, LLM gateway (cache /
      metering / budget), rubric scoring, CLI
- [x] M2: ATS collectors (Greenhouse/Lever) + JD cleaning + dedup + crewAI
      orchestration + Markdown weekly report (`jobpilot report`)
- [x] M3: eval platform (Spearman/MAE/Top-k/calibration) + cost accounting +
      Streamlit dashboard + deployment artifacts
- [x] M4: scheduled monitoring (`jobpilot watch`: off-peak batches, high-score
      push, budget patrol) + PDF resume parsing (`parse-resume`) + browser-use
      fallback collector (optional dependency)

## Weekly report sample

`docs/reports/` contains a sample report built from a real crawl
(2,158 postings across 8 companies) with offline dummy scores: `2026-W36.md`.
