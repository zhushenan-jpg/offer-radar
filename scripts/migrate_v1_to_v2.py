"""数据库迁移脚本：新增扩展技能表.

使用方法：
    python scripts/migrate_v1_to_v2.py <数据库路径>

示例：
    python scripts/migrate_v1_to_v2.py jobpilot.db
"""

import sqlite3
import sys

MIGRATION_SQL = """
-- 新增 claim_extractions 表
CREATE TABLE IF NOT EXISTS claim_extractions(
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs,
    resume_version TEXT NOT NULL,
    claims_json TEXT NOT NULL,
    gaps_json TEXT NOT NULL,
    evidence_matrix_json TEXT DEFAULT '[]',
    extraction_tokens INTEGER DEFAULT 0,
    extraction_cost REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_claim_extractions_job ON claim_extractions(job_id);

-- 新增 resume_patches 表
CREATE TABLE IF NOT EXISTS resume_patches(
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs,
    bullet_rewrites_json TEXT DEFAULT '[]',
    missing_evidence_json TEXT DEFAULT '[]',
    hr_opener_text TEXT DEFAULT '',
    patch_markdown TEXT DEFAULT '',
    generation_tokens INTEGER DEFAULT 0,
    generation_cost REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_resume_patches_job ON resume_patches(job_id);

-- 新增 interview_briefs 表
CREATE TABLE IF NOT EXISTS interview_briefs(
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs,
    company_overview TEXT DEFAULT '',
    tech_stack_json TEXT DEFAULT '[]',
    predicted_questions_json TEXT DEFAULT '[]',
    followup_protocol_json TEXT DEFAULT '[]',
    weak_area_drills_json TEXT DEFAULT '[]',
    evidence_summary_json TEXT DEFAULT '{}',
    brief_markdown TEXT DEFAULT '',
    generation_tokens INTEGER DEFAULT 0,
    generation_cost REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_interview_briefs_job ON interview_briefs(job_id);

-- 扩展 scores 表（添加 claims/gaps 相关字段）
-- 注意：SQLite 不支持 ALTER TABLE ADD COLUMN IF NOT EXISTS，需要先检查
"""


def check_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """检查表中是否存在指定列."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate(db_path: str) -> None:
    """执行数据库迁移."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # 创建新表
    conn.executescript(MIGRATION_SQL)

    # 扩展 scores 表
    if not check_column_exists(conn, "scores", "claims_json"):
        conn.execute("ALTER TABLE scores ADD COLUMN claims_json TEXT DEFAULT '[]'")
        print("Added claims_json column to scores table")

    if not check_column_exists(conn, "scores", "gaps_json"):
        conn.execute("ALTER TABLE scores ADD COLUMN gaps_json TEXT DEFAULT '[]'")
        print("Added gaps_json column to scores table")

    if not check_column_exists(conn, "scores", "evidence_matrix_json"):
        conn.execute("ALTER TABLE scores ADD COLUMN evidence_matrix_json TEXT DEFAULT '[]'")
        print("Added evidence_matrix_json column to scores table")

    conn.commit()
    conn.close()

    print(f"Migration completed successfully: {db_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python migrate_v1_to_v2.py <db_path>")
        print("Example: python migrate_v1_to_v2.py jobpilot.db")
        sys.exit(1)

    db_path = sys.argv[1]
    migrate(db_path)


if __name__ == "__main__":
    main()
