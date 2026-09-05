import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden(name: str):
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))
