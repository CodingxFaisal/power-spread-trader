"""Tests for configuration loading and validation."""

from dataclasses import replace

import pytest


def test_instrument_names(cfg):
    names = cfg.instrument_names()
    assert names[0] == cfg.reference_zone            # outright first
    assert f"{cfg.reference_zone}-FR" in names
    assert len(names) == len(cfg.zones)              # outright + (n-1) spreads


def test_cost_per_unit_turnover(cfg):
    assert cfg.cost_per_unit_turnover == pytest.approx(
        cfg.transaction_cost_eur_per_mwh + cfg.slippage_eur_per_mwh)


def test_entry_must_exceed_exit(cfg):
    with pytest.raises(ValueError):
        replace(cfg, entry_z=0.5, exit_z=1.0)


def test_reference_zone_must_be_in_zones(cfg):
    with pytest.raises(ValueError):
        replace(cfg, reference_zone="ES")


def test_oos_split_bounds(cfg):
    with pytest.raises(ValueError):
        replace(cfg, oos_split_frac=1.5)
