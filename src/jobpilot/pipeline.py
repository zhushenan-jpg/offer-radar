"""流水线编排:采集 → 清洗 → 评分 → 周报。

两条执行路径:
- crew 模式(默认,真实调用):crewAI Crew 的 Scout/Matcher agent 通过工具驱动
  采集与评分,Reporter agent 生成摘要,摘要注入周报;
- 确定性模式(--fake / --no-crew):同一套函数直接顺序执行,零 LLM 推理开销,
  用于离线演示与测试。
"""

import asyncio
from pathlib import Path

import httpx
import yaml
from pydantic import BaseModel

from jobpilot.collectors import CollectorError, get_collector
from jobpilot.collectors.clean import clean_jd
from jobpilot.collectors.dedup import dedupe_jobs
from jobpilot.reporting import render_weekly

USER_AGENT = "OfferRadar/0.1 (student resume project; polite crawler via official APIs)"
CONCURRENCY = 5


class SourceCfg(BaseModel):
    source: str
    slug: str
    name: str

    def label(self) -> str:
        return f"{self.name}({self.slug})"


def load_sources(path: Path | str) -> list[SourceCfg]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [SourceCfg.model_validate(item) for item in data]


async def collect_all(
    storage, sources: list[SourceCfg | dict], *, client=None, cfg=None
) -> dict[str, int]:
    """并发采集全部来源;失败源记 -1 跳过;返回 {来源: 新职位数}.

    sources 兼容 dict 与 SourceCfg(调度器传入的是 yaml 原始 dict).
    """
    sources = [s if isinstance(s, SourceCfg) else SourceCfg.model_validate(s) for s in sources]
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT})
    sem = asyncio.Semaphore(CONCURRENCY)
    summary: dict[str, int] = {}

    async def _one(src: SourceCfg) -> None:
        async with sem:
            try:
                jobs = await get_collector(src.source, client, cfg=cfg).fetch(src.slug, src.name)
            except CollectorError as e:
                print(f"[采集跳过] {src.name}({src.slug}): {e}")
                summary[src.label()] = -1
                return
            kept, _removed = dedupe_jobs(jobs)
            new = 0
            for job in kept:
                is_new = storage.jobs.get(job.id) is None
                storage.jobs.upsert(job)
                if is_new:
                    new += 1
            summary[src.label()] = new

    await asyncio.gather(*(_one(s) for s in sources))
    if own_client:
        await client.aclose()
    return summary


def clean_pending(storage) -> int:
    """对 status=new 的职位做样板清洗,流转到 parsed;返回处理条数."""
    n = 0
    for job_id in storage.jobs.ids_by_status("new"):
        job = storage.jobs.get(job_id)
        if job is None:
            continue
        storage.jobs.set_clean_md(job_id, clean_jd(job.description_md))
        storage.jobs.update_status(job_id, "parsed")
        n += 1
    return n


def parse_jd(jd_md: str) -> dict:
    """简单 JD 解析:提取技能、要求等结构化信息."""
    import re

    # 提取技能关键词
    skill_patterns = [
        r"Python|Java|JavaScript|TypeScript|React|Vue|Angular|Node\.js",
        r"SQL|MySQL|PostgreSQL|Redis|MongoDB|Docker|Kubernetes|AWS|Azure|GCP",
        r"Git|Linux|Shell|Bash|CI/CD|Jenkins|GitHub Actions",
        r"FastAPI|Django|Flask|Spring Boot|Express",
        r"机器学习|深度学习|TensorFlow|PyTorch|NLP",
    ]

    skills = []
    for pattern in skill_patterns:
        matches = re.findall(pattern, jd_md, re.IGNORECASE)
        skills.extend(matches)

    # 提取要求
    requirements = []
    lines = jd_md.split("\n")
    for line in lines:
        if any(kw in line for kw in ["要求", "必须", "需要", "必备", "熟悉", "掌握"]):
            requirements.append(line.strip())

    return {
        "skills": list(set(skills)),
        "requirements": requirements,
        "raw_text": jd_md,
    }


def score_pending(storage, profile, gateway, limit: int | None = None) -> int:
    """对 status=parsed 的职位逐条评分(走网关),流转到 scored;返回处理条数."""
    from jobpilot.agents.matcher import score_and_store

    ids = storage.jobs.ids_by_status("parsed")
    if limit is not None:
        ids = ids[:limit]
    for job_id in ids:
        clean_md = storage.jobs.get_clean(job_id) or (storage.jobs.get(job_id).description_md)
        parsed_jd = parse_jd(clean_md)
        score_and_store(
            gateway, storage, profile, clean_md,
            parsed_jd=parsed_jd, job_id=job_id
        )
        storage.jobs.update_status(job_id, "scored")
    return len(ids)


async def run_report(
    storage,
    profile,
    sources: list[SourceCfg | dict],
    *,
    gateway,
    use_crew: bool = True,
    out_dir: Path | str = "docs/reports",
    db_path: Path | str = "jobpilot.db",
    top_n: int = 10,
    limit: int | None = None,
) -> Path:
    sources = [s if isinstance(s, SourceCfg) else SourceCfg.model_validate(s) for s in sources]
    exec_summary = ""

    if use_crew:
        try:
            from jobpilot.agents.crew import build_crew

            crew = build_crew(gateway.cfg, storage, profile, sources)
            exec_summary = str(crew.kickoff() or "").strip()
        except ImportError:
            use_crew = False  # crewai 未安装时自动降级,保证流水线可用
    if not use_crew:
        await collect_all(storage, sources, cfg=gateway.cfg)
        clean_pending(storage)
        score_pending(storage, profile, gateway, limit=limit)

    return render_weekly(
        storage,
        profile_name=profile.name,
        out_dir=Path(out_dir),
        top_n=top_n,
        exec_summary=exec_summary,
    )
