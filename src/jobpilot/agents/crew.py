"""crewAI 编排层:M2 的四 Agent 装配。

架构说明(对应详细设计 §5.2 的落地取舍):
- 结构化业务调用(评分)一律经 llm_gateway,享受缓存/计量/预算;
- crew agent 自身的推理调用走 crewai→litellm(openai 兼容端点直连 GLM),
  通过 litellm success_callback 把用量写回同一张 usage 表(module='crew'),
  保证成本归因仍是全局一份。
- 采集/清洗/评分/渲染的真实工作在确定性函数里(pipeline.py),agent 通过
  工具驱动它们,避免"为 30 个公司跑 30 次 LLM 决定要不要爬"这类开销。
"""

import asyncio

from jobpilot.pipeline import clean_pending, collect_all, score_pending


def _register_metering(cfg, storage) -> None:
    """crew 内部 LLM 调用的用量归因到 usage 表(module='crew')."""
    try:
        import litellm
    except ImportError:
        return
    if getattr(litellm, "_jobpilot_metering_registered", False):
        return

    def _record(kwargs, completion_response, start_time, end_time):
        try:
            usage = getattr(completion_response, "usage", None)
            pt = getattr(usage, "prompt_tokens", 0) or 0
            ct = getattr(usage, "completion_tokens", 0) or 0
            cost = (pt * cfg.price_input_cny_per_mtok + ct * cfg.price_output_cny_per_mtok) / 1e6
            storage.usage.record("crew", cfg.model, pt, ct, round(cost, 6), 0)
        except Exception:  # noqa: BLE001, S110 - 计量失败绝不能影响主流程
            pass

    litellm.success_callback = [*list(litellm.success_callback or []), _record]
    litellm._jobpilot_metering_registered = True


def build_crew(cfg, storage, profile, sources):
    from crewai import LLM, Agent, Crew, Process, Task

    _register_metering(cfg, storage)
    llm = LLM(
        model=f"openai/{cfg.model}",
        base_url=cfg.base_url,
        api_key=cfg.api_key.get_secret_value(),
        temperature=cfg.temperature,
        top_p=cfg.top_p,
    )

    from crewai.tools import BaseTool

    class CollectAllTool(BaseTool):
        name: str = "collect_all_sources"
        description: str = (
            "采集全部目标公司的在招职位(Greenhouse/Lever 官方 API),自动清洗样板内容。"
            "无需参数,调用一次即可;返回各公司新增职位数摘要。"
        )
        _storage: object = None
        _sources: list = None
        _db_path: str = ""

        def __init__(self, storage, sources, db_path):
            super().__init__()
            self._storage = storage
            self._sources = sources
            self._db_path = str(db_path)

        def _run(self) -> str:
            summary = asyncio.run(collect_all(self._storage, self._sources))
            cleaned = clean_pending(self._storage)
            ok = {k: v for k, v in summary.items() if v >= 0}
            skipped = [k for k, v in summary.items() if v < 0]
            return (
                f"采集完成:新增职位 {sum(ok.values())} 条("
                + ", ".join(f"{k}: +{v}" for k, v in ok.items())
                + f");已清洗 {cleaned} 条;"
                + (f"失败跳过:{', '.join(skipped)}" if skipped else "无失败来源")
            )

    class ScorePendingTool(BaseTool):
        name: str = "score_pending_jobs"
        description: str = (
            "对全部已清洗职位执行简历匹配评分(四维 rubric,带 JD 原文证据),"
            "无需参数;返回评分摘要与最高分职位。"
        )
        _storage: object = None
        _profile: object = None
        _gateway: object = None

        def __init__(self, storage, profile, gateway):
            super().__init__()
            self._storage = storage
            self._profile = profile
            self._gateway = gateway

        def _run(self) -> str:
            n = score_pending(self._storage, self._profile, self._gateway)
            rows = self._storage.jobs.scored_with_scores()
            top = rows[0] if rows else None
            return f"评分完成 {n} 条;" + (
                f"当前最高分:{top['company']} {top['title']} {top['overall']}/100"
                if top
                else "无待评分职位"
            )

    scout = Agent(
        role="职位搜集专员",
        goal="驱动采集工具,拿到本周目标公司全部新职位并如实汇报",
        backstory="你负责 OfferRadar 的数据入口,只信工具返回的结果,绝不编造职位。",
        llm=llm,
        tools=[CollectAllTool(storage, sources, "jobpilot.db")],
        allow_delegation=False,
        verbose=False,
    )
    matcher = Agent(
        role="匹配评估师",
        goal="驱动评分工具,为每条新职位产出带证据的匹配评分",
        backstory="你负责评分环节的执行与质检,关注评分数量与最高分职位。",
        llm=llm,
        tools=[ScorePendingTool(storage, profile, None)],
        allow_delegation=False,
        verbose=False,
    )
    reporter = Agent(
        role="求职报告主编",
        goal="基于已评分职位写出 3-5 句中文周摘要:高匹配职位、整体情况、下一步建议",
        backstory="你为求职学生写本周摘要,务实、具体、不空话。",
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )

    return Crew(
        agents=[scout, matcher, reporter],
        tasks=[
            Task(
                description="调用 collect_all_sources 工具完成本周职位采集与清洗。",
                expected_output="一行采集摘要:新增数量、各来源明细、失败来源。",
                agent=scout,
            ),
            Task(
                description="调用 score_pending_jobs 工具,为全部已清洗职位评分。",
                expected_output="一行评分摘要:评分条数与最高分职位。",
                agent=matcher,
            ),
            Task(
                description=(
                    "根据上一任务的评分结果,写 3-5 句中文周摘要,"
                    "点出高匹配职位与下一步建议,不要罗列全部数据。"
                ),
                expected_output="3-5 句中文摘要文本。",
                agent=reporter,
            ),
        ],
        process=Process.sequential,
        verbose=False,
    )
