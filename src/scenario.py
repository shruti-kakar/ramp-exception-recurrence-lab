"""Counterfactual scenario model.

This module answers one question: if a prevention change removed some share of
*repeat* exceptions for a cause, how much reviewer effort would stop happening?

It is arithmetic on an assumption, not a measurement, and the API is shaped to
make that hard to forget: every projection returns a low/point/high band and the
assumption that produced it, so nothing can be quoted as an observed result.
"""

from __future__ import annotations

import pandas as pd

from src.config import (
    DEFAULT_REVIEWER_HOURLY_COST,
    HOURS_PER_FTE_MONTH,
    SENSITIVITY_BAND,
)

DISCLAIMER = (
    "Projection from a user-set assumption on synthetic data. "
    "Not a measured result and not a Ramp performance claim."
)


def project(
    repeat_hours_per_month: float,
    reduction_pct: float,
    hourly_cost: float = DEFAULT_REVIEWER_HOURLY_COST,
    band: float = SENSITIVITY_BAND,
) -> dict:
    """Translate one prevention assumption into a banded effort estimate.

    Args:
        repeat_hours_per_month: addressable pool, repeat occurrences only.
        reduction_pct: assumed share of that pool removed, 0-100.
        hourly_cost: loaded cost of a reviewer hour, for the currency view.
        band: fractional width of the sensitivity band around the point estimate.

    Only repeat hours are ever reduced. First occurrences stay in the baseline
    because no feedback loop can prevent a problem's first appearance.
    """
    if repeat_hours_per_month < 0:
        raise ValueError("repeat_hours_per_month cannot be negative")
    if not 0 <= reduction_pct <= 100:
        raise ValueError("reduction_pct must be between 0 and 100")

    fraction = reduction_pct / 100.0
    point = repeat_hours_per_month * fraction
    low = point * (1 - band)
    high = point * (1 + band)

    return {
        "assumption_pct": reduction_pct,
        "addressable_hours_per_month": repeat_hours_per_month,
        "hours_saved_point": point,
        "hours_saved_low": low,
        "hours_saved_high": high,
        "hours_saved_per_year": point * 12,
        "cost_point": point * hourly_cost,
        "cost_per_year": point * 12 * hourly_cost,
        "fte_equivalent": point / HOURS_PER_FTE_MONTH if HOURS_PER_FTE_MONTH else 0.0,
        "residual_hours_per_month": repeat_hours_per_month - point,
        "basis": DISCLAIMER,
    }


def project_table(
    cause_table: pd.DataFrame,
    reduction_pct: float,
    hourly_cost: float = DEFAULT_REVIEWER_HOURLY_COST,
    band: float = SENSITIVITY_BAND,
) -> pd.DataFrame:
    """Apply one reduction assumption across every root cause.

    Expects the output of `analytics.root_cause_table`.
    """
    if cause_table.empty:
        return pd.DataFrame(
            columns=[
                "root_cause", "addressable_hours_per_month", "hours_saved_point",
                "hours_saved_low", "hours_saved_high", "cost_per_year", "fte_equivalent",
            ]
        )
    rows = []
    for _, row in cause_table.iterrows():
        est = project(float(row["repeat_hours_per_month"]), reduction_pct, hourly_cost, band)
        rows.append({"root_cause": row["root_cause"], **est})
    return pd.DataFrame(rows).sort_values("hours_saved_point", ascending=False).reset_index(drop=True)


def expected_value(
    cause_table: pd.DataFrame,
    reduction_pct: float,
    hourly_cost: float = DEFAULT_REVIEWER_HOURLY_COST,
) -> pd.DataFrame:
    """Discount each projection by the cause's fixability prior.

    A raw projection assumes the chosen reduction is equally achievable
    everywhere. Weighting by fixability is the honest version: the same 10%
    assumption is worth less on duplicate detection than on a required field.
    """
    table = project_table(cause_table, reduction_pct, hourly_cost)
    fix = cause_table.set_index("root_cause")["fixability"]
    table["fixability"] = table["root_cause"].map(fix).fillna(0.5)
    table["expected_hours_per_month"] = table["hours_saved_point"] * table["fixability"]
    table["expected_cost_per_year"] = table["expected_hours_per_month"] * 12 * hourly_cost
    return table.sort_values("expected_hours_per_month", ascending=False).reset_index(drop=True)


def pilot_sample_size(
    baseline_rate_per_1000: float, detectable_relative_change: float = 0.20
) -> int | None:
    """Bills per arm needed to see a relative change in the recurrence rate.

    Two-proportion z-test approximation at 80% power and alpha 0.05, which is
    the standard the 30-day experiment in the PRD should be held to. The point of
    surfacing it is that it is often the number that kills a tidy-looking pilot.
    """
    if baseline_rate_per_1000 <= 0 or not 0 < detectable_relative_change < 1:
        return None
    p1 = baseline_rate_per_1000 / 1000.0
    p2 = p1 * (1 - detectable_relative_change)
    p_bar = (p1 + p2) / 2
    delta = p1 - p2
    if delta <= 0:
        return None
    # (z_a/2 + z_b)^2 = (1.96 + 0.84)^2 = 7.849
    n = 7.849 * 2 * p_bar * (1 - p_bar) / (delta**2)
    return int(round(n))
