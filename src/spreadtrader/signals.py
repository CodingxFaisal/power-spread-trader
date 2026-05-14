"""Signal construction: tradable instruments and the mean-reversion rule.

Instruments
-----------
* Outright: the reference zone's daily-baseload price level (optional).
* Spreads: reference_zone minus each other zone's daily-baseload price.

Both are traded as daily-settled financial positions (a spread swap / CfD for
the spreads). See the README for the price-taker / settlement assumptions.

The signal
----------
For each instrument we z-score the level against a trailing window and *fade*
deviations (classic mean reversion): a spread far above its recent mean is
expected to fall, so we go short; far below, we go long. Entry and exit use a
hysteresis band (``entry_z`` > ``exit_z``) to avoid churning around the mean.

No lookahead: the z-score on day *t* uses only prices up to and including day
*t*, and the resulting position earns the *t -> t+1* move (applied in the
backtest via a one-day shift).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spreadtrader.config import StrategyConfig


def build_instruments(daily: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Construct the tradable level series (outright + cross-border spreads)."""
    ref = cfg.reference_zone
    cols: dict[str, pd.Series] = {}
    if cfg.include_outright:
        cols[ref] = daily[ref]
    for z in cfg.zones:
        if z != ref:
            cols[f"{ref}-{z}"] = daily[ref] - daily[z]
    return pd.DataFrame(cols, index=daily.index)


def zscore(levels: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Rolling z-score of each column (trailing mean/std, no lookahead)."""
    mean = levels.rolling(lookback, min_periods=lookback).mean()
    std = levels.rolling(lookback, min_periods=lookback).std(ddof=1)
    return (levels - mean) / std.replace(0.0, np.nan)


def _positions_from_z(z: pd.Series, entry: float, exit_: float, cap: float) -> pd.Series:
    """Hysteresis state machine, vectorised via forward-fill.

    target = short (-cap) when z > entry, long (+cap) when z < -entry, flat (0)
    when |z| < exit, and "hold previous" in between (encoded as NaN then ffill).
    """
    raw = pd.Series(np.nan, index=z.index, dtype="float64")
    raw[z > entry] = -cap          # fade the overshoot
    raw[z < -entry] = cap          # fade the undershoot
    raw[z.abs() < exit_] = 0.0     # take profit / go flat near the mean
    return raw.ffill().fillna(0.0)


def mean_reversion_positions(levels: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Positions held into the next day for every instrument.

    ``position[t]`` is decided at the close of day *t* from ``zscore[t]`` and,
    in the backtest, earns the day *t -> t+1* change.
    """
    z = zscore(levels, cfg.lookback_days)
    pos = {
        col: _positions_from_z(z[col], cfg.entry_z, cfg.exit_z, cfg.max_position)
        for col in levels.columns
    }
    return pd.DataFrame(pos, index=levels.index)
