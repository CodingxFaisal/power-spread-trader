"""Reproduce every result and chart in the README.

    python scripts/run_all.py

Downloads prices (once, cached), runs the backtest, the cost-sensitivity sweep
and the robustness checks. A couple of minutes on a laptop.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PY = sys.executable

STEPS = [
    ["download_prices.py"],
    ["run_backtest.py"],
    ["run_cost_sensitivity.py"],
    ["run_robustness.py"],
]


def main() -> None:
    for step in STEPS:
        print(f"\n{'=' * 70}\n$ python scripts/{' '.join(step)}\n{'=' * 70}")
        subprocess.run([PY, str(SCRIPTS / step[0]), *step[1:]], check=True)


if __name__ == "__main__":
    main()
