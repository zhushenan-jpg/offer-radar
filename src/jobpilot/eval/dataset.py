"""评测数据集管理:抽样入集、人工标注、取配对数据."""

import json
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()


def seed_dataset(storage, n: int = 40) -> list[dict]:
    """按公司均衡抽样 n 条职位进评测集;返回抽样明细."""
    companies = [
        r[0] for r in storage.conn.execute("SELECT DISTINCT company FROM jobs ORDER BY company")
    ]
    if not companies:
        return []
    per = max(1, n // len(companies))
    picked: list[dict] = []
    for company in companies:
        rows = storage.conn.execute(
            "SELECT id, company, title FROM jobs WHERE company=? ORDER BY title LIMIT ?",
            (company, per),
        ).fetchall()
        for r in rows:
            storage.eval_ds.add(r["id"])
            picked.append({"job_id": r["id"], "company": r["company"], "title": r["title"]})
    return picked


def record_annotation(storage, job_id: str, human_overall: float, annotator: str) -> None:
    storage.annotations.add(job_id, human_overall, annotator)


def pending_ids(storage, annotator: str | None = None) -> list[dict]:
    """评测集中还没有该标注人记录的职位."""
    return storage.annotations.pending_for_eval(annotator)


def pairs_with_predictions(storage, annotator: str | None = None) -> list[dict]:
    return storage.annotations.pairs_with_predictions(annotator)


def dump_dims(dims_json: str) -> dict:
    return json.loads(dims_json) if dims_json else {}
