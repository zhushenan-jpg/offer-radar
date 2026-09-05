"""职位去重:精确 id + 同公司内标题归一化/模糊匹配."""

import re

from rapidfuzz.fuzz import token_sort_ratio

from jobpilot.models.job import JobPosting

FUZZY_THRESHOLD = 92


def _norm_title(title: str) -> str:
    """小写 + 去空白与标点:'Backend Intern - Shanghai' → 'backendinternshanghai'."""
    return re.sub(r"[\s\W_]+", "", title.lower(), flags=re.UNICODE)


def dedupe_jobs(
    jobs: list[JobPosting], threshold: int = FUZZY_THRESHOLD
) -> tuple[list[JobPosting], int]:
    """返回 (保留列表, 去重数量)。保持输入顺序(调用方应先按 new→old 排)."""
    seen_ids: set[str] = set()
    titles_by_company: dict[tuple[str, str], list[str]] = {}
    kept: list[JobPosting] = []
    removed = 0
    for job in jobs:
        if job.id in seen_ids:
            removed += 1
            continue
        key = (job.source, job.company)
        norm = _norm_title(job.title)
        previous = titles_by_company.get(key, [])
        if norm and any(token_sort_ratio(norm, prev) >= threshold for prev in previous):
            removed += 1
            continue
        seen_ids.add(job.id)
        titles_by_company.setdefault(key, []).append(norm)
        kept.append(job)
    return kept, removed
