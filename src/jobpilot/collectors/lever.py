"""Lever 官方 postings API:https://github.com/lever/postings-api"""

import httpx

from jobpilot.models.job import JobPosting

from .base import Collector, CollectorError, is_remote


class LeverCollector(Collector):
    source = "lever"

    async def fetch(self, slug: str, company: str) -> list[JobPosting]:
        url = f"https://api.lever.co/v0/postings/{slug}"
        try:
            resp = await self._client.get(url, params={"mode": "json"})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise CollectorError(f"lever/{slug}: {e}") from e
        jobs: list[JobPosting] = []
        for item in resp.json():
            loc = (item.get("categories") or {}).get("location") or ""
            dept = (item.get("categories") or {}).get("team") or ""
            md = self._description_md(item)
            jobs.append(
                JobPosting(
                    id=JobPosting.compute_id("lever", company, item["text"], loc),
                    source="lever",
                    company=company,
                    title=item["text"],
                    location=loc,
                    remote=is_remote(loc),
                    url=item.get("hostedUrl") or "",
                    department=dept,
                    description_md=md,
                )
            )
        return jobs

    @staticmethod
    def _description_md(item: dict) -> str:
        parts = [item.get("descriptionPlain") or ""]
        for lst in item.get("lists") or []:
            heading = lst.get("text") or ""
            bullets = "\n".join(f"- {it.get('content', '')}" for it in lst.get("content") or [])
            if heading or bullets:
                parts.append(f"### {heading}\n{bullets}".strip())
        return "\n\n".join(p for p in parts if p).strip()
