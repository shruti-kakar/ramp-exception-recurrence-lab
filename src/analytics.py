"""Recurrence analytics: the part of the project that is actually a point of view.

The ordinary version of this tool counts exceptions by category and stops. That
ranking tells an operations team where review time goes, not where a fix would
pay off. Three adjustments separate the two:

1. Only *repeat* occurrences are addressable. The first time a vendor/cause pair
   appears, no learning loop could have prevented it, so first occurrences are
   excluded from the addressable pool.
2. Concentrated causes are cheaper to fix than diffuse ones. A cause driven by
   three vendors can be fixed with a targeted change; the same minutes spread
   across thirty vendors needs a platform change.
3. Causes differ in how much an upstream control can remove at all. That prior
   lives in config.FIXABILITY_PRIOR and is the most arguable number here.

Every function is pure and takes a DataFrame, so the tests cover the product
logic without launching the UI.
"""

from __future__ import annotations

import pandas as pd

from src.config import FIXABILITY_PRIOR, MIN_CLUSTER_SIZE

CLUSTER_KEYS = ("vendor", "root_cause")

# How many vendors count as "concentrated" for a cause. Three is a judgement
# call: it is roughly the number of vendor-specific fixes one AP admin can own
# in a month. Changing it changes the ranking, so it is named, not buried.
TOP_VENDORS_FOR_CONCENTRATION = 3


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Attach recurrence structure and timing columns.

    Adds:
      month              calendar month the exception opened
      cluster            the vendor/root_cause pair
      occurrence         1-based position within its cluster, oldest first
      is_repeat          occurrence >= MIN_CLUSTER_SIZE
      cluster_size       total occurrences in the cluster across the window
      resolution_hours   calendar hours from opened to resolved, NaN if open
    """
    out = df.sort_values("opened_at").copy()
    out["month"] = out["opened_at"].dt.strftime("%Y-%m")
    out["cluster"] = out["vendor"].str.cat(out["root_cause"], sep=" / ")

    grouped = out.groupby(list(CLUSTER_KEYS), sort=False)
    out["occurrence"] = grouped.cumcount() + 1
    out["cluster_size"] = grouped["invoice_id"].transform("size")
    out["is_repeat"] = out["occurrence"] >= MIN_CLUSTER_SIZE

    delta = out["resolved_at"] - out["opened_at"]
    out["resolution_hours"] = delta.dt.total_seconds() / 3600.0
    return out


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def months_covered(df: pd.DataFrame) -> int:
    """Distinct months in the window, floored at 1 so monthly rates never divide by zero."""
    return max(1, int(df["month"].nunique()))


def baseline_metrics(df: pd.DataFrame, volume: pd.DataFrame | None = None) -> dict:
    """Headline figures for the current filter selection.

    `bills_processed` and the per-1,000 rates are omitted when no volume file is
    supplied, rather than silently substituting the exception count.
    """
    d = df if "is_repeat" in df.columns else add_derived(df)
    n = len(d)
    repeats = int(d["is_repeat"].sum())
    minutes = float(d["minutes_spent"].sum())
    repeat_minutes = float(d.loc[d["is_repeat"], "minutes_spent"].sum())
    resolved = d[d["status"] == "resolved"]

    metrics = {
        "exceptions": n,
        "repeat_exceptions": repeats,
        "repeat_share": _safe_div(repeats, n),
        "reviewer_hours": minutes / 60.0,
        "repeat_reviewer_hours": repeat_minutes / 60.0,
        "median_minutes": float(d["minutes_spent"].median()) if n else 0.0,
        "median_resolution_hours": (
            float(resolved["resolution_hours"].median()) if len(resolved) else float("nan")
        ),
        "reopen_rate": _safe_div(int(resolved["reopened"].sum()), len(resolved)),
        "open_now": int((d["status"] != "resolved").sum()),
        "vendors_affected": int(d["vendor"].nunique()),
        "months": months_covered(d),
        "bills_processed": None,
        "exceptions_per_1000_bills": None,
        "repeats_per_1000_bills": None,
    }

    if volume is not None and len(volume):
        in_window = volume[volume["month"].isin(set(d["month"]))]
        bills = float(in_window["bills_processed"].sum())
        if bills:
            metrics["bills_processed"] = bills
            metrics["exceptions_per_1000_bills"] = n / bills * 1000
            metrics["repeats_per_1000_bills"] = repeats / bills * 1000
    return metrics


def concentration(df_cause: pd.DataFrame, top_n: int = TOP_VENDORS_FOR_CONCENTRATION) -> float:
    """Share of a cause's repeat minutes held by its heaviest few vendors.

    1.0 means the whole cause sits with a handful of vendors and a targeted fix
    reaches all of it. Values near 0 mean the cause is diffuse and needs a
    product change rather than a vendor conversation.
    """
    repeats = df_cause[df_cause["is_repeat"]]
    total = float(repeats["minutes_spent"].sum())
    if not total:
        return 0.0
    by_vendor = repeats.groupby("vendor")["minutes_spent"].sum().sort_values(ascending=False)
    return float(by_vendor.head(top_n).sum() / total)


def root_cause_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per root cause, ranked by prevention index.

    Columns a reviewer should read first:
      repeat_hours_per_month   addressable review effort, repeats only
      concentration            0-1, how few vendors drive the repeats
      fixability               0-1 assumption from config, argue with it
      prevention_index         repeat_hours_per_month * concentration * fixability
    """
    d = df if "is_repeat" in df.columns else add_derived(df)
    n_months = months_covered(d)

    rows = []
    for cause, grp in d.groupby("root_cause"):
        repeats = grp[grp["is_repeat"]]
        repeat_minutes = float(repeats["minutes_spent"].sum())
        conc = concentration(grp)
        fix = FIXABILITY_PRIOR.get(cause, 0.5)
        repeat_hours_month = repeat_minutes / 60.0 / n_months
        resolved = grp[grp["status"] == "resolved"]
        rows.append(
            {
                "root_cause": cause,
                "exceptions": len(grp),
                "repeat_exceptions": int(grp["is_repeat"].sum()),
                "repeat_share": _safe_div(int(grp["is_repeat"].sum()), len(grp)),
                "vendors": int(grp["vendor"].nunique()),
                "repeat_vendors": int(repeats["vendor"].nunique()),
                "reviewer_hours": float(grp["minutes_spent"].sum()) / 60.0,
                "repeat_hours_per_month": repeat_hours_month,
                "median_minutes": float(grp["minutes_spent"].median()),
                "median_resolution_hours": (
                    float(resolved["resolution_hours"].median()) if len(resolved) else float("nan")
                ),
                "reopen_rate": _safe_div(int(resolved["reopened"].sum()), len(resolved)),
                "amount_exposed": float(grp["amount"].sum()),
                "concentration": conc,
                "fixability": fix,
                "prevention_index": repeat_hours_month * conc * fix,
            }
        )

    table = pd.DataFrame(rows).sort_values("prevention_index", ascending=False)
    table["rank"] = range(1, len(table) + 1)
    # The naive ranking the tool is arguing against, kept visible for contrast.
    table["rank_by_volume"] = table["exceptions"].rank(ascending=False, method="min").astype(int)
    return table.reset_index(drop=True)


