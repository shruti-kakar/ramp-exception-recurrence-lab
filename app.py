"""Exception Recurrence Lab — Streamlit front end.

An independent product-operations case study on Ramp Bill Pay. All data is
synthetic. Nothing here connects to Ramp, and no figure in this app is a
measured result.

Run with: streamlit run app.py
"""

from __future__ import annotations

import io

import altair as alt
import pandas as pd
import streamlit as st

from src import analytics, interventions, scenario, theme
from src.config import (
    DEFAULT_REDUCTION_PCT,
    DEFAULT_REVIEWER_HOURLY_COST,
    EXCEPTIONS_CSV,
)
from src.loader import SchemaError, load_bill_volume, load_exceptions

st.set_page_config(
    page_title="Exception Recurrence Lab",
    page_icon="◳",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.enable_altair_theme()

st.markdown(f"<style>{theme.css()}</style>", unsafe_allow_html=True)

CAUSE_LABELS = {
    "missing_po": "Missing PO",
    "gl_coding": "GL coding",
    "vendor_details": "Vendor details",
    "approval_routing": "Approval routing",
    "duplicate_invoice": "Duplicate invoice",
}


def label(cause: str) -> str:
    return CAUSE_LABELS.get(cause, cause.replace("_", " ").title())


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _bundled() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the sample dataset, generating it first if it is not on disk.

    The generated CSVs are gitignored, so a fresh clone and a hosted deployment
    both arrive with no data file. Rebuilding it is deterministic and takes
    milliseconds, which is a better reviewer experience than an error telling
    them to run a command they cannot run on a hosted app.
    """
    if not EXCEPTIONS_CSV.exists():
        from src.generate_data import main as generate

        generate()
    return load_exceptions(strict=False), load_bill_volume()


def _uploaded(file) -> pd.DataFrame:
    from src.loader import coerce, validate

    raw = pd.read_csv(file, dtype=str)
    problems = validate(raw)
    fatal = [p for p in problems if "expected only for duplicate cases" not in p]
    if fatal:
        raise SchemaError(" · ".join(fatal))
    for warning in problems:
        st.sidebar.warning(warning)
    return coerce(raw)


def _caption(text: str) -> None:
    st.markdown(f"<p class='erl-caption'>{text}</p>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.markdown("<p class='erl-eyebrow'>Data source</p>", unsafe_allow_html=True)
upload = st.sidebar.file_uploader("Exception CSV", type="csv", label_visibility="collapsed")

volume = pd.DataFrame()
try:
    if upload is not None:
        raw_df = _uploaded(upload)
        st.sidebar.success(f"Loaded {len(raw_df):,} rows from upload")
    else:
        raw_df, volume = _bundled()
        st.sidebar.caption(f"Bundled sample · {EXCEPTIONS_CSV.name} · {len(raw_df):,} synthetic rows")
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()
except SchemaError as exc:
    st.sidebar.error(f"Schema check failed — {exc}")
    st.stop()

full = analytics.add_derived(raw_df)

st.sidebar.markdown("<hr class='erl-rule'>", unsafe_allow_html=True)
st.sidebar.markdown("<p class='erl-eyebrow'>Filters</p>", unsafe_allow_html=True)

causes = st.sidebar.multiselect(
    "Root cause",
    options=sorted(full["root_cause"].unique()),
    default=sorted(full["root_cause"].unique()),
    format_func=label,
)
statuses = st.sidebar.multiselect(
    "Status",
    options=sorted(full["status"].unique()),
    default=sorted(full["status"].unique()),
)
months = sorted(full["month"].unique())
month_range = st.sidebar.select_slider(
    "Month opened", options=months, value=(months[0], months[-1])
) if len(months) > 1 else (months[0], months[0])

st.sidebar.markdown("<hr class='erl-rule'>", unsafe_allow_html=True)
st.sidebar.markdown("<p class='erl-eyebrow'>Assumptions</p>", unsafe_allow_html=True)
hourly_cost = st.sidebar.number_input(
    "Loaded reviewer cost per hour (USD)",
    min_value=10.0,
    max_value=250.0,
    value=DEFAULT_REVIEWER_HOURLY_COST,
    step=1.0,
    help="Used only to translate reviewer hours into a figure finance teams recognise.",
)
_caption_sidebar = (
    "Every projection in this app is arithmetic on assumptions you control. "
    "None of it is measured Ramp performance."
)
st.sidebar.markdown(f"<p class='erl-caption'>{_caption_sidebar}</p>", unsafe_allow_html=True)

df = full[
    full["root_cause"].isin(causes)
    & full["status"].isin(statuses)
    & full["month"].between(month_range[0], month_range[1])
]

if df.empty:
    st.warning("No exceptions match the current filters.")
    st.stop()

# Recurrence is a property of the whole window, so clusters are computed on the
# unfiltered data and the filter only chooses which of them to display.
metrics = analytics.baseline_metrics(df, volume)
causes_table = analytics.root_cause_table(df)
clusters = analytics.cluster_table(df)
trend = analytics.monthly_trend(df, volume)

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown("<p class='erl-eyebrow'>Case study 01 · Ramp Bill Pay</p>", unsafe_allow_html=True)
st.markdown("# Exception Recurrence Lab")
st.markdown(
    "<p class='erl-lede'>From resolving exceptions to preventing them. "
    "An independent product-operations study of where recurring invoice exceptions "
    "come from, and which upstream fix is worth running an experiment on.</p>",
    unsafe_allow_html=True,
)
st.markdown(
    "<span class='erl-tag'>Synthetic data</span>&nbsp;"
    "<span class='erl-tag--muted erl-tag'>No Ramp integration</span>&nbsp;"
    "<span class='erl-tag--muted erl-tag'>Projections, not results</span>",
    unsafe_allow_html=True,
)
st.markdown("<hr class='erl-rule'>", unsafe_allow_html=True)

tab_baseline, tab_rank, tab_worklist, tab_scenario, tab_gap = st.tabs(
    ["Baseline", "Where to fix", "Worklist", "Prevention scenario", "Gap map"]
)

# --------------------------------------------------------------------------- #
# Baseline
# --------------------------------------------------------------------------- #
with tab_baseline:
    cols = st.columns(5)
    cols[0].metric("Exceptions", f"{metrics['exceptions']:,}")
    cols[1].metric("Repeat share", f"{metrics['repeat_share']:.0%}")
    cols[2].metric("Reviewer hours", f"{metrics['reviewer_hours']:.0f}")
    rate = metrics["exceptions_per_1000_bills"]
    cols[3].metric("Per 1,000 bills", f"{rate:.1f}" if rate else "n/a")
    cols[4].metric("Reopen rate", f"{metrics['reopen_rate']:.0%}")
    _caption(
        f"{metrics['months']} month window · {metrics['vendors_affected']} vendors · "
        f"{metrics['open_now']} still in the queue · median {metrics['median_minutes']:.0f} "
        f"hands-on minutes per case."
        + (
            f" Denominator: {metrics['bills_processed']:,.0f} bills processed."
            if metrics["bills_processed"]
            else " No bill-volume file loaded, so rates per 1,000 bills are unavailable."
        )
    )

    st.markdown("## What a feedback loop could and could not touch")
    split = analytics.first_vs_repeat(df)
    left, right = st.columns([2, 3], gap="large")
    with left:
        chart = (
            alt.Chart(split)
            .mark_bar()
            .encode(
                y=alt.Y("bucket:N", title=None, sort="-x"),
                x=alt.X("reviewer_hours:Q", title="Reviewer hours"),
                color=alt.Color(
                    "bucket:N",
                    scale=alt.Scale(
                        domain=["repeat occurrence", "first occurrence"],
                        range=[theme.INK, theme.RULE],
                    ),
                    legend=None,
                ),
                tooltip=["bucket", alt.Tooltip("exceptions:Q"), alt.Tooltip("reviewer_hours:Q", format=".1f")],
            )
            .properties(height=120)
        )
        st.altair_chart(chart, use_container_width=True)
    with right:
        st.markdown(
            f"<div class='erl-panel erl-panel--accent'>"
            f"<p class='erl-eyebrow'>Addressable pool</p>"
            f"<p class='erl-big'>{metrics['repeat_reviewer_hours']:.0f} h</p>"
            f"<p class='erl-caption'>Of {metrics['reviewer_hours']:.0f} reviewer hours in this window, "
            f"{metrics['repeat_reviewer_hours']:.0f} were spent on the second or later time the same "
            f"vendor hit the same root cause. A learning loop can only ever target that part. "
            f"The first occurrence of a novel problem is the cost of doing business.</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown("## Trend")
    if "exceptions_per_1000_bills" in trend.columns:
        long = trend.melt(
            id_vars="month",
            value_vars=["exceptions_per_1000_bills", "repeats_per_1000_bills"],
            var_name="series",
            value_name="rate",
        )
        long["series"] = long["series"].map(
            {
                "exceptions_per_1000_bills": "All exceptions",
                "repeats_per_1000_bills": "Repeat exceptions",
            }
        )
        line = (
            alt.Chart(long)
            .mark_line(point=True)
            .encode(
                x=alt.X("month:N", title=None),
                y=alt.Y("rate:Q", title="Per 1,000 bills"),
                color=alt.Color(
                    "series:N",
                    title=None,
                    scale=alt.Scale(
                        domain=["All exceptions", "Repeat exceptions"],
                        range=[theme.INK_40, theme.INK],
                    ),
                ),
                tooltip=["month", "series", alt.Tooltip("rate:Q", format=".1f")],
            )
            .properties(height=240)
        )
        st.altair_chart(line, use_container_width=True)
        _caption(
            "The total rate falls while the repeat rate holds. That shape is the whole argument: "
            "the team is getting better at closing exceptions without the same vendor/cause pairs "
            "stopping. In this synthetic dataset that pattern is built in by design, which is why "
            "it is a hypothesis to test against real data, not a finding."
        )
    else:
        st.bar_chart(trend.set_index("month")["exceptions"])
        _caption("No bill-volume file loaded, so this shows raw counts rather than a rate.")

# --------------------------------------------------------------------------- #
# Where to fix
# --------------------------------------------------------------------------- #
with tab_rank:
    st.markdown("## Ranked by what a fix would be worth, not by volume")
    _caption(
        "Prevention index = addressable repeat hours per month × vendor concentration × "
        "fixability prior. Concentration is the share of a cause's repeat hours sitting with its "
        "three heaviest vendors. The fixability prior is the author's estimate of how much an "
        "upstream control could remove, and it is the most arguable number in the project."
    )

    display = causes_table.assign(cause=causes_table["root_cause"].map(label))
    bar = (
        alt.Chart(display)
        .mark_bar()
        .encode(
            y=alt.Y("cause:N", title=None, sort="-x"),
            x=alt.X("prevention_index:Q", title="Prevention index"),
            color=alt.value(theme.INK),
            tooltip=[
                alt.Tooltip("cause:N", title="Root cause"),
                alt.Tooltip("repeat_hours_per_month:Q", title="Repeat h/month", format=".1f"),
                alt.Tooltip("concentration:Q", title="Concentration", format=".0%"),
                alt.Tooltip("fixability:Q", title="Fixability", format=".2f"),
                alt.Tooltip("prevention_index:Q", title="Index", format=".2f"),
            ],
        )
        .properties(height=190)
    )
    st.altair_chart(bar, use_container_width=True)

    flips = display[display["rank"] != display["rank_by_volume"]]
    if len(flips):
        moves = ", ".join(
            f"{r.cause} moves {r.rank_by_volume} → {r.rank}" for r in flips.itertuples()
        )
        st.markdown(
            f"<div class='erl-panel erl-panel--accent'><p class='erl-eyebrow'>Ranking changes</p>"
            f"<p>{moves}.</p><p class='erl-caption'>Where the two rankings agree, a volume report "
            f"is good enough and this tool adds nothing. The disagreements are the only places it "
            f"earns its keep.</p></div>",
            unsafe_allow_html=True,
        )

    st.dataframe(
        display[
            [
                "rank", "cause", "exceptions", "repeat_exceptions", "repeat_share",
                "repeat_hours_per_month", "concentration", "fixability",
                "prevention_index", "rank_by_volume", "reopen_rate",
                "median_resolution_hours", "amount_exposed",
            ]
        ].rename(
            columns={
                "cause": "root cause",
                "repeat_hours_per_month": "repeat h/month",
                "rank_by_volume": "rank by volume",
                "median_resolution_hours": "median hours to resolve",
                "amount_exposed": "invoice value touched",
            }
        ),
        hide_index=True,
        use_container_width=True,
        column_config={
            "repeat_share": st.column_config.NumberColumn(format="%.0f%%"),
            "concentration": st.column_config.NumberColumn(format="%.0f%%"),
            "reopen_rate": st.column_config.NumberColumn(format="%.0f%%"),
            "repeat h/month": st.column_config.NumberColumn(format="%.1f"),
            "prevention_index": st.column_config.NumberColumn(format="%.2f"),
            "fixability": st.column_config.NumberColumn(format="%.2f"),
            "median hours to resolve": st.column_config.NumberColumn(format="%.0f"),
            "invoice value touched": st.column_config.NumberColumn(format="$%.0f"),
        },
    )

    st.markdown("## Candidate intervention")
    pick = st.selectbox(
        "Root cause",
        options=list(causes_table["root_cause"]),
        format_func=label,
        label_visibility="collapsed",
    )
    iv = interventions.for_cause(pick)
    if iv is None:
        st.info("No intervention catalogued for this cause yet.")
    else:
        st.markdown(f"### {iv.label}")
        a, b = st.columns(2, gap="large")
        with a:
            st.markdown(f"**Upstream change**  \n{iv.upstream_change}")
            st.markdown(f"**Owner**  \n{iv.owner}")
            st.markdown(f"**Ramp surface it would live on**  \n{iv.surface}")
        with b:
            st.markdown(f"**Signal that would confirm it worked**  \n{iv.confirming_signal}")
            st.markdown(f"**How it fails**  \n{iv.failure_mode}")
            st.markdown(f"**Build effort (author's estimate)**  \n{iv.effort}")
        _caption(
            "Candidate interventions are product proposals written against Ramp's publicly "
            "documented surfaces. They are not Ramp roadmap items and this app changes nothing."
        )

# --------------------------------------------------------------------------- #
# Worklist
# --------------------------------------------------------------------------- #
with tab_worklist:
    st.markdown("## Recurring vendor and cause pairs")
    _caption(
        "Each row is one conversation or one configuration change, not a category. "
        "Sorted by the reviewer hours spent on repeat occurrences."
    )
    if clusters.empty:
        st.info("No vendor/cause pair recurs within the current filters.")
    else:
        st.dataframe(
            clusters.assign(**{"root cause": clusters["root_cause"].map(label)}).drop(
                columns="root_cause"
            )[
                ["vendor", "root cause", "occurrences", "repeat_hours", "days_recurring",
                 "still_open", "amount_exposed", "first_seen", "last_seen"]
            ].rename(
                columns={
                    "repeat_hours": "repeat hours",
                    "days_recurring": "days recurring",
                    "still_open": "still open",
                    "amount_exposed": "invoice value touched",
                    "first_seen": "first seen",
                    "last_seen": "last seen",
                }
            ),
            hide_index=True,
            use_container_width=True,
            column_config={
                "repeat hours": st.column_config.NumberColumn(format="%.1f"),
                "invoice value touched": st.column_config.NumberColumn(format="$%.0f"),
                "first seen": st.column_config.DatetimeColumn(format="D MMM YYYY"),
                "last seen": st.column_config.DatetimeColumn(format="D MMM YYYY"),
            },
        )

        st.markdown("## Inspect the cases behind a pair")
        options = [f"{r.vendor} · {label(r.root_cause)}" for r in clusters.itertuples()]
        chosen = st.selectbox("Pair", options, label_visibility="collapsed")
        vendor_sel, cause_label = chosen.split(" · ")
        cause_sel = next(k for k, v in CAUSE_LABELS.items() if v == cause_label)
        cases = df[(df["vendor"] == vendor_sel) & (df["root_cause"] == cause_sel)].sort_values(
            "opened_at"
        )
        st.dataframe(
            cases[
                ["occurrence", "invoice_id", "opened_at", "status", "minutes_spent",
                 "resolution_hours", "reopened", "amount", "owner", "reviewer_note"]
            ].rename(
                columns={
                    "minutes_spent": "minutes",
                    "resolution_hours": "hours to resolve",
                    "reviewer_note": "reviewer note",
                }
            ),
            hide_index=True,
            use_container_width=True,
            column_config={
                "opened_at": st.column_config.DatetimeColumn("opened", format="D MMM YYYY"),
                "hours to resolve": st.column_config.NumberColumn(format="%.0f"),
                "amount": st.column_config.NumberColumn(format="$%.0f"),
            },
        )
        _caption(
            "Reviewer notes are synthetic free text. They exist so a later iteration can test "
            "whether a model can read a note and propose the root cause, measured against these "
            "labels as ground truth."
        )

# --------------------------------------------------------------------------- #
# Prevention scenario
# --------------------------------------------------------------------------- #
with tab_scenario:
    st.markdown("## If prevention worked, how much would stop happening?")
    reduction = st.slider(
        "Assumed reduction in repeat exceptions",
        min_value=0,
        max_value=50,
        value=DEFAULT_REDUCTION_PCT,
        step=5,
        format="%d%%",
    )
    projected = scenario.expected_value(causes_table, reduction, hourly_cost)
    total_point = float(projected["hours_saved_point"].sum())
    total_low = float(projected["hours_saved_low"].sum())
    total_high = float(projected["hours_saved_high"].sum())
    total_expected = float(projected["expected_hours_per_month"].sum())

    c = st.columns(4)
    c[0].metric("Addressable hours / month", f"{projected['addressable_hours_per_month'].sum():.1f}")
    c[1].metric("Hours avoided / month", f"{total_point:.1f}", help="Point estimate at the chosen assumption")
    c[2].metric("Fixability-weighted", f"{total_expected:.1f}")
    c[3].metric("Annualised cost", f"${total_point * 12 * hourly_cost:,.0f}")
    _caption(
        f"Sensitivity band {total_low:.1f} to {total_high:.1f} hours per month. "
        f"{scenario.DISCLAIMER}"
    )

    st.dataframe(
        projected.assign(cause=projected["root_cause"].map(label))[
            ["cause", "addressable_hours_per_month", "hours_saved_point", "hours_saved_low",
             "hours_saved_high", "fixability", "expected_hours_per_month", "expected_cost_per_year"]
        ].rename(
            columns={
                "addressable_hours_per_month": "addressable h/month",
                "hours_saved_point": "avoided h/month",
                "hours_saved_low": "low",
                "hours_saved_high": "high",
                "expected_hours_per_month": "weighted h/month",
                "expected_cost_per_year": "weighted $/year",
            }
        ),
        hide_index=True,
        use_container_width=True,
        column_config={
            "addressable h/month": st.column_config.NumberColumn(format="%.2f"),
            "avoided h/month": st.column_config.NumberColumn(format="%.2f"),
            "low": st.column_config.NumberColumn(format="%.2f"),
            "high": st.column_config.NumberColumn(format="%.2f"),
            "fixability": st.column_config.NumberColumn(format="%.2f"),
            "weighted h/month": st.column_config.NumberColumn(format="%.2f"),
            "weighted $/year": st.column_config.NumberColumn(format="$%.0f"),
        },
    )

    st.markdown("## Could a 30-day pilot actually detect this?")
    repeat_rate = metrics["repeats_per_1000_bills"]
    monthly_bills = (metrics["bills_processed"] or 0) / max(1, metrics["months"])
    if repeat_rate and monthly_bills:
        needed = scenario.pilot_sample_size(repeat_rate, 0.20)
        months_needed = needed / monthly_bills if needed else None
        panel_class = "erl-panel erl-panel--flag" if months_needed and months_needed > 1 else "erl-panel erl-panel--accent"
        st.markdown(
            f"<div class='{panel_class}'><p class='erl-eyebrow'>Statistical power check</p>"
            f"<p>At a repeat rate of {repeat_rate:.1f} per 1,000 bills, detecting a 20% relative "
            f"improvement at 80% power needs about <strong>{needed:,} bills per arm</strong>. "
            f"This team processes roughly {monthly_bills:,.0f} bills a month, so one arm would "
            f"take about <strong>{months_needed:.0f} months</strong> to fill.</p>"
            f"<p class='erl-caption'>The PRD proposes a 30-day experiment. On these volumes that "
            f"window cannot measure the primary metric. The experiment has to change: pool several "
            f"customers, pick a larger cohort, or judge the pilot on a leading indicator such as "
            f"the share of exceptions caught before review, with recurrence read later.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        _caption("Load a bill-volume file to run the power check.")

    st.markdown("## Export")
    buffer = io.StringIO()
    export = causes_table.merge(
        projected[["root_cause", "hours_saved_point", "hours_saved_low", "hours_saved_high",
                   "expected_hours_per_month"]],
        on="root_cause",
        how="left",
    )
    export["assumption_pct"] = reduction
    export["reviewer_hourly_cost"] = hourly_cost
    export["basis"] = scenario.DISCLAIMER
    export.to_csv(buffer, index=False)
    st.download_button(
        "Download summary CSV",
        data=buffer.getvalue(),
        file_name=f"recurrence_summary_{reduction}pct.csv",
        mime="text/csv",
    )

# --------------------------------------------------------------------------- #
# Gap map
# --------------------------------------------------------------------------- #
with tab_gap:
    st.markdown("## What Ramp already ships, and where this sits")
    _caption(
        "Each row links to a live Ramp page, fetched and checked during this project rather than "
        "assumed. Ramp's public surface is more capable than a first pass at this research "
        "suggested — see the revision note below the table."
    )
    gap = pd.DataFrame(
        [
            ("Bill Pay: Needs Review queue", "Central queue for payments needing intervention, including missing information", "Already provides exception triage"),
            ("AP Review Agent", "Checks bills against policy, contracts, POs and supporting documents; flags inconsistencies", "Already detects many invoice exceptions"),
            ("Approval Intelligence", "AI summaries, anomaly flags, recommendations, historical spending context", "Already assists human reviewers"),
            ("Smart OCR & Auto-coding", "Extracts invoice data, learns GL coding from historical corrections", "Already addresses missing/incorrect GL coding"),
            ("Bill Pay Submission Policies", "Validates required fields at submission, flags violations, records overrides", "Already enforces preventive controls"),
            ("Audit Logs & Bills/Vendors APIs", "Records workflow events; agent attribution added Sep 2026", "Credible data foundation, not yet exposed as recurrence analysis — see below"),
        ],
        columns=["Public Ramp capability", "What it does", "Relevance to this project"],
    )
    st.dataframe(gap, hide_index=True, use_container_width=True)

    st.markdown(
        "<div class='erl-panel erl-panel--accent'><p class='erl-eyebrow'>Revised, not discovered</p>"
        "<p>An earlier pass at this research read Ramp's public surface as a plain exception "
        "detector and concluded a recurrence layer was simply missing. It wasn't wrong about the "
        "gap, but it understated how much Ramp already automates: an AI agent reviews bills "
        "against policy and documents today, and submission policies already prevent some of what "
        "this prototype's interventions propose. The gap this project actually stands behind is "
        "narrower and more precise: no public Ramp page shows all four of (1) grouping historical "
        "exceptions into recurring root-cause patterns, (2) estimating which patterns cost the "
        "most avoidable work, (3) recommending an upstream change per pattern, and (4) tracking "
        "whether that change reduced recurrence. Any one or two of those might already exist "
        "privately — see CASESTUDY.md for the full revision.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### A real data foundation, verified directly")
    st.markdown(
        "Ramp's `GET /developer/v1/audit-logs/events` endpoint returns an `actor_type` "
        "(`policy_agent`, `spend_request_agent`, `ramp`, or `user`) and an `agent_details.agent_name` "
        "field on every event — confirmed by reading the live OpenAPI schema, not assumed. That is a "
        "real foundation for a Bills + Vendors + Audit Logs integration. Two limits showed up in the "
        "same schema: the event-type list includes an `Exception` family, but those events are "
        "policy-limit overrides, not invoice-processing exceptions like a missing PO or a GL miscode; "
        "and the Bills endpoint carries no root-cause or review-time field. A real version of this "
        "tool would have to infer recurrence from proxies — repeated `Violation from rule` events on "
        "the same vendor, say — rather than read it off a label, the way this synthetic dataset does."
    )
    _caption(
        '<a href="https://docs.ramp.com/developer-api/v1/api/audit-logs">Audit Logs API</a> &middot; '
        '<a href="https://docs.ramp.com/developer-api/v1/changelog">Developer API changelog</a> &middot; '
        '<a href="https://support.ramp.com/ap-agents-available-in-ramp-bill-pay">AP agents in Bill Pay</a> &middot; '
        '<a href="https://support.ramp.com/managing-bills-and-payments-on-bill-pay">Managing bills and payments</a>'
    )

    st.markdown(
        "<div class='erl-panel'><p class='erl-eyebrow'>Honest limits</p>"
        "<p>No Ramp integration, no authentication, no real customer data, no AI inference, and "
        "no measured savings. The dataset is generated with a built-in recurrence pattern, so the "
        "pattern this app finds is the one it was given. The value on offer is the method and the "
        "argument, not the numbers.</p></div>",
        unsafe_allow_html=True,
    )
    _caption("PRD.md, CASESTUDY.md, ASSUMPTIONS.md and DESIGN.md in the repository carry the full reasoning.")
