"""Greenhouse 官方 boards API:https://developers.greenhouse.io/job-board.html"""

import html

import html2text
import httpx

from jobpilot.models.job import JobPosting

from .base import Collector, CollectorError, is_remote

_converter = html2text.HTML2Text()
_converter.bodywidth = 0  # 禁止换行折叠,保证 evidence 逐字引用可用


class GreenhouseCollector(Collector):
    source = "greenhouse"

    async def fetch(self, slug: str, company: str) -> list[JobPosting]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            resp = await self._client.get(url, params={"content": "true"})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise CollectorError(f"greenhouse/{slug}: {e}") from e
        jobs: list[JobPosting] = []
        for item in resp.json().get("jobs", []):
            raw_html = html.unescape(item.get("content") or "")
            md = _converter.handle(raw_html).strip()
            loc = (item.get("location") or {}).get("name") or ""
            dept = ", ".join(d.get("name", "") for d in item.get("departments") or [])
            jobs.append(
                JobPosting(
                    id=JobPosting.compute_id("greenhouse", company, item["title"], loc),
                    source="greenhouse",
                    company=company,
                    title=item["title"],
                    location=loc,
                    remote=is_remote(loc),
                    url=item.get("absolute_url") or "",
                    department=dept,
                    description_md=md,
                )
            )
        return jobs
