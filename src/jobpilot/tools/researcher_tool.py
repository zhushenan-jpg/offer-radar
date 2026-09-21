"""公司调研工具:基于 LLM 网关 + 网页搜索生成公司调研报告.

设计文档创新点 3 的实现:将调研能力封装为可复用工具,供 InterviewPrep 等模块调用.
不引入 gpt-researcher 重依赖,而是用 DuckDuckGo 搜索 + LLM 网关组合实现同等能力.
"""

import hashlib

from jobpilot.llm_gateway.gateway import LLMGateway, make_cache_key

RESEARCHER_VERSION = "1.0"

SYSTEM_RESEARCHER = """你是一位专业的公司调研分析师。根据提供的搜索结果，生成结构化的公司调研报告。

报告必须包含以下部分：
1. 公司概况（业务、规模、总部、融资情况）
2. 技术栈与工程文化
3. 行业口碑与员工评价
4. 常见面试流程与题目类型
5. 薪资水平参考

要求：
- 信息必须来源于提供的搜索结果，不要编造
- 如果某项信息搜索结果中没有，明确标注"未找到相关信息"
- 用中文输出，保持客观专业"""


def _search_company(company_name: str, max_results: int = 5) -> str:
    """使用 DuckDuckGo 搜索公司信息."""
    try:
        from duckduckgo_search import DDGS
        queries = [
            f"{company_name} company engineering culture tech stack",
            f"{company_name} glassdoor interview questions",
        ]
        all_results = []
        with DDGS() as ddgs:
            for q in queries:
                try:
                    results = list(ddgs.text(q, max_results=max_results))
                    all_results.extend(results)
                except Exception:
                    continue

        if not all_results:
            return "搜索未返回结果。"

        # 格式化搜索结果
        lines = []
        seen_titles = set()
        for r in all_results:
            title = r.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"### {title}\n{body}\n来源: {href}\n")

        return "\n".join(lines) if lines else "搜索未返回有效结果。"
    except ImportError:
        return "搜索模块未安装(duckduckgo-search)。"
    except Exception as e:
        return f"搜索出错: {e}"


class ResearcherTool:
    """公司调研工具.

    使用 DuckDuckGo 搜索 + LLM 网关生成结构化的公司调研报告.
    结果会被缓存,相同公司的重复调研不会消耗额外 API 调用.

    Attributes:
        gateway: LLM 网关实例
        storage: 存储层实例(用于缓存)
    """

    def __init__(self, gateway: LLMGateway, storage=None):
        self.gateway = gateway
        self.storage = storage

    def research(self, company_name: str, job_title: str = "") -> str:
        """生成公司调研报告.

        Args:
            company_name: 公司名称
            job_title: 职位名称（可选，用于更精准的调研）

        Returns:
            str: Markdown 格式的公司调研报告
        """
        # 计算缓存键
        content_hash = hashlib.sha256(
            f"{company_name}|{job_title}|{RESEARCHER_VERSION}".encode()
        ).hexdigest()[:16]
        cache_key = make_cache_key(content_hash, self.gateway.cfg.model)

        # 检查缓存
        if self.storage:
            cached = self.storage.cache.get(cache_key)
            if cached:
                return cached

        # 搜索公司信息
        search_results = _search_company(company_name)

        # 构建 prompt
        prompt = f"""请基于以下搜索结果，为 "{company_name}" 生成一份结构化的公司调研报告。

{f"目标职位: {job_title}" if job_title else ""}

## 搜索结果

{search_results}

请按照系统提示的要求输出调研报告。"""

        # 调用 LLM
        report = self.gateway.text(
            prompt,
            system=SYSTEM_RESEARCHER,
            module="researcher",
        )

        # 缓存结果
        if self.storage:
            self.storage.cache.put(cache_key, report)

        return report


def research_company(
    gateway: LLMGateway,
    storage,
    company_name: str,
    job_title: str = "",
) -> str:
    """便捷函数:生成公司调研报告."""
    tool = ResearcherTool(gateway, storage)
    return tool.research(company_name, job_title)
