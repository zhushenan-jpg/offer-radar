"""SQLite 存储:WAL 模式,schema 版本化初始化."""

import sqlite3
from pathlib import Path

from .repo import (
    AnnotationRepo,
    CacheRepo,
    ClaimExtractionRepo,
    EvalRepo,
    InterviewBriefRepo,
    JobRepo,
    ResumePatchRepo,
    ScoreRepo,
    UsageRepo,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies(
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, source TEXT NOT NULL,
  display_name TEXT NOT NULL, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY, company_id INTEGER REFERENCES companies,
  source TEXT DEFAULT '', company TEXT DEFAULT '',
  title TEXT NOT NULL, location TEXT DEFAULT '', remote INTEGER DEFAULT 0,
  url TEXT DEFAULT '', department TEXT DEFAULT '',
  description_raw_md TEXT DEFAULT '', description_clean_md TEXT DEFAULT '',
  fingerprint TEXT DEFAULT '', first_seen TEXT, last_seen TEXT, status TEXT DEFAULT 'new');
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_fp ON jobs(fingerprint);
CREATE TABLE IF NOT EXISTS scores(
  id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT REFERENCES jobs,
  overall REAL, dims_json TEXT, evidence_json TEXT, confidence REAL, summary TEXT,
  rubric_version TEXT, model_version TEXT, resume_version TEXT,
  review_status TEXT DEFAULT 'auto', human_overall REAL,
  claims_json TEXT DEFAULT '[]', gaps_json TEXT DEFAULT '[]',
  evidence_matrix_json TEXT DEFAULT '[]', created_at TEXT);
CREATE INDEX IF NOT EXISTS idx_scores_job ON scores(job_id);
CREATE TABLE IF NOT EXISTS llm_cache(
  key TEXT PRIMARY KEY, value_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS usage(
  ts TEXT, module TEXT, model TEXT, prompt_tokens INTEGER,
  completion_tokens INTEGER, cost_cny REAL, cache_hit INTEGER);
CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage(ts);
CREATE TABLE IF NOT EXISTS annotations(
  id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT,
  human_overall REAL, dims_json TEXT, annotator TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS eval_dataset(
  job_id TEXT PRIMARY KEY, added_at TEXT);
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT,
  path TEXT, cost_cny REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS claim_extractions(
  id TEXT PRIMARY KEY, job_id TEXT REFERENCES jobs,
  resume_version TEXT NOT NULL, claims_json TEXT DEFAULT '[]',
  gaps_json TEXT DEFAULT '[]', evidence_matrix_json TEXT DEFAULT '[]',
  extraction_tokens INTEGER DEFAULT 0, extraction_cost REAL DEFAULT 0.0,
  created_at TEXT DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS idx_claim_extractions_job ON claim_extractions(job_id);
CREATE TABLE IF NOT EXISTS resume_patches(
  id TEXT PRIMARY KEY, job_id TEXT REFERENCES jobs,
  bullet_rewrites_json TEXT DEFAULT '[]', missing_evidence_json TEXT DEFAULT '[]',
  hr_opener_text TEXT DEFAULT '', patch_markdown TEXT DEFAULT '',
  generation_tokens INTEGER DEFAULT 0, generation_cost REAL DEFAULT 0.0,
  created_at TEXT DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS idx_resume_patches_job ON resume_patches(job_id);
CREATE TABLE IF NOT EXISTS interview_briefs(
  id TEXT PRIMARY KEY, job_id TEXT REFERENCES jobs,
  company_overview TEXT DEFAULT '', tech_stack_json TEXT DEFAULT '[]',
  predicted_questions_json TEXT DEFAULT '[]', followup_protocol_json TEXT DEFAULT '[]',
  weak_area_drills_json TEXT DEFAULT '[]', evidence_summary_json TEXT DEFAULT '{}',
  brief_markdown TEXT DEFAULT '', generation_tokens INTEGER DEFAULT 0,
  generation_cost REAL DEFAULT 0.0, created_at TEXT DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS idx_interview_briefs_job ON interview_briefs(job_id);
"""


class Storage:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.jobs = JobRepo(conn)
        self.scores = ScoreRepo(conn)
        self.usage = UsageRepo(conn)
        self.cache = CacheRepo(conn)
        self.annotations = AnnotationRepo(conn)
        self.eval_ds = EvalRepo(conn)
        self.claims = ClaimExtractionRepo(conn)
        self.patches = ResumePatchRepo(conn)
        self.briefs = InterviewBriefRepo(conn)

    @classmethod
    def open(cls, path: Path | str) -> "Storage":
        path = Path(path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA)
        conn.commit()
        return cls(conn)
