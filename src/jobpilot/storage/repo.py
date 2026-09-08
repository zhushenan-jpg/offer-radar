"""DAO 层:全部 SQL 收口在这里."""

import json
from datetime import UTC, datetime

from jobpilot.models.claim import ClaimExtractionResult
from jobpilot.models.interview_brief import InterviewBrief
from jobpilot.models.job import JobPosting
from jobpilot.models.resume_patch import ResumePatch
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
        """全部已评分职位的最新评分,按 overall 降序;周报与面板数据源."""
        rows = self.conn.execute(
            """SELECT j.id AS job_id, j.company, j.title, j.url, j.location, s.overall,
                 s.dims_json, s.confidence, s.summary, s.review_status, s.rubric_version
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
        claims_json = json.dumps([c.model_dump() for c in score.claims], ensure_ascii=False)
        gaps_json = json.dumps([g.model_dump() for g in score.gaps], ensure_ascii=False)
        evidence_matrix_json = json.dumps(
            [e.model_dump() for e in score.evidence_matrix], ensure_ascii=False
        )
        self.conn.execute(
            """INSERT INTO scores(job_id, overall, dims_json, evidence_json, confidence,
                 summary, rubric_version, model_version, resume_version, review_status,
                 claims_json, gaps_json, evidence_matrix_json, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
                claims_json,
                gaps_json,
                evidence_matrix_json,
                _now(),
            ),
        )
        self.conn.commit()

    def latest_for_job(self, job_id: str):
        row = self.conn.execute(
            "SELECT * FROM scores WHERE job_id=? ORDER BY id DESC LIMIT 1", (job_id,)
        ).fetchone()
        return row

    def latest_claims_for_job(self, job_id: str) -> list[dict]:
        """获取指定职位最新的 Claim 列表."""
        row = self.conn.execute(
            "SELECT claims_json FROM scores WHERE job_id=? ORDER BY id DESC LIMIT 1", (job_id,)
        ).fetchone()
        if row and row["claims_json"]:
            return json.loads(row["claims_json"])
        return []

    def latest_gaps_for_job(self, job_id: str) -> list[dict]:
        """获取指定职位最新的 Gap 列表."""
        row = self.conn.execute(
            "SELECT gaps_json FROM scores WHERE job_id=? ORDER BY id DESC LIMIT 1", (job_id,)
        ).fetchone()
        if row and row["gaps_json"]:
            return json.loads(row["gaps_json"])
        return []


class AnnotationRepo:
    def __init__(self, conn):
        self.conn = conn

    def add(self, job_id: str, human_overall: float, annotator: str) -> None:
        self.conn.execute(
            "INSERT INTO annotations(job_id, human_overall, annotator, created_at) VALUES(?,?,?,?)",
            (job_id, human_overall, annotator, _now()),
        )
        self.conn.commit()

    def pairs_with_predictions(self, annotator: str | None = None) -> list[dict]:
        """评测集内:每人每职位最新标注 × 该职位最新模型分."""
        sql = """
            SELECT a.job_id AS job_id, a.human_overall AS human, a.annotator AS annotator,
                   j.company AS company, j.title AS title, s.overall AS pred
            FROM annotations a
            JOIN jobs j ON j.id = a.job_id
            JOIN scores s ON s.job_id = a.job_id
              AND s.id = (SELECT MAX(id) FROM scores WHERE job_id = a.job_id)
            WHERE a.id = (
                SELECT MAX(id) FROM annotations
                WHERE job_id = a.job_id AND annotator = a.annotator)
        """
        params: list = []
        if annotator:
            sql += " AND a.annotator = ?"
            params.append(annotator)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def pending_for_eval(self, annotator: str | None = None) -> list[dict]:
        sql = """
            SELECT e.job_id AS job_id, j.company AS company, j.title AS title
            FROM eval_dataset e
            JOIN jobs j ON j.id = e.job_id
            WHERE NOT EXISTS (
                SELECT 1 FROM annotations a
                WHERE a.job_id = e.job_id{extra})
        """.format(extra=" AND a.annotator = ?" if annotator else "")
        params = [annotator] if annotator else []
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]


class EvalRepo:
    def __init__(self, conn):
        self.conn = conn

    def add(self, job_id: str) -> None:
        self.conn.execute(
            "INSERT INTO eval_dataset(job_id, added_at) VALUES(?,?) ON CONFLICT(job_id) DO NOTHING",
            (job_id, _now()),
        )
        self.conn.commit()

    def all_ids(self) -> list[str]:
        return [
            r[0] for r in self.conn.execute("SELECT job_id FROM eval_dataset ORDER BY added_at")
        ]


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


