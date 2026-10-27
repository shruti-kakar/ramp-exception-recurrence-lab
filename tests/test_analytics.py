"""The recurrence logic is the product argument, so it is tested on a frame
whose right answers can be counted by hand."""

from __future__ import annotations

import math

from src import analytics


def test_occurrence_index_counts_within_vendor_and_cause(frame):
    d = analytics.add_derived(frame)
    northwind = d[d["vendor"] == "Northwind"].sort_values("opened_at")
    assert list(northwind["occurrence"]) == [1, 2, 3]
    assert list(northwind["is_repeat"]) == [False, True, True]


def test_first_occurrence_is_never_addressable(frame):
    d = analytics.add_derived(frame)
    assert (d.loc[d["occurrence"] == 1, "is_repeat"] == False).all()  # noqa: E712


def test_one_off_cluster_contributes_no_repeats(frame):
    d = analytics.add_derived(frame)
    solo = d[d["vendor"] == "Solo"]
    assert solo["cluster_size"].iloc[0] == 1
    assert not solo["is_repeat"].any()


def test_repeat_hours_exclude_first_occurrences(frame):
    # Repeats are INV-2 (60), INV-3 (30), INV-5 (40) = 130 minutes.
    m = analytics.baseline_metrics(frame)
    assert m["repeat_exceptions"] == 3
    assert math.isclose(m["repeat_reviewer_hours"], 130 / 60)
    assert math.isclose(m["reviewer_hours"], 190 / 60)


def test_rates_need_a_denominator(frame, volume):
    without = analytics.baseline_metrics(frame)
    assert without["exceptions_per_1000_bills"] is None

    with_vol = analytics.baseline_metrics(frame, volume)
    assert math.isclose(with_vol["exceptions_per_1000_bills"], 6 / 2000 * 1000)
    assert math.isclose(with_vol["repeats_per_1000_bills"], 3 / 2000 * 1000)


def test_reopen_rate_uses_resolved_cases_only(frame):
    # Five rows are resolved, one of them reopened.
    m = analytics.baseline_metrics(frame)
    assert math.isclose(m["reopen_rate"], 1 / 5)


def test_concentration_is_one_when_few_vendors_hold_the_repeats(frame):
    d = analytics.add_derived(frame)
    po = d[d["root_cause"] == "missing_po"]
    # Two vendors hold all missing_po repeats, fewer than the top-3 cutoff.
    assert math.isclose(analytics.concentration(po), 1.0)


def test_concentration_is_zero_without_repeats(frame):
    d = analytics.add_derived(frame)
    coding = d[d["root_cause"] == "gl_coding"]
    assert analytics.concentration(coding) == 0.0


def test_prevention_index_is_the_product_of_its_three_factors(frame):
    table = analytics.root_cause_table(frame)
    row = table[table["root_cause"] == "missing_po"].iloc[0]
    expected = row["repeat_hours_per_month"] * row["concentration"] * row["fixability"]
    assert math.isclose(row["prevention_index"], expected)


def test_cause_with_no_repeats_scores_zero(frame):
    table = analytics.root_cause_table(frame)
    row = table[table["root_cause"] == "gl_coding"].iloc[0]
    assert row["prevention_index"] == 0.0
    assert row["rank"] == 2  # ranks below missing_po despite being a real exception


def test_volume_ranking_is_kept_for_contrast(frame):
    table = analytics.root_cause_table(frame)
    assert set(["rank", "rank_by_volume"]).issubset(table.columns)


def test_cluster_table_excludes_single_occurrences(frame):
    clusters = analytics.cluster_table(frame)
    assert set(clusters["vendor"]) == {"Northwind", "Atlas"}
    northwind = clusters[clusters["vendor"] == "Northwind"].iloc[0]
    assert northwind["occurrences"] == 3
    assert math.isclose(northwind["repeat_hours"], 90 / 60)
    assert northwind["still_open"] == 1


def test_cluster_table_returns_shaped_frame_when_nothing_recurs(frame):
    solo = frame[frame["vendor"] == "Solo"]
    out = analytics.cluster_table(solo)
    assert out.empty
    assert "repeat_hours" in out.columns


def test_monthly_trend_splits_repeats_and_adds_rates(frame, volume):
    trend = analytics.monthly_trend(frame, volume)
    assert list(trend["month"]) == ["2026-04", "2026-05"]
    assert list(trend["exceptions"]) == [3, 3]
    assert list(trend["repeat_exceptions"]) == [1, 2]
    assert "repeats_per_1000_bills" in trend.columns


def test_first_vs_repeat_splits_all_effort(frame):
    split = analytics.first_vs_repeat(frame)
    assert set(split["bucket"]) == {"first occurrence", "repeat occurrence"}
    assert math.isclose(split["reviewer_hours"].sum(), 190 / 60)


def test_months_covered_never_divides_by_zero(frame):
    d = analytics.add_derived(frame)
    assert analytics.months_covered(d.iloc[0:0]) == 1
