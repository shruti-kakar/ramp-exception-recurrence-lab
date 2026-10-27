"""The loader must fail loudly. A silent pass on a malformed file is the one
failure mode that produces a confident, wrong answer."""

from __future__ import annotations

import pandas as pd
import pytest

from src.loader import SchemaError, coerce, load_exceptions, validate


def test_clean_frame_has_no_problems(raw_frame):
    assert validate(raw_frame) == []


def test_missing_required_column_is_reported_alone(raw_frame):
    problems = validate(raw_frame.drop(columns=["root_cause"]))
    assert len(problems) == 1
    assert "root_cause" in problems[0]


def test_non_numeric_minutes_is_caught(raw_frame):
    bad = raw_frame.copy()
    bad.loc[0, "minutes_spent"] = "about half an hour"
    assert any("minutes_spent" in p and "not numeric" in p for p in validate(bad))


def test_negative_amount_is_caught(raw_frame):
    bad = raw_frame.copy()
    bad.loc[0, "amount"] = "-5"
    assert any("negative" in p for p in validate(bad))


def test_unparseable_open_date_is_caught(raw_frame):
    bad = raw_frame.copy()
    bad.loc[0, "opened_at"] = "last Tuesday"
    assert any("opened_at" in p for p in validate(bad))


def test_blank_resolved_at_is_allowed(raw_frame):
    # INV-3 is still open and has no resolution date. That must not be an error.
    assert not any("resolved_at" in p for p in validate(raw_frame))


def test_blank_resolved_at_survives_a_csv_round_trip(tmp_path, raw_frame):
    # pandas writes "" and reads NaN. A blank check that misses that reports
    # parse errors on every open exception in the file.
    path = tmp_path / "round_trip.csv"
    raw_frame.to_csv(path, index=False)
    assert validate(pd.read_csv(path, dtype=str)) == []


def test_missing_open_date_is_caught(raw_frame):
    bad = raw_frame.copy()
    bad.loc[0, "opened_at"] = ""
    assert any("no open date" in p for p in validate(bad))


def test_unknown_status_is_caught(raw_frame):
    bad = raw_frame.copy()
    bad.loc[0, "status"] = "escalated"
    assert any("escalated" in p for p in validate(bad))


def test_empty_file_is_caught(raw_frame):
    assert any("no rows" in p for p in validate(raw_frame.iloc[0:0]))


def test_coerce_applies_types(frame):
    assert frame["amount"].dtype.kind == "f"  # money is never an integer
    assert frame["minutes_spent"].dtype.kind in "if"
    assert frame["opened_at"].dtype.kind == "M"
    assert frame["reopened"].dtype == bool
    assert bool(frame.loc[1, "reopened"]) is True


def test_coerce_adds_missing_optional_columns(raw_frame):
    out = coerce(raw_frame.drop(columns=["reviewer_note"]))
    assert "reviewer_note" in out.columns


def test_missing_file_names_the_fix(tmp_path):
    with pytest.raises(FileNotFoundError, match="generate_data"):
        load_exceptions(tmp_path / "nope.csv")


def test_strict_load_raises_on_bad_schema(tmp_path, raw_frame):
    bad = raw_frame.copy()
    bad.loc[0, "status"] = "escalated"
    path = tmp_path / "bad.csv"
    bad.to_csv(path, index=False)
    with pytest.raises(SchemaError):
        load_exceptions(path, strict=True)


def test_repeated_invoice_id_is_a_warning_not_a_failure(tmp_path, raw_frame):
    # Two rows of a genuine duplicate-invoice case can share an id, so this
    # must load rather than raise.
    dupe = pd.concat([raw_frame, raw_frame.iloc[[0]]], ignore_index=True)
    path = tmp_path / "dupe.csv"
    dupe.to_csv(path, index=False)
    assert len(load_exceptions(path, strict=True)) == 7
