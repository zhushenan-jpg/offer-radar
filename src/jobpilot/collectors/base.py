"""采集器基类与错误类型."""

from abc import ABC, abstractmethod

import httpx

from jobpilot.models.job import JobPosting


class CollectorError(Exception):
    """单源采集失败(网络/限流/slug 无效),由上层降级跳过."""


class Collector(ABC):
    source: str = ""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    @abstractmethod
    async def fetch(self, slug: str, company: str) -> list[JobPosting]:
        """拉取一个公司的全部在招职位并归一化为 JobPosting."""


def is_remote(location: str) -> bool:
    low = location.lower()
    return "remote" in low or "远程" in location
