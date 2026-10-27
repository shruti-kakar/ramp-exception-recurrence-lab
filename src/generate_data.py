"""Generate the reproducible synthetic dataset.

Every record is invented. The generator deliberately builds in the structure the
product hypothesis depends on: a minority of vendor/cause pairs recur many
times, while most exceptions are one-offs. If the real world turns out to be
flat instead of concentrated, the prevention thesis in the PRD is wrong, and
this file is where that assumption is visible.

Stdlib only, so the dataset can be rebuilt without installing anything.

Run with: python -m src.generate_data
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta

from src.config import (
    BILL_VOLUME_CSV,
    DATA_DIR,
    EXCEPTIONS_CSV,
    MONTHS,
    N_EXCEPTIONS,
    OPTIONAL_COLUMNS,
    RANDOM_SEED,
    REQUIRED_COLUMNS,
)

# Cause mix, chosen to echo the review-effort split described in the case study.
CAUSE_WEIGHTS: dict[str, float] = {
    "missing_po": 0.29,
    "gl_coding": 0.24,
    "vendor_details": 0.19,
    "approval_routing": 0.16,
    "duplicate_invoice": 0.12,
}

# Coarse queue bucket a reviewer sees before anyone diagnoses a cause. The gap
# between this column and root_cause is the whole point of the project.
EXCEPTION_TYPE: dict[str, str] = {
    "missing_po": "invoice_data_incomplete",
    "gl_coding": "coding_review",
    "vendor_details": "vendor_record_incomplete",
    "approval_routing": "approval_stalled",
    "duplicate_invoice": "payment_risk",
}

# Hands-on reviewer minutes: (mean, stdev). Duplicates cost the most because
# someone has to prove the two bills are the same bill.
MINUTES_PROFILE: dict[str, tuple[float, float]] = {
    "missing_po": (22.0, 8.0),
    "gl_coding": (16.0, 6.0),
    "vendor_details": (28.0, 11.0),
    "approval_routing": (19.0, 9.0),
    "duplicate_invoice": (41.0, 15.0),
}

# Probability a resolved exception later reopens.
REOPEN_RATE: dict[str, float] = {
    "missing_po": 0.08,
    "gl_coding": 0.11,
    "vendor_details": 0.14,
    "approval_routing": 0.22,
    "duplicate_invoice": 0.06,
}

REVIEWER_NOTES: dict[str, tuple[str, ...]] = {
    "missing_po": (
        "No PO on the invoice, emailed requester for the number",
        "PO exists in the system but was never referenced on submission",
        "Requester submitted before raising the PO",
    ),
    "gl_coding": (
        "Coded to marketing, should sit in software subscriptions",
        "Department left blank, guessed from last month's bill",
        "Split coding redone after controller review",
    ),
    "vendor_details": (
        "Bank details missing, chased vendor twice",
        "W-9 on file is out of date",
        "Remittance email bounced, vendor record stale",
    ),
    "approval_routing": (
        "Routed to an approver who left in August",
        "Threshold sent it to the wrong cost centre owner",
        "Sat unapproved for a week, escalated manually",
    ),
    "duplicate_invoice": (
        "Same invoice number submitted twice by two requesters",
        "Vendor re-sent the invoice, both got entered",
        "Near match on amount and date, confirmed not a duplicate",
    ),
}

OWNERS = ("A. Okafor", "J. Lindqvist", "M. Haddad", "P. Suryavanshi", "R. Delgado")

VENDOR_POOL = (
    "Northwind Logistics", "Beacon Cloud", "Harborline Print", "Vertex Facilities",
    "Lumen Legal", "Copperfield Staffing", "Atlas Freight", "Sable Analytics",
    "Pinegrove Catering", "Kestrel Security", "Orinoco Media", "Tallow & Finch",
    "Driftwood Travel", "Mercer Hardware", "Quillon Software", "Arbor Health",
    "Castellan Audit", "Fernway Utilities", "Granite Shipping", "Helio Labs",
    "Ironvale Supply", "Juniper Telecom", "Larkspur Design", "Monsoon Hosting",
    "Nimbus Couriers", "Oakenshaw Rentals", "Perrin Consulting", "Quarry Works",
    "Redcliff Insurance", "Sandpiper Foods", "Thornbury Legal", "Umber Studios",
    "Vantage Office", "Westmere Energy", "Yarrow Maintenance", "Zephyr Imports",
)

# Chronic pairs: a small set of (vendor, cause) combinations that keep coming
# back. This is the concentration the ranking model is built to find.
CHRONIC_PAIRS: tuple[tuple[str, str], ...] = (
    ("Northwind Logistics", "missing_po"),
    ("Copperfield Staffing", "missing_po"),
    ("Atlas Freight", "missing_po"),
    ("Beacon Cloud", "gl_coding"),
    ("Monsoon Hosting", "gl_coding"),
    ("Pinegrove Catering", "vendor_details"),
    ("Yarrow Maintenance", "vendor_details"),
    ("Orinoco Media", "approval_routing"),
    ("Granite Shipping", "duplicate_invoice"),
)

# Share of exceptions drawn from the chronic pairs rather than the long tail.
CHRONIC_SHARE = 0.46


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def _window(months: int) -> tuple[datetime, datetime]:
    """Closed six-month window ending at the start of the current month."""
    end = datetime(2026, 10, 1)
    start = end - timedelta(days=30 * months)
    return start, end


def build_exceptions(seed: int = RANDOM_SEED, n: int = N_EXCEPTIONS) -> list[dict]:
    rng = random.Random(seed)
    start, end = _window(MONTHS)
    span_days = (end - start).days

    rows: list[dict] = []
    for i in range(n):
        if rng.random() < CHRONIC_SHARE:
            vendor, cause = rng.choice(CHRONIC_PAIRS)
        else:
            vendor = rng.choice(VENDOR_POOL)
            cause = _weighted_choice(rng, CAUSE_WEIGHTS)

        opened = start + timedelta(
            days=rng.randrange(span_days),
            hours=rng.randrange(8, 19),
            minutes=rng.randrange(60),
        )

        mean, stdev = MINUTES_PROFILE[cause]
        minutes = max(4, round(rng.gauss(mean, stdev)))

        # Older exceptions are more likely to be closed by now.
        age_days = (end - opened).days
        resolved_odds = 0.55 + min(0.40, age_days / 400)
        if rng.random() < resolved_odds:
            status = "resolved"
            # Calendar time to resolve is much longer than hands-on minutes.
            resolved = opened + timedelta(hours=max(1.0, rng.gauss(minutes / 6 + 20, 18)))
            resolved = min(resolved, end + timedelta(days=5))
            reopened = rng.random() < REOPEN_RATE[cause]
        else:
            status = "in_review" if rng.random() < 0.6 else "open"
            resolved = None
            reopened = False

        rows.append(
            {
                "invoice_id": f"INV-{2026}{i:04d}",
                "vendor": vendor,
                "amount": round(rng.lognormvariate(7.4, 0.9), 2),
                "exception_type": EXCEPTION_TYPE[cause],
                "status": status,
                "opened_at": opened.isoformat(timespec="seconds"),
                "resolved_at": resolved.isoformat(timespec="seconds") if resolved else "",
                "root_cause": cause,
                "owner": rng.choice(OWNERS),
                "minutes_spent": minutes,
                "reopened": str(bool(reopened)).lower(),
                "reviewer_note": rng.choice(REVIEWER_NOTES[cause]),
            }
        )

    rows.sort(key=lambda r: r["opened_at"])
    return rows


def build_bill_volume(seed: int = RANDOM_SEED, months: int = MONTHS) -> list[dict]:
    """Monthly bills processed, the denominator for the primary metric.

    Covers exactly the months the exception window spans, so no partial month
    drags the per-1,000 rate down.

    Without a denominator, a falling exception count can just mean a quiet month.
    """
    rng = random.Random(seed + 1)
    start, _ = _window(months)
    rows = []
    base = 1180
    for m in range(months):
        month = (start.replace(day=1) + timedelta(days=31 * m)).strftime("%Y-%m")
        bills = int(base * (1.06 ** m) * rng.uniform(0.94, 1.06))
        rows.append({"month": month, "bills_processed": bills})
    return rows


def write_csv(path, rows: list[dict], columns: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    exceptions = build_exceptions()
    write_csv(EXCEPTIONS_CSV, exceptions, REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
    volume = build_bill_volume()
    write_csv(BILL_VOLUME_CSV, volume, ("month", "bills_processed"))
    print(f"wrote {len(exceptions)} exceptions -> {EXCEPTIONS_CSV}")
    print(f"wrote {len(volume)} months of bill volume -> {BILL_VOLUME_CSV}")


if __name__ == "__main__":
    main()
