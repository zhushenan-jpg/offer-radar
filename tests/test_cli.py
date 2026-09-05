"""CLI 端到端测试(全程 --fake,不触网)."""

from pathlib import Path

from typer.testing import CliRunner

from jobpilot.app.cli import app

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "examples" / "jobs"


def run(tmp_path, job_name):
    runner = CliRunner()
    return runner.invoke(
        app,
        [
            "score",
            "--file",
            str(JOBS / job_name),
            "--profile",
            str(ROOT / "profile.example.yaml"),
            "--db",
            str(tmp_path / "cli.db"),
            "--fake",
        ],
    )


class TestScoreCommand:
    def test_three_jds_exit_zero(self, tmp_path):
        for name in ("jd_backend_intern.md", "jd_frontend_intern.md", "jd_data_engineer.md"):
            result = run(tmp_path, name)
            assert result.exit_code == 0, result.output
            assert "综合匹配" in result.output

    def test_scores_persisted(self, tmp_path):
        from jobpilot.storage.db import Storage

        for name in ("jd_backend_intern.md", "jd_frontend_intern.md", "jd_data_engineer.md"):
            run(tmp_path, name)
        storage = Storage.open(tmp_path / "cli.db")
        count = storage.conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        assert count == 3
