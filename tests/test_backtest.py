"""Tests for the backtest engine: no lookahead, cost accounting, and that the
strategy profits on mean-reverting data but not on trends."""

from dataclasses import replace

import numpy as np
import pandas as pd

from spreadtrader.backtest import run_backtest, run_from_daily
from spreadtrader.metrics import sharpe_ratio
from spreadtrader.signals import build_instruments


def test_pnl_has_no_lookahead(cfg, mean_reverting_daily):
    # gross_pnl[t] must equal position[t-1] * (level[t] - level[t-1]).
    inst = build_instruments(mean_reverting_daily, cfg)
    res = run_backtest(inst, cfg)
    expected = res.positions.shift(1) * inst.diff()
    pd.testing.assert_frame_equal(res.gross_pnl, expected)


def test_zero_turnover_means_zero_cost(cfg, mean_reverting_daily):
    # If nothing ever trades, cost must be exactly zero.
    inst = build_instruments(mean_reverting_daily, cfg)
    # entry_z huge -> never enters -> positions all flat -> no turnover.
    never = replace(cfg, entry_z=100.0, exit_z=99.0)
    res = run_backtest(inst, never)
    assert res.positions.abs().to_numpy().sum() == 0
    assert res.cost.fillna(0).to_numpy().sum() == 0.0


def test_costs_reduce_pnl(cfg, mean_reverting_daily):
    inst = build_instruments(mean_reverting_daily, cfg)
    cheap = replace(cfg, transaction_cost_eur_per_mwh=0.0, slippage_eur_per_mwh=0.0)
    dear = replace(cfg, transaction_cost_eur_per_mwh=5.0, slippage_eur_per_mwh=0.0)
    assert run_backtest(inst, dear).portfolio_pnl.sum() < \
        run_backtest(inst, cheap).portfolio_pnl.sum()


def test_profits_on_mean_reverting_data(cfg, mean_reverting_daily):
    res = run_from_daily(mean_reverting_daily, cfg)
    assert res.out_of_sample().sum() > 0
    assert sharpe_ratio(res.out_of_sample(), cfg.trading_days_per_year) > 0.5


def test_does_not_profit_on_trending_data(cfg, mean_reverting_daily, trending_daily):
    # A fade-the-move strategy should do markedly worse on trends than on
    # mean-reverting data -- proof the edge is the reversion, not the machinery.
    mr = run_from_daily(mean_reverting_daily, cfg).out_of_sample()
    tr = run_from_daily(trending_daily, cfg).out_of_sample()
    ppy = cfg.trading_days_per_year
    assert sharpe_ratio(tr, ppy) < sharpe_ratio(mr, ppy)
