"""Charts for the analysis and README. Each function saves one figure.

Styling goes through seaborn so every chart shares one palette and grid. Blue
marks the main series and long positions, red marks losses and thresholds,
green marks the z-score and the out-of-sample region.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

sns.set_theme(style="whitegrid", context="notebook")

_BLUE = "#4C72B0"
_RED = "#C44E52"
_GREEN = "#55A868"
_SLATE = "#4C4C4C"

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _save(fig, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_equity_curve(pnl: pd.Series, split_date, out_path, title: str) -> Path:
    """Cumulative P&L with the out-of-sample region shaded."""
    equity = pnl.cumsum()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(equity.index, equity.values, color=_BLUE, lw=1.6)
    ax.axvspan(split_date, equity.index[-1], color=_GREEN, alpha=0.07,
               label="out-of-sample")
    ax.axvline(split_date, color=_GREEN, ls="--", lw=1.0)
    ax.axhline(0, color="k", lw=0.6, alpha=0.5)
    ax.set_ylabel("Cumulative P&L (EUR / MWh notional)")
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=9)
    return _save(fig, out_path)


def plot_drawdown(pnl: pd.Series, out_path, title: str = "Underwater (drawdown) curve") -> Path:
    equity = pnl.cumsum()
    dd = equity - equity.cummax()
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.fill_between(dd.index, dd.values, 0, color=_RED, alpha=0.4)
    ax.set_ylabel("Drawdown (EUR)")
    ax.set_title(title)
    return _save(fig, out_path)


def plot_per_instrument_sharpe(per_instrument: pd.DataFrame, out_path,
                               title: str = "Out-of-sample Sharpe by instrument") -> Path:
    s = per_instrument["sharpe"].sort_values()
    colors = [_RED if v < 0 else _BLUE for v in s.values]
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(s) + 1.5))
    ax.barh(s.index, s.values, color=colors)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("Annualized Sharpe")
    ax.set_title(title)
    return _save(fig, out_path)


def plot_cost_sensitivity(costs, sharpes, out_path,
                          title: str = "Robustness: Sharpe vs. transaction cost") -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(costs, sharpes, "o-", color=_BLUE)
    ax.axhline(0, color=_RED, ls="--", lw=1.0)
    ax.set_xlabel("Transaction cost + slippage (EUR/MWh per unit turnover)")
    ax.set_ylabel("Out-of-sample Sharpe")
    ax.set_title(title)
    return _save(fig, out_path)


def plot_lag_decay(lags, sharpes, out_path,
                   title: str = "Signal decay: Sharpe vs. execution lag (days)") -> Path:
    """A genuine 1-day mean-reversion decays as you delay execution; a lookahead
    artifact would not. This chart is the no-lookahead evidence."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(lags, sharpes, "o-", color=_BLUE)
    ax.axhline(0, color=_RED, ls="--", lw=1.0)
    ax.set_xlabel("Days between signal and execution")
    ax.set_ylabel("Gross Sharpe (full sample)")
    ax.set_xticks(list(lags))
    ax.set_title(title)
    return _save(fig, out_path)


def plot_param_heatmap(grid: pd.DataFrame, out_path,
                       title: str = "Robustness: in-sample Sharpe across parameters") -> Path:
    """Heatmap of Sharpe over (lookback, entry_z). A broad plateau of positive
    values means the edge is not a single cherry-picked parameter combo."""
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(grid.values, aspect="auto", origin="lower", cmap="RdBu_r",
                   vmin=-abs(grid.values).max(), vmax=abs(grid.values).max())
    ax.set_xticks(range(len(grid.columns)))
    ax.set_xticklabels(grid.columns)
    ax.set_yticks(range(len(grid.index)))
    ax.set_yticklabels(grid.index)
    ax.set_xlabel("entry z-score")
    ax.set_ylabel("lookback (days)")
    for i in range(len(grid.index)):
        for j in range(len(grid.columns)):
            ax.text(j, i, f"{grid.values[i, j]:.1f}", ha="center", va="center",
                    fontsize=8, color="black")
    fig.colorbar(im, ax=ax, label="in-sample Sharpe")
    ax.set_title(title)
    ax.grid(False)
    return _save(fig, out_path)


def plot_signal_example(levels: pd.DataFrame, positions: pd.DataFrame,
                        z: pd.DataFrame, instrument: str, out_path,
                        window: tuple | None = None) -> Path:
    """Price level, z-score band and position for one instrument over a window."""
    lv, ps, zz = levels[instrument], positions[instrument], z[instrument]
    if window:
        lv, ps, zz = lv.loc[window[0]:window[1]], ps.loc[window[0]:window[1]], zz.loc[window[0]:window[1]]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(lv.index, lv.values, color=_SLATE, lw=1.3, label=f"{instrument} level")
    ax1.set_ylabel("EUR/MWh")
    ax1.set_title(f"Mean-reversion signal on {instrument}")
    ax1b = ax1.twinx()
    ax1b.fill_between(ps.index, ps.values, 0, step="post", color=_BLUE, alpha=0.2)
    ax1b.plot(ps.index, ps.values, drawstyle="steps-post", color=_BLUE, lw=1.0,
              label="position")
    ax1b.set_ylabel("position", color=_BLUE)
    ax1b.grid(False)

    ax2.plot(zz.index, zz.values, color=_GREEN, lw=1.0)
    ax2.axhline(0, color="k", lw=0.6)
    for lvl in (-1, 1):
        ax2.axhline(lvl * 1.5, color=_RED, ls="--", lw=0.8, alpha=0.7)
    ax2.set_ylabel("z-score")
    fig.autofmt_xdate()
    return _save(fig, out_path)
