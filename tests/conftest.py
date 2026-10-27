"""Fixtures shared by the test suite.

Tests run on a small hand-written frame rather than the generated dataset
wherever the expected answer needs to be obvious by inspection.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.loader import coerce

ROWS = [
    # Northwind hits missing_po three times: one first occurrence, two repeats.
    ("INV-1", "Northwind", "1000", "invoice_data_incomplete", "resolved",
     "2026-04-01T09:00:00", "2026-04-02T09:00:00", "missing_po", "A", "30", "false", "n1"),
    ("INV-2", "Northwind", "1000", "invoice_data_incomplete", "resolved",
     "2026-04-10T09:00:00", "2026-04-12T09:00:00", "missing_po", "A", "60", "true", "n2"),
    ("INV-3", "Northwind", "1000", "invoice_data_incomplete", "open",
     "2026-05-01T09:00:00", "", "missing_po", "B", "30", "false", "n3"),
    # Atlas hits missing_po twice: one first, one repeat.
    ("INV-4", "Atlas", "500", "invoice_data_incomplete", "resolved",
     "2026-04-05T09:00:00", "2026-04-06T09:00:00", "missing_po", "B", "20", "false", "n4"),
    ("INV-5", "Atlas", "500", "invoice_data_incomplete", "resolved",
     "2026-05-05T09:00:00", "2026-05-06T09:00:00", "missing_po", "B", "40", "false", "n5"),
    # A single one-off: no repeat, so nothing addressable.
    ("INV-6", "Solo", "250", "coding_review", "resolved",
     "2026-05-20T09:00:00", "2026-05-21T09:00:00", "gl_coding", "A", "10", "false", "n6"),
]

COLUMNS = (
    "invoice_id", "vendor", "amount", "exception_type", "status", "opened_at",
    "resolved_at", "root_cause", "owner", "minutes_spent", "reopened", "reviewer_note",
)


@pytest.fixture
def raw_frame() -> pd.DataFrame:
    return pd.DataFrame(ROWS, columns=list(COLUMNS)).astype(str)


@pytest.fixture
def frame(raw_frame: pd.DataFrame) -> pd.DataFrame:
    return coerce(raw_frame)


@pytest.fixture
def volume() -> pd.DataFrame:
    return pd.DataFrame(
        {"month": ["2026-04", "2026-05"], "bills_processed": [1000.0, 1000.0]}
    )
