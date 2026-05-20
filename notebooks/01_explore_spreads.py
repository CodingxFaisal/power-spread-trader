# ---
# Exploratory script for inspecting the spreads. Open as a notebook (the `# %%`
# markers are cells) or run directly:  python notebooks/01_explore_spreads.py
# It looks at the cross-border spreads the strategy trades: their level, their
# mean-reverting behaviour, and the one-day negative autocorrelation that the
# signal exploits.
# ---

# %% imports + path bootstrap
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib.pyplot as plt

from spreadtrader.config import load_config
from spreadtrader.data import fetch_prices, to_daily_baseload

ROOT = Path(__file__).resolve().parents[1]
cfg = load_config(ROOT / "config" / "strategy.yaml")

# %% load daily baseload prices (cached after first download)
hourly = fetch_prices(cfg.zones, cfg.start, cfg.end, cache_dir=ROOT / "data" / "raw")
daily = to_daily_baseload(hourly)
print(daily.describe().round(1))

# %% cross-border spreads over time
spreads = daily[["FR", "NL", "AT"]].rsub(daily["DE_LU"], axis=0)
spreads.columns = ["DE-FR", "DE-NL", "DE-AT"]
ax = spreads.plot(alpha=0.7)
ax.axhline(0, color="k", lw=0.8)
ax.set(ylabel="EUR/MWh", title="Cross-border day-ahead spreads (daily baseload)")
plt.show()

# %% the mean reversion: one-day autocorrelation of spread *changes* is negative
changes = spreads.diff().dropna()
print("lag-1 autocorrelation of daily spread changes (negative = mean reverting):")
for c in changes.columns:
    print(f"  {c}: {changes[c].autocorr(1):+.2f}")

# %% distribution of a spread and its rolling z-score
de_at = (daily["DE_LU"] - daily["AT"])
z = (de_at - de_at.rolling(20).mean()) / de_at.rolling(20).std()
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4))
de_at.plot(ax=a, title="DE-AT spread")
a.axhline(0, color="k", lw=0.8)
z.plot(ax=b, title="DE-AT spread z-score (20d)")
for lvl in (-1.5, 1.5):
    b.axhline(lvl, color="r", ls="--", lw=0.8)
plt.show()