class ClaimExtractionRepo:
    """Claim 提取结果 DAO."""

    def __init__(self, conn):
        self.conn = conn

    def save(self, result: ClaimExtractionResult) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO claim_extractions(id, job_id, resume_version, claims_json,
                 gaps_json, evidence_matrix_json, extraction_tokens, extraction_cost, created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                result.id,
                result.job_id,
                result.resume_version,
                json.dumps([c.model_dump() for c in result.claims], ensure_ascii=False),
                json.dumps([g.model_dump() for g in result.gaps], ensure_ascii=False),
                json.dumps(
                    [e.model_dump() for e in result.evidence_matrix], ensure_ascii=False
                ),
                result.extraction_tokens,
                result.extraction_cost,
                _now(),
            ),
        )
        self.conn.commit()

    def get_by_job_id(self, job_id: str) -> ClaimExtractionResult | None:
        row = self.conn.execute(
            "SELECT * FROM claim_extractions WHERE job_id=? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        return ClaimExtractionResult(
            id=row["id"],
            job_id=row["job_id"],
            resume_version=row["resume_version"],
            claims=json.loads(row["claims_json"]),
            gaps=json.loads(row["gaps_json"]),
            evidence_matrix=json.loads(row["evidence_matrix_json"]),
            extraction_tokens=row["extraction_tokens"],
            extraction_cost=row["extraction_cost"],
        )


class ResumePatchRepo:
    """简历补丁 DAO."""

    def __init__(self, conn):
        self.conn = conn

    def save(self, patch: ResumePatch) -> None:
        hr_opener_text = patch.hr_opener.opener_text if patch.hr_opener else ""
        self.conn.execute(
            """INSERT OR REPLACE INTO resume_patches(id, job_id, bullet_rewrites_json,
                 missing_evidence_json, hr_opener_text, patch_markdown,
                 generation_tokens, generation_cost, created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                patch.id,
                patch.job_id,
                json.dumps(
                    [b.model_dump() for b in patch.bullet_rewrites], ensure_ascii=False
                ),
                json.dumps(
                    [m.model_dump() for m in patch.missing_evidence], ensure_ascii=False
                ),
                hr_opener_text,
                patch.patch_markdown,
                patch.generation_tokens,
                patch.generation_cost,
                _now(),
            ),
        )
        self.conn.commit()

    def get_by_job_id(self, job_id: str) -> ResumePatch | None:
        row = self.conn.execute(
            "SELECT * FROM resume_patches WHERE job_id=? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        return ResumePatch(
            id=row["id"],
            job_id=row["job_id"],
            bullet_rewrites=json.loads(row["bullet_rewrites_json"]),
            missing_evidence=json.loads(row["missing_evidence_json"]),
            hr_opener=None,  # 简化：不反序列化 HROpener
            patch_markdown=row["patch_markdown"],
            generation_tokens=row["generation_tokens"],
            generation_cost=row["generation_cost"],
        )


class InterviewBriefRepo:
    """面试速览 DAO."""

    def __init__(self, conn):
        self.conn = conn

    def save(self, brief: InterviewBrief) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO interview_briefs(id, job_id, company_overview, tech_stack_json,
                 predicted_questions_json, followup_protocol_json, weak_area_drills_json,
                 evidence_summary_json, brief_markdown, generation_tokens, generation_cost,
                 created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                brief.id,
                brief.job_id,
                brief.company_overview,
                json.dumps(brief.tech_stack, ensure_ascii=False),
                json.dumps(
                    [q.model_dump() for q in brief.predicted_questions], ensure_ascii=False
                ),
                json.dumps(
                    [f.model_dump() for f in brief.followup_protocol], ensure_ascii=False
                ),
                json.dumps(
                    [d.model_dump() for d in brief.weak_area_drills], ensure_ascii=False
                ),
                json.dumps(brief.evidence_summary, ensure_ascii=False),
                brief.brief_markdown,
                brief.generation_tokens,
                brief.generation_cost,
                _now(),
            ),
        )
        self.conn.commit()

    def get_by_job_id(self, job_id: str) -> InterviewBrief | None:
        row = self.conn.execute(
            "SELECT * FROM interview_briefs WHERE job_id=? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        return InterviewBrief(
            id=row["id"],
            job_id=row["job_id"],
            company_overview=row["company_overview"],
            tech_stack=json.loads(row["tech_stack_json"]),
            predicted_questions=json.loads(row["predicted_questions_json"]),
            followup_protocol=json.loads(row["followup_protocol_json"]),
            weak_area_drills=json.loads(row["weak_area_drills_json"]),
            evidence_summary=json.loads(row["evidence_summary_json"]),
            brief_markdown=row["brief_markdown"],
            generation_tokens=row["generation_tokens"],
            generation_cost=row["generation_cost"],
        )
