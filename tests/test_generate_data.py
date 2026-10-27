"""The dataset has to be reproducible and schema-clean, or every other number
in the project is unverifiable."""

from __future__ import annotations

import pandas as pd

from src import generate_data
from src.config import MONTHS, N_EXCEPTIONS, REQUIRED_COLUMNS
from src.loader import coerce, validate


def test_same_seed_gives_the_same_dataset():
    assert generate_data.build_exceptions(seed=7, n=50) == generate_data.build_exceptions(seed=7, n=50)


def test_different_seeds_diverge():
    assert generate_data.build_exceptions(seed=7, n=50) != generate_data.build_exceptions(seed=8, n=50)


def test_generated_rows_pass_the_loader_schema_check():
    df = pd.DataFrame(generate_data.build_exceptions()).astype(str)
    assert validate(df) == []


def test_default_size_matches_config():
    assert len(generate_data.build_exceptions()) == N_EXCEPTIONS


def test_required_columns_are_all_present():
    row = generate_data.build_exceptions(n=1)[0]
    assert set(REQUIRED_COLUMNS).issubset(row)


def test_open_cases_have_no_resolution_date():
    rows = generate_data.build_exceptions()
    assert all(r["resolved_at"] == "" for r in rows if r["status"] != "resolved")
    assert all(r["resolved_at"] != "" for r in rows if r["status"] == "resolved")


def test_recurrence_is_actually_built_in():
    # The whole product hypothesis needs repeat clusters to exist. If this fails,
    # the generator stopped modelling the thing the app is built to find.
    from src.analytics import baseline_metrics

    df = coerce(pd.DataFrame(generate_data.build_exceptions()).astype(str))
    assert baseline_metrics(df)["repeat_share"] > 0.3


def test_bill_volume_covers_the_exception_window_with_no_partial_month():
    volume = generate_data.build_bill_volume()
    assert len(volume) == MONTHS
    rows = generate_data.build_exceptions()
    months_seen = {r["opened_at"][:7] for r in rows}
    assert months_seen.issubset({v["month"] for v in volume})
