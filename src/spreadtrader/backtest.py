"""The backtest engine.

Turns positions into P&L honestly:

    gross_pnl[t] = position[t-1] * (level[t] - level[t-1])      # earn the move
    cost[t]      = |position[t] - position[t-1]| * cost_per_unit # pay on turnover
    net_pnl[t]   = gross_pnl[t] - cost[t]

The one-day shift on the position guarantees no lookahead: only yesterday's
position (decided from information available yesterday) earns today's move. The
portfolio equal-weights the instruments. An in-sample / out-of-sample split is
carried through so the headline numbers can be reported on unseen data.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from spreadtrader.config import StrategyConfig
from spreadtrader.metrics import summarize
from spreadtrader.signals import build_instruments, mean_reversion_positions


@dataclass
class BacktestResult:
    cfg: StrategyConfig
    levels: pd.DataFrame
    positions: pd.DataFrame
    gross_pnl: pd.DataFrame
    cost: pd.DataFrame
    net_pnl: pd.DataFrame          # per-instrument net P&L
    portfolio_pnl: pd.Series       # equal-weight across instruments

    # -- splitting ------------------------------------------------------- #
    def split_date(self) -> pd.Timestamp:
        idx = self.portfolio_pnl.index
        return idx[int(len(idx) * self.cfg.oos_split_frac)]

    def in_sample(self) -> pd.Series:
        return self.portfolio_pnl.loc[: self.split_date()].iloc[:-1]

    def out_of_sample(self) -> pd.Series:
        return self.portfolio_pnl.loc[self.split_date():]

    # -- reporting ------------------------------------------------------- #
    def summary(self) -> dict[str, dict]:
        ppy = self.cfg.trading_days_per_year
        return {
            "full": summarize(self.portfolio_pnl, self.positions, ppy, "full"),
            "in_sample": summarize(self.in_sample(), None, ppy, "in_sample"),
            "out_of_sample": summarize(self.out_of_sample(), None, ppy, "out_of_sample"),
        }

    def per_instrument_summary(self) -> pd.DataFrame:
        ppy = self.cfg.trading_days_per_year
        rows = [
            summarize(self.net_pnl[col].dropna(),
                      self.positions[[col]], ppy, col)
            for col in self.net_pnl.columns
        ]
        return pd.DataFrame(rows).set_index("label")


def run_backtest(levels: pd.DataFrame, cfg: StrategyConfig) -> BacktestResult:
    """Run the mean-reversion backtest on a table of instrument level series."""
    positions = mean_reversion_positions(levels, cfg)

    level_change = levels.diff()
    gross = positions.shift(1) * level_change            # no lookahead
    turnover = positions.diff().abs()
    cost = turnover * cfg.cost_per_unit_turnover
    net = gross - cost

    # Equal-weight portfolio; drop the warmup rows with no complete signal.
    portfolio = net.mean(axis=1).dropna()

    return BacktestResult(
        cfg=cfg,
        levels=levels,
        positions=positions,
        gross_pnl=gross,
        cost=cost,
        net_pnl=net,
        portfolio_pnl=portfolio,
    )


def run_from_daily(daily: pd.DataFrame, cfg: StrategyConfig) -> BacktestResult:
    """Convenience: build instruments from daily prices, then backtest."""
    levels = build_instruments(daily, cfg)
    return run_backtest(levels, cfg)
