"""Typed configuration for the spread-trading backtest."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class StrategyConfig:
    # data
    start: str
    end: str
    zones: list[str]
    # signal
    reference_zone: str
    include_outright: bool
    lookback_days: int
    entry_z: float
    exit_z: float
    max_position: float
    # costs
    transaction_cost_eur_per_mwh: float
    slippage_eur_per_mwh: float
    # backtest
    oos_split_frac: float
    trading_days_per_year: int = 365

    @property
    def cost_per_unit_turnover(self) -> float:
        """Total frictional cost charged per unit of |position change|."""
        return self.transaction_cost_eur_per_mwh + self.slippage_eur_per_mwh

    def instrument_names(self) -> list[str]:
        """Ordered list of tradable instruments: spreads (+ optional outright)."""
        others = [z for z in self.zones if z != self.reference_zone]
        names = [f"{self.reference_zone}-{z}" for z in others]
        if self.include_outright:
            names = [self.reference_zone] + names
        return names

    def __post_init__(self) -> None:
        if not 0.0 < self.oos_split_frac < 1.0:
            raise ValueError("oos_split_frac must be in (0, 1).")
        if self.entry_z <= self.exit_z:
            raise ValueError("entry_z must exceed exit_z (hysteresis band).")
        if self.reference_zone not in self.zones:
            raise ValueError("reference_zone must be one of zones.")
        if self.lookback_days < 2:
            raise ValueError("lookback_days must be >= 2.")


def load_config(path: str | Path = "config/strategy.yaml") -> StrategyConfig:
    with Path(path).open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    d, s, c, b = raw["data"], raw["strategy"], raw["costs"], raw["backtest"]
    return StrategyConfig(
        start=str(d["start"]),
        end=str(d["end"]),
        zones=list(d["zones"]),
        reference_zone=str(s["reference_zone"]),
        include_outright=bool(s["include_outright"]),
        lookback_days=int(s["lookback_days"]),
        entry_z=float(s["entry_z"]),
        exit_z=float(s["exit_z"]),
        max_position=float(s["max_position"]),
        transaction_cost_eur_per_mwh=float(c["transaction_cost_eur_per_mwh"]),
        slippage_eur_per_mwh=float(c["slippage_eur_per_mwh"]),
        oos_split_frac=float(b["oos_split_frac"]),
        trading_days_per_year=int(b.get("trading_days_per_year", 365)),
    )
