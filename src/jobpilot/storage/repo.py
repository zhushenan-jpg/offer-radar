"""DAO 层:全部 SQL 收口在这里."""

import json
from datetime import UTC, datetime

from jobpilot.models.job import JobPosting
from jobpilot.models.score import DIMS, MatchScore

LOW_CONFIDENCE_THRESHOLD = 0.6


def _now() -> str:
    return datetime.now(UTC).isoformat()


class JobRepo:
    def __init__(self, conn):
        self.conn = conn

    def upsert(self, job: JobPosting) -> None:
        """已存在则仅刷新 last_seen 与描述,first_seen/status 保持不变."""
        self.conn.execute(
            """INSERT INTO jobs(id, company_id, source, company, title, location, remote, url,
                 department, description_raw_md, description_clean_md, fingerprint,
                 first_seen, last_seen, status)
               VALUES(?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title, location=excluded.location, remote=excluded.remote,
                 url=excluded.url, department=excluded.department,
                 description_raw_md=excluded.description_raw_md, last_seen=excluded.last_seen""",
            (
                job.id,
                job.source,
                job.company,
                job.title,
                job.location,
                int(job.remote),
                job.url,
                job.department,
                job.description_md,
                job.fingerprint,
                job.first_seen.isoformat(),
                job.last_seen.isoformat(),
                job.status,
            ),
        )
        self.conn.commit()

    def get(self, job_id: str) -> JobPosting | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return None
        return JobPosting(
            id=row["id"],
            source=row["source"] or "manual",
            company=row["company"] or "manual",
            title=row["title"],
            location=row["location"] or "",
            remote=bool(row["remote"]),
            url=row["url"] or "",
            department=row["department"] or "",
            description_md=row["description_raw_md"] or "",
        )

    def get_clean(self, job_id: str) -> str:
        row = self.conn.execute(
            "SELECT description_clean_md FROM jobs WHERE id=?", (job_id,)
        ).fetchone()
        return row[0] if row else ""

    def set_clean_md(self, job_id: str, clean_md: str) -> None:
        self.conn.execute("UPDATE jobs SET description_clean_md=? WHERE id=?", (clean_md, job_id))
        self.conn.commit()

    def update_status(self, job_id: str, status: str) -> None:
        self.conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
        self.conn.commit()

    def ids_by_status(self, status: str) -> list[str]:
        return [
            r[0]
            for r in self.conn.execute(
                "SELECT id FROM jobs WHERE status=? ORDER BY first_seen", (status,)
            ).fetchall()
        ]

    def scored_with_scores(self) -> list[dict]:
        """全部已评分职位的最新评分,按 overall 降序;周报数据源."""
        rows = self.conn.execute(
            """SELECT j.company, j.title, j.url, j.location, s.overall, s.dims_json,
                 s.confidence, s.summary, s.review_status, s.rubric_version
               FROM jobs j JOIN scores s ON s.job_id = j.id
               WHERE s.id = (SELECT MAX(id) FROM scores WHERE job_id = j.id)
               ORDER BY s.overall DESC"""
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["dims"] = json.loads(d.pop("dims_json"))
            out.append(d)
        return out


class ScoreRepo:
    def __init__(self, conn):
        self.conn = conn

    def save(
        self,
        job_id: str,
        score: MatchScore,
        *,
        rubric_version: str,
        model_version: str,
        resume_version: str,
    ) -> None:
        dims_dump = {k: score.dims[k].model_dump() for k in DIMS}
        evidence_flat = [ev.model_dump() for k in DIMS for ev in score.dims[k].evidence]
        review = "review" if score.confidence < LOW_CONFIDENCE_THRESHOLD else "auto"
        self.conn.execute(
            """INSERT INTO scores(job_id, overall, dims_json, evidence_json, confidence,
                 summary, rubric_version, model_version, resume_version, review_status, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                job_id,
                score.overall,
                json.dumps(dims_dump, ensure_ascii=False),
                json.dumps(evidence_flat, ensure_ascii=False),
                score.confidence,
                score.summary,
                rubric_version,
                model_version,
                resume_version,
                review,
                _now(),
            ),
        )
        self.conn.commit()

    def latest_for_job(self, job_id: str):
        row = self.conn.execute(
            "SELECT * FROM scores WHERE job_id=? ORDER BY id DESC LIMIT 1", (job_id,)
        ).fetchone()
        return row


class UsageRepo:
    def __init__(self, conn):
        self.conn = conn

    def record(
        self,
        module: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_cny: float,
        cache_hit: int,
        ts: str | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO usage(ts, module, model, prompt_tokens, completion_tokens, cost_cny,"
            " cache_hit) VALUES(?,?,?,?,?,?,?)",
            (ts or _now(), module, model, prompt_tokens, completion_tokens, cost_cny, cache_hit),
        )
        self.conn.commit()

    def month_cost(self) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_cny),0) FROM usage"
            " WHERE substr(ts,1,7)=strftime('%Y-%m','now')"
        ).fetchone()
        return row[0]

    def month_cost_by_module(self) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT module, SUM(cost_cny) FROM usage"
            " WHERE substr(ts,1,7)=strftime('%Y-%m','now') GROUP BY module"
        ).fetchall()
        return {r[0]: r[1] for r in rows}


class CacheRepo:
    def __init__(self, conn):
        self.conn = conn

    def get(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value_json FROM llm_cache WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def put(self, key: str, value_json: str) -> None:
        self.conn.execute(
            "INSERT INTO llm_cache(key, value_json, created_at) VALUES(?,?,?)"
            " ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
            (key, value_json, _now()),
        )
        self.conn.commit()
