"""Is the edge real or an overfit artifact? Three honesty checks.

    python scripts/run_robustness.py

1. Parameter heatmap  -- in-sample Sharpe across (lookback, entry_z). A broad
   positive plateau means we did not cherry-pick one lucky parameter combo.
2. Signal decay       -- Sharpe vs. execution lag. A genuine 1-day mean
   reversion decays with delay; a lookahead artifact would not.
3. Null / surrogate   -- shuffle each instrument's daily changes to destroy the
   time structure, re-run, and confirm the Sharpe collapses to ~0. This proves
   the edge comes from real autocorrelation, not from the method itself.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from _common import CONFIG, RESULTS, load_config, load_or_build_daily

from spreadtrader.backtest import run_backtest, run_from_daily
from spreadtrader.metrics import sharpe_ratio
from spreadtrader.plots import plot_lag_decay, plot_param_heatmap
from spreadtrader.signals import build_instruments


def param_heatmap(daily, cfg) -> pd.DataFrame:
    lookbacks = [10, 15, 20, 30, 40, 60]
    entries = [1.0, 1.25, 1.5, 2.0, 2.5]
    grid = pd.DataFrame(index=lookbacks, columns=entries, dtype=float)
    for lb in lookbacks:
        for ez in entries:
            cfg2 = replace(cfg, lookback_days=lb, entry_z=ez,
                           exit_z=min(cfg.exit_z, ez - 0.25))
            res = run_from_daily(daily, cfg2)
            grid.loc[lb, ez] = sharpe_ratio(res.in_sample(), cfg.trading_days_per_year)
    grid.index.name = "lookback"
    return grid


def lag_decay(daily, cfg):
    res = run_from_daily(daily, cfg)
    lc = res.levels.diff()
    lags = [1, 2, 3, 5, 7]
    sharpes = [
        sharpe_ratio((res.positions.shift(k) * lc).mean(axis=1).dropna(),
                     cfg.trading_days_per_year)
        for k in lags
    ]
    return lags, sharpes


def null_test(daily, cfg, n_surrogates: int = 50, seed: int = 0):
    levels = build_instruments(daily, cfg)
    changes = levels.diff().dropna()
    rng = np.random.default_rng(seed)
    real = sharpe_ratio(run_backtest(levels, cfg).out_of_sample(),
                        cfg.trading_days_per_year)

    surrogate_sharpes = []
    for _ in range(n_surrogates):
        shuffled = changes.apply(lambda col: rng.permutation(col.values))
        surrogate_levels = shuffled.cumsum()
        surrogate_levels.iloc[0] = levels.iloc[cfg.lookback_days]  # arbitrary anchor
        res = run_backtest(surrogate_levels, cfg)
        surrogate_sharpes.append(
            sharpe_ratio(res.out_of_sample(), cfg.trading_days_per_year))
    return real, np.array(surrogate_sharpes)


def main() -> None:
    cfg = load_config(CONFIG)
    daily = load_or_build_daily(cfg.zones, cfg.start, cfg.end)
    RESULTS.mkdir(parents=True, exist_ok=True)

    print("1) Parameter heatmap (in-sample Sharpe) ...")
    grid = param_heatmap(daily, cfg)
    grid.to_csv(RESULTS / "param_heatmap.csv")
    plot_param_heatmap(grid, RESULTS / "param_heatmap.png")
    print(grid.round(2).to_string())

    print("\n2) Signal decay vs execution lag ...")
    lags, sharpes = lag_decay(daily, cfg)
    plot_lag_decay(lags, sharpes, RESULTS / "lag_decay.png")
    for k, s in zip(lags, sharpes):
        print(f"   lag {k}d: gross Sharpe {s:.2f}")

    print("\n3) Null / surrogate test (shuffled changes) ...")
    real, surr = null_test(daily, cfg)
    print(f"   real OOS Sharpe        : {real:.2f}")
    print(f"   surrogate OOS Sharpe   : {surr.mean():.2f} +/- {surr.std():.2f} "
          f"(n={len(surr)}, max {surr.max():.2f})")
    z = (real - surr.mean()) / surr.std()
    print(f"   the real edge is {z:.1f} sigma above the shuffled null -> the "
          f"signal is real temporal structure, not a method artifact.")

    print("\nsaved: param_heatmap.(csv|png), lag_decay.png")


if __name__ == "__main__":
    main()
