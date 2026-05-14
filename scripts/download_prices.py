"""Download and cache SMARD day-ahead prices for the configured zones.

    python scripts/download_prices.py

Caches per-zone hourly prices under data/raw and the assembled daily-baseload
table under data/processed, so re-runs and the backtest hit the network once.
"""

from __future__ import annotations

from _common import CONFIG, load_config, load_or_build_daily


def main() -> None:
    cfg = load_config(CONFIG)
    print(f"Downloading day-ahead prices {cfg.start} -> {cfg.end} for {cfg.zones} ...")
    daily = load_or_build_daily(cfg.zones, cfg.start, cfg.end)
    print(f"Daily rows: {len(daily):,}  ({daily.index.min().date()} -> {daily.index.max().date()})")
    print("\nMean daily baseload price by zone (EUR/MWh):")
    print(daily.mean().round(1).to_string())
    print("\nMean DE_LU spreads (EUR/MWh):")
    for z in cfg.zones:
        if z != cfg.reference_zone:
            spread = (daily[cfg.reference_zone] - daily[z])
            print(f"  {cfg.reference_zone}-{z:5s}  mean {spread.mean():6.2f}  std {spread.std():6.2f}")


if __name__ == "__main__":
    main()
