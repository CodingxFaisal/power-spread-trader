"""Tests for signal construction, the z-score and the hysteresis rule."""

import numpy as np
import pandas as pd

from spreadtrader.signals import (
    _positions_from_z,
    build_instruments,
    mean_reversion_positions,
    zscore,
)


def test_build_instruments_spreads_and_outright(cfg, mean_reverting_daily):
    inst = build_instruments(mean_reverting_daily, cfg)
    assert cfg.reference_zone in inst.columns          # outright present
    assert f"{cfg.reference_zone}-FR" in inst.columns  # a spread present
    # Spread equals the difference of the two zone prices.
    expected = mean_reverting_daily["DE_LU"] - mean_reverting_daily["FR"]
    pd.testing.assert_series_equal(
        inst["DE_LU-FR"], expected, check_names=False)


def test_zscore_is_standardized():
    # Constant-slope ramp: rolling z-score should be finite and, on a symmetric
    # window, have the right sign relative to the trailing mean.
    s = pd.DataFrame({"x": np.arange(100, dtype=float)})
    z = zscore(s, 10)["x"].dropna()
    assert np.isfinite(z).all()
    assert (z > 0).all()  # a rising series sits above its trailing mean


def test_hysteresis_state_machine():
    # z crosses +entry (go short), drifts in the dead band (hold), returns
    # inside exit (go flat), then crosses -entry (go long).
    z = pd.Series([0.0, 2.0, 1.0, 0.2, -2.0, -1.0, 0.1])
    pos = _positions_from_z(z, entry=1.5, exit_=0.5, cap=1.0)
    assert list(pos) == [0.0, -1.0, -1.0, 0.0, 1.0, 1.0, 0.0]


def test_positions_only_use_past(cfg, mean_reverting_daily):
    # Truncating the future must not change past positions (no lookahead).
    inst = build_instruments(mean_reverting_daily, cfg)
    full = mean_reversion_positions(inst, cfg)
    cut = mean_reversion_positions(inst.iloc[:400], cfg)
    pd.testing.assert_frame_equal(full.iloc[:400], cut, check_freq=False)
