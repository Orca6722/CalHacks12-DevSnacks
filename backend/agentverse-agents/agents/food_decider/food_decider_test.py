import os
import sys
import subprocess
from pathlib import Path

# Ensure GROQ key is present
if "GROQ_API_KEY" not in os.environ:
    raise RuntimeError("Set GROQ_API_KEY before running this test!")

# Resolve repo root and important paths regardless of where you run from
THIS_FILE = Path(__file__).resolve()
FOOD_DECIDER_MAIN = THIS_FILE.parent / "main.py"  # .../agents/food_decider/main.py
PKG_ROOT = THIS_FILE.parents[2]  # .../backend/agentverse-agents

# Child env: add our package root to PYTHONPATH so 'shared' imports work
child_env = os.environ.copy()
child_env["PYTHONPATH"] = f"{PKG_ROOT}:{child_env.get('PYTHONPATH','')}"

tests = [
    {
        "label": "Focused / Calm dev commits",
        "commits": [
            "refactor: simplify dependency injection system",
            "chore: improve code readability",
            "docs: update README with new examples",
        ],
    },
    {
        "label": "Stressed / Debugging session",
        "commits": [
            "fix: production crash in payment flow",
            "hotfix: patch websocket reconnect bug",
            "debug: temporary logging to trace memory leak",
        ],
    },
    {
        "label": "Celebratory / Energized release",
        "commits": [
            "feat: add launch banner for v2.0!",
            "chore: final release prep and tagging",
            "docs: announce release in CHANGELOG",
        ],
    },
    {
        "label": "Meh / Routine maintenance",
        "commits": [
            "chore: bump dependencies",
            "ci: update workflow versions",
            "style: reformat with black",
        ],
    },
]

for t in tests:
    print(f"\n=== TEST: {t['label']} ===")
    cmd = [sys.executable, str(FOOD_DECIDER_MAIN), "--demo"] + t["commits"]
    result = subprocess.run(
        cmd,
        env=child_env,
        cwd=PKG_ROOT.parent,  # run from repo "backend" dir; adjust if needed
        capture_output=True,
        text=True,
    )
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()

    if out:
        print(out)
    if err:
        print("[stderr]", err)
    print(f"[exit code] {result.returncode}")


