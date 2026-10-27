"""CSV ingestion with explicit schema checks.

The loader is strict on purpose. In exception work the most expensive failure is
an analysis that silently ran on a malformed file, so a bad column or an
unparseable date stops the load rather than producing a plausible-looking chart.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import (
    BILL_VOLUME_CSV,
    DATE_COLUMNS,
    EXCEPTIONS_CSV,
    NUMERIC_COLUMNS,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    STATUSES,
)


def _is_blank(series: pd.Series) -> pd.Series:
    """True where a cell carries no value, however the CSV round trip spelled it.

    pandas writes an empty cell back as an empty string and reads it as NaN, so a
    blank check that only looks for "" reports phantom parse errors.
    """
    text = series.astype(str).str.strip().str.lower()
    return series.isna() | text.isin({"", "nan", "nat", "none", "null"})


class SchemaError(ValueError):
    """Raised when an uploaded or on-disk CSV does not match the PRD data model."""


def validate(df: pd.DataFrame) -> list[str]:
    """Return a list of human-readable schema problems. Empty list means clean.

    Returns problems rather than raising so the app can show every issue at once
    instead of making a reviewer fix them one upload at a time.
    """
    problems: list[str] = []

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        problems.append(f"missing required columns: {', '.join(missing)}")
        return problems  # further checks would be noise

    if df.empty:
        problems.append("file parsed but contains no rows")
        return problems

    for col in NUMERIC_COLUMNS:
        coerced = pd.to_numeric(df[col], errors="coerce")
        bad = int(coerced.isna().sum())
        if bad:
            problems.append(f"{col}: {bad} value(s) are not numeric")
        if (coerced.dropna() < 0).any():
            problems.append(f"{col}: contains negative values")

    for col in DATE_COLUMNS:
        parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
        blank = _is_blank(df[col])
        unparseable = int((parsed.isna() & ~blank).sum())
        if unparseable:
            problems.append(f"{col}: {unparseable} non-blank value(s) are not parseable dates")
        # resolved_at is legitimately blank for exceptions still in the queue;
        # opened_at never is, because an exception that was never opened is not a row.
        if col == "opened_at" and int(blank.sum()):
            problems.append(f"opened_at: {int(blank.sum())} row(s) have no open date")

    unknown_status = sorted(set(df["status"].dropna().unique()) - set(STATUSES))
    if unknown_status:
        problems.append(f"status: unexpected value(s) {', '.join(map(str, unknown_status))}")

    dupe_ids = int(df["invoice_id"].duplicated().sum())
    if dupe_ids:
        # Not fatal: a genuine duplicate-invoice exception can share an id.
        problems.append(f"invoice_id: {dupe_ids} repeated id(s) — expected only for duplicate cases")

    return problems


def coerce(df: pd.DataFrame) -> pd.DataFrame:
    """Apply types once, so no downstream module has to guess at a column's dtype."""
    out = df.copy()
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").astype("float64")
    out["minutes_spent"] = pd.to_numeric(out["minutes_spent"], errors="coerce")
    for col in DATE_COLUMNS:
        out[col] = pd.to_datetime(out[col], errors="coerce", format="mixed")
    for col in OPTIONAL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    out["reopened"] = out["reopened"].astype(str).str.strip().str.lower().isin(
        {"true", "1", "yes", "y"}
    )
    for col in ("vendor", "root_cause", "exception_type", "status", "owner"):
        out[col] = out[col].astype(str).str.strip()
    return out


def load_exceptions(path: Path | str = EXCEPTIONS_CSV, strict: bool = True) -> pd.DataFrame:
    """Read, validate and type the exception file.

    `strict=True` raises on any schema problem except the tolerated repeated-id
    warning. The app passes strict=False and renders the warnings itself.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.generate_data` to build the sample dataset."
        )
    raw = pd.read_csv(path, dtype=str)
    problems = validate(raw)
    fatal = [p for p in problems if "expected only for duplicate cases" not in p]
    if strict and fatal:
        raise SchemaError("; ".join(fatal))
    return coerce(raw)


def load_bill_volume(path: Path | str = BILL_VOLUME_CSV) -> pd.DataFrame:
    """Monthly bills processed: the denominator for the primary metric.

    Missing volume is survivable. The app falls back to raw counts and says so,
    because a rate without a denominator is worse than an honest count.
    """
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=["month", "bills_processed"])
    df = pd.read_csv(path, dtype={"month": str})
    df["bills_processed"] = pd.to_numeric(df["bills_processed"], errors="coerce")
    return df.dropna(subset=["bills_processed"])
