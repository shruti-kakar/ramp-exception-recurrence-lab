"""The scenario model is arithmetic on an assumption. These tests pin the
arithmetic and, more importantly, pin the guardrails around it."""

from __future__ import annotations

import math

import pytest

from src import analytics, scenario


def test_zero_assumption_saves_nothing():
    est = scenario.project(10.0, 0)
    assert est["hours_saved_point"] == 0
    assert est["residual_hours_per_month"] == 10.0


def test_point_estimate_is_a_share_of_the_addressable_pool():
    est = scenario.project(10.0, 10)
    assert math.isclose(est["hours_saved_point"], 1.0)
    assert math.isclose(est["hours_saved_per_year"], 12.0)


def test_every_projection_carries_a_band_and_a_disclaimer():
    est = scenario.project(10.0, 20, band=0.5)
    assert est["hours_saved_low"] < est["hours_saved_point"] < est["hours_saved_high"]
    assert math.isclose(est["hours_saved_low"], 1.0)
    assert math.isclose(est["hours_saved_high"], 3.0)
    assert "Not a measured result" in est["basis"]


def test_cost_translation_uses_the_supplied_rate():
    est = scenario.project(10.0, 10, hourly_cost=50.0)
    assert math.isclose(est["cost_point"], 50.0)
    assert math.isclose(est["cost_per_year"], 600.0)


def test_assumption_outside_zero_to_one_hundred_is_rejected():
    with pytest.raises(ValueError):
        scenario.project(10.0, 120)
    with pytest.raises(ValueError):
        scenario.project(-1.0, 10)


def test_expected_value_discounts_by_fixability(frame):
    table = analytics.root_cause_table(frame)
    ev = scenario.expected_value(table, 10)
    row = ev[ev["root_cause"] == "missing_po"].iloc[0]
    assert math.isclose(row["expected_hours_per_month"], row["hours_saved_point"] * row["fixability"])
    assert row["expected_hours_per_month"] < row["hours_saved_point"]


def test_project_table_handles_an_empty_cause_table(frame):
    empty = analytics.root_cause_table(frame).iloc[0:0]
    out = scenario.project_table(empty, 10)
    assert out.empty
    assert "hours_saved_point" in out.columns


def test_pilot_sample_size_grows_as_the_effect_shrinks():
    small_effect = scenario.pilot_sample_size(24.0, 0.10)
    large_effect = scenario.pilot_sample_size(24.0, 0.40)
    assert small_effect > large_effect


def test_pilot_sample_size_is_undefined_without_a_baseline():
    assert scenario.pilot_sample_size(0.0) is None
    assert scenario.pilot_sample_size(24.0, 0.0) is None
