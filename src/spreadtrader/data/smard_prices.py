"""SMARD.de day-ahead price client for multiple bidding zones.

Fetches hourly day-ahead wholesale prices (EUR/MWh) for Germany and its
neighbours from the free SMARD chart-data API (no key, no registration), with
on-disk CSV caching. See the sibling ``zones.py`` for the validated series IDs.

Data model mirrors SMARD's: hourly points in weekly JSON chunks, UTC epoch-ms
timestamps parsed to Europe/Berlin so DST-length days come out right.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://www.smard.de/app/chart_data"
_WEEK_MS = 7 * 24 * 3600 * 1000
TZ = "Europe/Berlin"

# Validated SMARD day-ahead price filter IDs (DE region files cover all zones).
# Confirmed against SMARD's price module; magnitudes sanity-checked (EUR/MWh).
ZONE_IDS = {
    "DE_LU": 4169,   # Germany / Luxembourg
    "FR": 253,       # France
    "NL": 254,       # Netherlands
    "BE": 4996,      # Belgium
    "AT": 255,       # Austria
    "CH": 257,       # Switzerland
    "DK1": 4170,     # Denmark 1 (west)
    "PL": 256,       # Poland
    "CZ": 259,       # Czech Republic
    "NO2": 4997,     # Norway 2
}


def _cache_path(cache_dir: Path, zone: str) -> Path:
    return cache_dir / f"da_price_{zone}.csv"


def _load_cache(path: Path) -> pd.Series:
    if not path.exists():
        return pd.Series(dtype="float64")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    s = df.set_index("timestamp")["price"]
    s.index = pd.to_datetime(s.index, utc=True).tz_convert(TZ)
    return s


def _save_cache(path: Path, series: pd.Series) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = series.sort_index()
    out.index.name = "timestamp"
    out.rename("price").to_csv(path)


def fetch_zone(
    zone: str,
    start: str,
    end: str,
    cache_dir: str | Path = "data/raw",
    session: requests.Session | None = None,
    pause_s: float = 0.03,
) -> pd.Series:
    """Fetch one zone's hourly day-ahead price over ``[start, end)``."""
    if zone not in ZONE_IDS:
        raise KeyError(f"unknown zone {zone!r}; known: {sorted(ZONE_IDS)}")
    series_id = ZONE_IDS[zone]
    cache_dir = Path(cache_dir)

    start_ts = pd.Timestamp(start, tz=TZ)
    end_ts = pd.Timestamp(end, tz=TZ)
    start_ms = int(start_ts.tz_convert("UTC").timestamp() * 1000)
    end_ms = int(end_ts.tz_convert("UTC").timestamp() * 1000)

    path = _cache_path(cache_dir, zone)
    cached = _load_cache(path)
    have_ms = set()
    if not cached.empty:
        have_ms = set(cached.index.tz_convert("UTC").astype("int64") // 1_000_000)

    own = session is None
    session = session or requests.Session()
    try:
        index = session.get(f"{BASE_URL}/{series_id}/DE/index_hour.json", timeout=30).json()
        weeks = [t for t in index["timestamps"] if (t + _WEEK_MS) > start_ms and t < end_ms]

        new = []
        for ts in weeks:
            hours = set(range(ts, ts + _WEEK_MS, 3600 * 1000))
            if hours.issubset(have_ms):
                continue
            payload = session.get(
                f"{BASE_URL}/{series_id}/DE/{series_id}_DE_hour_{ts}.json", timeout=30
            ).json()
            rows = [(t, v) for t, v in payload["series"] if v is not None]
            if rows:
                idx = pd.to_datetime([r[0] for r in rows], unit="ms", utc=True)
                new.append(pd.Series([r[1] for r in rows], index=idx))
            if pause_s:
                time.sleep(pause_s)

        if new:
            fetched = pd.concat(new)
            fetched.index = fetched.index.tz_convert(TZ)
            combined = pd.concat([cached, fetched])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            _save_cache(path, combined)
        else:
            combined = cached
    finally:
        if own:
            session.close()

    out = combined[(combined.index >= start_ts) & (combined.index < end_ts)]
    return out.sort_index().rename(zone)


def fetch_prices(
    zones: list[str],
    start: str,
    end: str,
    cache_dir: str | Path = "data/raw",
    pause_s: float = 0.03,
) -> pd.DataFrame:
    """Fetch hourly day-ahead prices for several zones into one DataFrame."""
    session = requests.Session()
    try:
        cols = {
            z: fetch_zone(z, start, end, cache_dir=cache_dir,
                          session=session, pause_s=pause_s)
            for z in zones
        }
    finally:
        session.close()
    df = pd.DataFrame(cols)
    df.index.name = "timestamp"
    return df


def to_daily_baseload(hourly: pd.DataFrame) -> pd.DataFrame:
    """Resample hourly prices to daily baseload (24h mean) per zone.

    Days with fewer than 20 valid hours (data gaps, clock changes edge cases)
    are dropped so the series stays comparable across zones.
    """
    grouped = hourly.groupby(hourly.index.normalize())
    daily = grouped.mean()
    counts = grouped.count().min(axis=1)
    daily = daily[counts >= 20]
    daily.index = daily.index.tz_localize(None)  # calendar dates, tz-naive
    daily.index.name = "date"
    return daily
