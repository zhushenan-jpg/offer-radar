"""JD 清洗:规则前置剥离样板段落,只删不改。

清洗只删两类内容:①样板段落(标题行 + 段内内容,直到下一个 markdown 标题);
②孤立样板行。核心 JD 内容(技能要求等)逐字保留,评分证据引用才可回溯。
"""

BOILERPLATE_HEADERS = (
    # 中文
    "薪资与福利",
    "薪酬福利",
    "福利待遇",
    "职位福利",
    "员工福利",
    "公司福利",
    "我们提供",
    "关于我们",
    "公司介绍",
    "加入我们",
    "为什么加入我们",
    "薪资范围",
    "薪酬范围",
    "工作地点",
    "联系方式",
    # 英文
    "perks",
    "benefits",
    "compensation",
    "total rewards",
    "salary & benefits",
    "about us",
    "about the company",
    "company description",
    "why join us",
    "what we offer",
    "our offer",
    # 法务/合规页脚(占篇幅、无评分价值)
    "eeo statement",
    "equal opportunity",
    "pay transparency",
    "eeo",
)


def _is_boilerplate_header(line: str) -> bool:
    stripped = line.lstrip("#").strip().rstrip(":：").strip().lower()
    if not stripped:
        return False
    return any(stripped == h or stripped.startswith(h + " ") for h in BOILERPLATE_HEADERS)


def clean_jd(md: str) -> str:
    out: list[str] = []
    skipping = False
    for line in md.splitlines():
        if _is_boilerplate_header(line):
            skipping = True
            continue
        if skipping and line.lstrip().startswith("#"):
            skipping = False  # 到达下一个 markdown 标题,样板段结束
        if not skipping:
            out.append(line)
    return "\n".join(out).strip()
