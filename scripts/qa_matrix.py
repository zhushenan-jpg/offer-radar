"""总体测试阶段③:CLI 端到端矩阵(全新临时库,模拟新用户完整旅程)."""

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python"
TMP = Path(__file__).resolve().parents[1] / ".qa_tmp"
TMP.mkdir(exist_ok=True)
DB = TMP / "qa.db"

results = []


def run(label, args, expect_ok=True, timeout=900):
    proc = subprocess.run(  # noqa: PLW1510 - 返回码由矩阵自行判定
        [str(PY), "-m", "jobpilot", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    ok = (proc.returncode == 0) == expect_ok
    results.append((label, "PASS" if ok else "FAIL", proc.returncode))
    print(f"[{'PASS' if ok else 'FAIL'}] {label} (exit={proc.returncode})")
    if not ok:
        print("  stdout:", proc.stdout[-400:])
        print("  stderr:", proc.stderr[-400:])
    return proc


print("=== 1. score --fake(离线单条评分)===")
run(
    "score --fake",
    [
        "score",
        "--file",
        "examples/jobs/jd_backend_intern.md",
        "--profile",
        "profile.example.yaml",
        "--db",
        str(DB),
        "--fake",
    ],
)

print("=== 2. report --fake --limit 3(真实采集 15 源 + 假评分)===")
run(
    "report --fake --limit 3",
    ["report", "--profile", "profile.example.yaml", "--db", str(DB), "--fake", "--limit", "3"],
    timeout=1200,
)

print("=== 3. eval-seed --n 8 ===")
run("eval-seed", ["eval-seed", "--n", "8", "--db", str(DB)])

print("=== 4. eval-annotate ×3 ===")
import sqlite3

conn = sqlite3.connect(DB)
ids = [r[0] for r in conn.execute("SELECT job_id FROM eval_dataset LIMIT 3")]
conn.close()
for i, jid in enumerate(ids, 1):
    run(
        f"eval-annotate #{i}",
        [
            "eval-annotate",
            "--job-id",
            jid,
            "--score",
            str(40 + i * 10),
            "--annotator",
            "qa",
            "--db",
            str(DB),
        ],
    )

print("=== 5. eval-run --fake ===")
run(
    "eval-run --fake", ["eval-run", "--fake", "--db", str(DB), "--out", str(TMP / "eval-report.md")]
)

print("=== 6. watch --once --limit 2(真实 API,预算安全阀生效)===")
run(
    "watch --once --limit 2",
    ["watch", "--once", "--profile", "profile.example.yaml", "--db", str(DB), "--limit", "2"],
    timeout=900,
)

print("=== 7. parse-resume(文本型 PDF,零模型调用)===")
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", size=11)
pdf.multi_cell(
    0,
    6,
    "QA Tester - Python Developer with three years of backend experience. "
    "Skills: Python, FastAPI, SQL, Docker, Linux, Git, REST APIs. "
    "Experience: built payment notification services and data pipelines.",
)
pdf_path = TMP / "qa_resume.pdf"
pdf.output(str(pdf_path))
prof_copy = TMP / "qa_profile.yaml"
data = yaml.safe_load((ROOT / "profile.example.yaml").read_text(encoding="utf-8"))
prof_copy.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
run("parse-resume", ["parse-resume", "--file", str(pdf_path), "--out", str(prof_copy)])

print("=== 8. 错误路径:无标注评测集 ===")
run("eval-run 空库报错", ["eval-run", "--fake", "--db", str(TMP / "empty.db")], expect_ok=False)

print("\n=== 矩阵结果汇总 ===")
fails = [r for r in results if r[1] == "FAIL"]
for label, status, code in results:
    print(f"  [{status}] {label}")
print(f"\n合计 {len(results)} 项,失败 {len(fails)} 项")
sys.exit(1 if fails else 0)
