"""浏览器兜底采集(FR9,二期)。

仅用于无公开 API 的招聘页:browser-use agent 阅读页面并结构化抽取。
合规约束:遵守 robots.txt 与频率限制,只读取公开可见内容,绝不自动提交任何表单。
browser-use 为可选依赖:未安装时 fetch 抛 CollectorError(上层自动跳过该源)。
"""

import asyncio
import json
import logging

from jobpilot.models.job import JobPosting

from .base import Collector, CollectorError, is_remote

logger = logging.getLogger(__name__)

INSTALL_HINT = "pip install browser-use && browser-use install"

TASK_TEMPLATE = (
    "访问 {url},提取页面上所有正在招聘的职位条目。"
    "只提取页面真实可见的内容,禁止编造;没有职位列表时输出空数组。"
    "按以下 JSON 格式输出,不要任何其他文字:\n"
    '[{{"title": "...", "location": "...", "url": "...", "description_md": "职位描述正文"}}]'
)


def _default_runner(url: str, cfg) -> list[dict]:
    """browser-use 默认执行器(可选依赖,调用方环境需已安装)."""
    try:
        from browser_use import Agent
        from browser_use.llm import ChatOpenAI
    except ImportError as e:
        raise CollectorError(f"浏览器兜底采集需要安装 browser-use({INSTALL_HINT})") from e

    agent = Agent(
        task=TASK_TEMPLATE.format(url=url),
        llm=ChatOpenAI(
            model=cfg.model, base_url=cfg.base_url, api_key=cfg.api_key.get_secret_value()
        ),
    )
    result = agent.run()
    content = getattr(result, "content", "") or str(result)
    start, end = content.find("["), content.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        return json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        logger.warning("browser-use 输出无法解析为 JSON:%s", content[:200])
        return []


class BrowserCollector(Collector):
    source = "browser"

    def __init__(self, client, runner=None, cfg=None):
        super().__init__(client)
        self._runner = runner or (lambda url: _default_runner(url, cfg))

    async def _robots_allows(self, url: str) -> bool:
        """robots.txt 校验:显式 Disallow 则拒绝;无 robots/获取失败视为允许."""
        from urllib import robotparser
        from urllib.parse import urlparse

        parsed = urlparse(url)
        rp = robotparser.RobotFileParser()
        try:
            resp = await self._client.get(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
            if resp.status_code in (401, 403):
                return False  # robots 存在但禁止读取 → 保守视为不允许
            rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
        except Exception:  # noqa: BLE001 - robots 获取失败不阻塞,与主流爬虫惯例一致
            return True
        return rp.can_fetch("*", url)

    async def fetch(self, slug: str, company: str) -> list[JobPosting]:
        """slug 即目标页面 URL。browser-use 为同步阻塞,放入线程执行."""
        if not await self._robots_allows(slug):
            raise CollectorError(f"robots.txt 不允许采集 {slug},已跳过")
        items = await asyncio.to_thread(self._runner, slug)
        jobs = []
        for item in items:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            loc = (item.get("location") or "").strip()
            jobs.append(
                JobPosting(
                    id=JobPosting.compute_id("browser", company, title, loc),
                    source="browser",
                    company=company,
                    title=title,
                    location=loc,
                    remote=is_remote(loc),
                    url=item.get("url") or slug,
                    description_md=(item.get("description_md") or "").strip(),
                )
            )
        return jobs
