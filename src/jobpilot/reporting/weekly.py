"""周报渲染:SQLite 数据 → Jinja2 → Markdown."""

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent / "templates"


def current_week_label() -> str:
    iso = datetime.now(UTC).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def render_weekly(
    storage,
    *,
    profile_name: str,
    out_dir: Path,
    period: str | None = None,
    top_n: int = 10,
    exec_summary: str = "",
) -> Path:
    rows = storage.jobs.scored_with_scores()
    period = period or current_week_label()
    cost = storage.usage.month_cost_by_module()
    review = [r for r in rows if r["review_status"] == "review"]
    rubric_version = rows[0]["rubric_version"] if rows else "-"

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=("html",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    md = env.get_template("weekly.md.j2").render(
        period=period,
        profile_name=profile_name,
        rubric_version=rubric_version,
        jobs=rows[:top_n],
        total=len(rows),
        review=review,
        cost=cost,
        exec_summary=exec_summary.strip(),
    )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{period}.md"
    path.write_text(md, encoding="utf-8")

    storage.conn.execute(
        "INSERT INTO reports(period, path, cost_cny, created_at) VALUES(?,?,?,?)",
        (period, str(path), sum(cost.values()), datetime.now(UTC).isoformat()),
    )
    storage.conn.commit()
    return path
