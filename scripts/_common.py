"""Shared helpers for the CLI scripts: path bootstrap + cached data loader."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from spreadtrader.config import load_config  # noqa: E402
from spreadtrader.data import fetch_prices, to_daily_baseload  # noqa: E402

DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
RESULTS = REPO_ROOT / "results"
CONFIG = REPO_ROOT / "config" / "strategy.yaml"


def load_or_build_daily(zones, start, end, refresh=False) -> pd.DataFrame:
    """Load cached daily-baseload prices, or download + build them from SMARD."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    key = "_".join(zones)
    cache = DATA_PROCESSED / f"daily_{key}_{start}_{end}.csv"
    if cache.exists() and not refresh:
        return pd.read_csv(cache, parse_dates=["date"], index_col="date")

    hourly = fetch_prices(list(zones), start, end, cache_dir=DATA_RAW)
    daily = to_daily_baseload(hourly)
    daily.to_csv(cache)
    return daily
