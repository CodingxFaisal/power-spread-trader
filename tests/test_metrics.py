"""Tests for the performance metrics."""

import numpy as np
import pandas as pd
import pytest

from spreadtrader.metrics import (
    hit_rate,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
)

TOL = 1e-9


def test_sharpe_matches_manual():
    pnl = pd.Series([1.0, -0.5, 2.0, 0.5, -1.0, 1.5])
    expected = pnl.mean() / pnl.std(ddof=1) * np.sqrt(365)
    assert sharpe_ratio(pnl, 365) == pytest.approx(expected)


def test_sharpe_zero_vol_is_nan():
    assert np.isnan(sharpe_ratio(pd.Series([1.0, 1.0, 1.0])))


def test_max_drawdown_known_curve():
    # Cumulative equity: 1, 3, 2, 5, 1  -> peak 3 then 2 (dd -1), peak 5 then 1 (dd -4)
    pnl = pd.Series([1, 2, -1, 3, -4], dtype=float)
    assert max_drawdown(pnl) == pytest.approx(-4.0)


def test_max_drawdown_monotonic_is_zero():
    pnl = pd.Series([1.0, 1.0, 1.0, 1.0])
    assert max_drawdown(pnl) == pytest.approx(0.0)


def test_hit_rate_ignores_flat_days():
    pnl = pd.Series([1.0, 0.0, -1.0, 2.0, 0.0])  # 3 active, 2 winners
    assert hit_rate(pnl) == pytest.approx(2 / 3)


def test_sortino_exceeds_sharpe_with_small_downside():
    # Big upside spikes inflate total volatility but not downside deviation, so
    # Sortino should exceed Sharpe here.
    pnl = pd.Series([5.0, -1.0, -2.0, 6.0, -1.0, 4.0])
    assert sortino_ratio(pnl) > sharpe_ratio(pnl)
