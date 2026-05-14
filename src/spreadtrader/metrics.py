"""Risk-adjusted performance metrics.

The strategy is self-financing and dollar-neutral-ish (spreads), so "return"
is the daily P&L per unit of notional (EUR per MWh position). All metrics are
computed on that P&L series -- exactly the language a trading desk uses:
Sharpe and Sortino for risk-adjusted return, max drawdown and Calmar for pain,
hit rate and turnover for how the money is actually made.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def annualized_pnl(pnl: pd.Series, periods_per_year: int = 365) -> float:
    return float(pnl.mean() * periods_per_year)


def sharpe_ratio(pnl: pd.Series, periods_per_year: int = 365) -> float:
    """Annualized Sharpe of a P&L series (risk-free rate assumed 0)."""
    sd = pnl.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float(pnl.mean() / sd * np.sqrt(periods_per_year))


def sortino_ratio(pnl: pd.Series, periods_per_year: int = 365) -> float:
    """Like Sharpe but penalises only downside deviation."""
    downside = pnl[pnl < 0]
    dd = downside.std(ddof=1)
    if dd == 0 or np.isnan(dd):
        return float("nan")
    return float(pnl.mean() / dd * np.sqrt(periods_per_year))


def equity_curve(pnl: pd.Series) -> pd.Series:
    """Cumulative P&L (EUR per unit notional)."""
    return pnl.cumsum()


def max_drawdown(pnl: pd.Series) -> float:
    """Largest peak-to-trough drop of the cumulative equity curve (EUR)."""
    equity = pnl.cumsum()
    running_max = equity.cummax()
    drawdown = equity - running_max
    return float(drawdown.min())


def calmar_ratio(pnl: pd.Series, periods_per_year: int = 365) -> float:
    """Annualized P&L divided by the max drawdown magnitude."""
    mdd = max_drawdown(pnl)
    if mdd == 0:
        return float("nan")
    return float(annualized_pnl(pnl, periods_per_year) / abs(mdd))


def hit_rate(pnl: pd.Series) -> float:
    """Share of active (non-zero P&L) days that are winners."""
    active = pnl[pnl != 0]
    if len(active) == 0:
        return float("nan")
    return float((active > 0).mean())


def avg_turnover(positions: pd.DataFrame) -> float:
    """Mean daily turnover = mean |change in position| summed over instruments."""
    return float(positions.diff().abs().sum(axis=1).mean())


def summarize(
    pnl: pd.Series,
    positions: pd.DataFrame | None = None,
    periods_per_year: int = 365,
    label: str = "",
) -> dict:
    """Bundle the headline metrics into one dict."""
    out = {
        "label": label,
        "days": int(len(pnl)),
        "total_pnl_eur": float(pnl.sum()),
        "annualized_pnl_eur": annualized_pnl(pnl, periods_per_year),
        "sharpe": sharpe_ratio(pnl, periods_per_year),
        "sortino": sortino_ratio(pnl, periods_per_year),
        "max_drawdown_eur": max_drawdown(pnl),
        "calmar": calmar_ratio(pnl, periods_per_year),
        "hit_rate": hit_rate(pnl),
    }
    if positions is not None:
        out["avg_daily_turnover"] = avg_turnover(positions)
    return out
