"""power-spread-trader: a cross-border day-ahead spread mean-reversion backtest.

An honest backtesting framework for a defensible statistical-arbitrage strategy
on European power prices. It trades the mean reversion of cross-border
day-ahead spreads (and the German price level), and reports risk-adjusted
performance -- Sharpe, Sortino, drawdown, turnover -- with transaction costs,
slippage and a strict out-of-sample split baked in from the start.
"""

from spreadtrader.config import StrategyConfig, load_config

__all__ = ["StrategyConfig", "load_config"]
__version__ = "0.1.0"
