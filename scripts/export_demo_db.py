"""把本地库导出为部署用演示库:deploy/demo_jobpilot.db(单文件、无缓存数据)。

用于 Streamlit Community Cloud 等只读演示:面板设 JOBPLOT_DB 指向它即可。
"""

import sqlite3
from pathlib import Path

SRC = Path("jobpilot.db")
DST_DIR = Path("deploy")
DST = DST_DIR / "demo_jobpilot.db"


def main() -> None:
    if not SRC.exists():
        raise SystemExit("找不到 jobpilot.db:先跑一次 jobpilot report")
    DST_DIR.mkdir(exist_ok=True)
    src = sqlite3.connect(SRC)
    src.execute("VACUUM INTO ?", (str(DST),))  # 干净的单文件副本(含 WAL 合并)
    src.close()
    dst = sqlite3.connect(DST)
    dst.execute("DELETE FROM llm_cache")  # 演示库不需要缓存数据
    dst.commit()
    jobs = dst.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    scores = dst.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
    dst.close()
    size_kb = DST.stat().st_size // 1024
    print(f"演示库已导出:{DST}(jobs={jobs}, scores={scores}, {size_kb} KB)")


if __name__ == "__main__":
    main()
