"""How much of the edge survives transaction costs? Find the break-even.

    python scripts/run_cost_sensitivity.py

Sweeps the round-trip friction (fees + bid-ask + slippage) and re-measures the
out-of-sample Sharpe and annualized P&L, then reports the break-even cost -- the
per-MWh friction at which the strategy stops making money. This is the honest
answer to "does your edge survive real trading costs?".
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from _common import CONFIG, RESULTS, load_config, load_or_build_daily

from spreadtrader.backtest import run_from_daily
from spreadtrader.metrics import annualized_pnl, sharpe_ratio
from spreadtrader.plots import plot_cost_sensitivity


def main() -> None:
    cfg = load_config(CONFIG)
    daily = load_or_build_daily(cfg.zones, cfg.start, cfg.end)
    RESULTS.mkdir(parents=True, exist_ok=True)

    costs = np.round(np.arange(0.0, 18.01, 1.0), 2)
    rows = []
    for c in costs:
        # Put the whole friction into transaction cost; zero the split slippage.
        cfg_c = replace(cfg, transaction_cost_eur_per_mwh=float(c),
                        slippage_eur_per_mwh=0.0)
        res = run_from_daily(daily, cfg_c)
        oos = res.out_of_sample()
        rows.append({
            "cost_eur_per_mwh": c,
            "oos_sharpe": sharpe_ratio(oos, cfg.trading_days_per_year),
            "oos_annualized_pnl_eur": annualized_pnl(oos, cfg.trading_days_per_year),
        })

    table = pd.DataFrame(rows)
    table.to_csv(RESULTS / "cost_sensitivity.csv", index=False)

    # Break-even: first cost where OOS annualized P&L turns non-positive.
    neg = table[table["oos_annualized_pnl_eur"] <= 0]
    breakeven = float(neg["cost_eur_per_mwh"].iloc[0]) if not neg.empty else float("inf")

    print("\n=== Cost sensitivity (out-of-sample) ===")
    print(table.round(2).to_string(index=False))
    be = f"{breakeven:.1f} EUR/MWh" if np.isfinite(breakeven) else ">8 EUR/MWh"
    print(f"\nBreak-even round-trip cost: ~{be}")
    print("For context, the typical daily spread move is ~8-9 EUR/MWh, so the "
          "signal is real but only a few EUR/MWh of friction separates it from "
          "worthless -- exactly why realizability, not the raw backtest, is the point.")

    plot_cost_sensitivity(table["cost_eur_per_mwh"], table["oos_sharpe"],
                          RESULTS / "cost_sensitivity.png")
    print("\nsaved: cost_sensitivity.csv, cost_sensitivity.png")


if __name__ == "__main__":
    main()
