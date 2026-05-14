"""Shared fixtures."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from spreadtrader.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def cfg():
    return load_config(REPO_ROOT / "config" / "strategy.yaml")


@pytest.fixture
def mean_reverting_daily():
    """Synthetic daily prices: an Ornstein-Uhlenbeck-style mean-reverting DE
    level and neighbours, so the mean-reversion strategy *should* profit."""
    n = 800
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    rng = np.random.default_rng(42)

    def ou(mu, theta, sigma):
        x = np.zeros(n)
        x[0] = mu
        for t in range(1, n):
            x[t] = x[t - 1] + theta * (mu - x[t - 1]) + rng.normal(0, sigma)
        return x

    de = ou(100, 0.3, 15)
    data = {"DE_LU": de}
    for z, mu in [("FR", 95), ("NL", 105), ("BE", 100), ("AT", 90),
                  ("CH", 98), ("DK1", 102)]:
        # neighbour = shared level + own mean-reverting spread
        data[z] = de - ou(100 - mu, 0.4, 8)
    return pd.DataFrame(data, index=idx)


@pytest.fixture
def trending_daily():
    """Synthetic trending prices (random walk with drift): mean reversion should
    NOT profit here -- a sanity check that the strategy isn't magic."""
    n = 800
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    rng = np.random.default_rng(7)
    de = 100 + np.cumsum(rng.normal(0.1, 5, n))
    data = {"DE_LU": de}
    for z in ["FR", "NL", "BE", "AT", "CH", "DK1"]:
        data[z] = de - (5 + np.cumsum(rng.normal(0.05, 3, n)))
    return pd.DataFrame(data, index=idx)