def cluster_table(df: pd.DataFrame, min_size: int = MIN_CLUSTER_SIZE) -> pd.DataFrame:
    """Recurring vendor/cause pairs, heaviest repeat effort first.

    This is the worklist: each row is one conversation or one configuration
    change, not an abstract category.
    """
    d = df if "is_repeat" in df.columns else add_derived(df)
    rows = []
    for (vendor, cause), grp in d.groupby(list(CLUSTER_KEYS)):
        if len(grp) < min_size:
            continue
        repeats = grp[grp["is_repeat"]]
        span = grp["opened_at"].max() - grp["opened_at"].min()
        rows.append(
            {
                "vendor": vendor,
                "root_cause": cause,
                "occurrences": len(grp),
                "repeat_hours": float(repeats["minutes_spent"].sum()) / 60.0,
                "first_seen": grp["opened_at"].min(),
                "last_seen": grp["opened_at"].max(),
                "days_recurring": int(span.days),
                "amount_exposed": float(grp["amount"].sum()),
                "still_open": int((grp["status"] != "resolved").sum()),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "vendor", "root_cause", "occurrences", "repeat_hours", "first_seen",
                "last_seen", "days_recurring", "amount_exposed", "still_open",
            ]
        )
    return (
        pd.DataFrame(rows)
        .sort_values(["repeat_hours", "occurrences"], ascending=False)
        .reset_index(drop=True)
    )


def monthly_trend(df: pd.DataFrame, volume: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-month counts and, where volume is known, rates per 1,000 bills."""
    d = df if "is_repeat" in df.columns else add_derived(df)
    trend = (
        d.groupby("month")
        .agg(
            exceptions=("invoice_id", "size"),
            repeat_exceptions=("is_repeat", "sum"),
            reviewer_hours=("minutes_spent", lambda s: float(s.sum()) / 60.0),
        )
        .reset_index()
    )
    trend["repeat_exceptions"] = trend["repeat_exceptions"].astype(int)

    if volume is not None and len(volume):
        trend = trend.merge(volume, on="month", how="left")
        trend["exceptions_per_1000_bills"] = (
            trend["exceptions"] / trend["bills_processed"] * 1000
        )
        trend["repeats_per_1000_bills"] = (
            trend["repeat_exceptions"] / trend["bills_processed"] * 1000
        )
    return trend


def first_vs_repeat(df: pd.DataFrame) -> pd.DataFrame:
    """Split review effort into the part a learning loop could address and the part it could not."""
    d = df if "is_repeat" in df.columns else add_derived(df)
    out = (
        d.assign(bucket=d["is_repeat"].map({True: "repeat occurrence", False: "first occurrence"}))
        .groupby("bucket")
        .agg(exceptions=("invoice_id", "size"), reviewer_hours=("minutes_spent", lambda s: float(s.sum()) / 60.0))
        .reset_index()
    )
    return out
