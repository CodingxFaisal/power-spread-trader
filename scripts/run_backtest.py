"""Run the cross-border spread mean-reversion backtest and report performance.

    python scripts/run_backtest.py

Prints full / in-sample / out-of-sample metrics, writes them to results/, and
saves the equity, drawdown, per-instrument and signal-example charts. The
headline is the *out-of-sample*, net-of-cost Sharpe -- everything else is
context.
"""

from __future__ import annotations

import pandas as pd

from _common import CONFIG, RESULTS, load_config, load_or_build_daily

from spreadtrader.backtest import run_from_daily
from spreadtrader.metrics import sharpe_ratio, summarize
from spreadtrader.plots import (
    plot_drawdown,
    plot_equity_curve,
    plot_per_instrument_sharpe,
    plot_signal_example,
)
from spreadtrader.signals import build_instruments, zscore


def _fmt(m: dict) -> str:
    return (f"{m['label']:14s} days={m['days']:5d}  "
            f"Sharpe={m['sharpe']:5.2f}  Sortino={m['sortino']:5.2f}  "
            f"maxDD={m['max_drawdown_eur']:8.1f}  Calmar={m['calmar']:5.2f}  "
            f"hit={m['hit_rate']*100:4.1f}%  annPnL={m['annualized_pnl_eur']:7.1f}")


def main() -> None:
    cfg = load_config(CONFIG)
    daily = load_or_build_daily(cfg.zones, cfg.start, cfg.end)
    RESULTS.mkdir(parents=True, exist_ok=True)

    res = run_from_daily(daily, cfg)
    summ = res.summary()

    print("\n=== Portfolio performance (EUR per MWh notional) ===")
    for key in ("full", "in_sample", "out_of_sample"):
        print("  " + _fmt(summ[key]))

    # Gross (no-cost) out-of-sample Sharpe, to show what costs eat.
    gross_oos = res.gross_pnl.mean(axis=1).dropna().loc[res.split_date():]
    print(f"\n  out-of-sample Sharpe  net={summ['out_of_sample']['sharpe']:.2f}  "
          f"gross(no costs)={sharpe_ratio(gross_oos, cfg.trading_days_per_year):.2f}")

    # Per-instrument, out-of-sample only.
    split = res.split_date()
    oos_net = res.net_pnl.loc[split:]
    per_inst = pd.DataFrame([
        summarize(oos_net[c].dropna(), res.positions[[c]].loc[split:],
                  cfg.trading_days_per_year, c)
        for c in oos_net.columns
    ]).set_index("label")

    # Persist metrics.
    pd.DataFrame(summ).T.to_csv(RESULTS / "portfolio_metrics.csv")
    per_inst.to_csv(RESULTS / "per_instrument_oos_metrics.csv")

    # Charts.
    plot_equity_curve(
        res.portfolio_pnl, split, RESULTS / "equity_curve.png",
        title="Cross-border spread mean reversion: cumulative P&L",
    )
    plot_drawdown(res.portfolio_pnl.loc[split:], RESULTS / "drawdown.png",
                  title="Out-of-sample drawdown")
    plot_per_instrument_sharpe(per_inst, RESULTS / "per_instrument_sharpe.png")

    # Signal example: pick the most-traded spread over a readable 4-month window.
    levels = build_instruments(daily, cfg)
    z = zscore(levels, cfg.lookback_days)
    busiest = res.positions.diff().abs().sum().drop(
        cfg.reference_zone, errors="ignore").idxmax()
    mid = levels.index[int(len(levels) * 0.7)]
    win = (mid, mid + pd.Timedelta(days=120))
    plot_signal_example(levels, res.positions, z, busiest,
                        RESULTS / "signal_example.png", window=win)

    print("\nsaved: portfolio_metrics.csv, per_instrument_oos_metrics.csv, "
          "equity_curve.png, drawdown.png, per_instrument_sharpe.png, signal_example.png")


if __name__ == "__main__":
    main()
