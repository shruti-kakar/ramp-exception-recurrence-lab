"""Single source of truth for schema, paths, and modelling assumptions.

Every number in this file is an *assumption*, not a measurement. Each one carries
a comment saying where it came from so a reviewer can argue with it. Nothing here
is derived from Ramp or JPMorgan internal data.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EXPORT_DIR = ROOT / "exports"

EXCEPTIONS_CSV = DATA_DIR / "exceptions.csv"
BILL_VOLUME_CSV = DATA_DIR / "bill_volume.csv"

# --- Schema -----------------------------------------------------------------
# Required columns match the PRD data model exactly. Optional columns are
# forward-looking extensions (see MILESTONES.md M5: AI root-cause assist).
REQUIRED_COLUMNS: tuple[str, ...] = (
    "invoice_id",
    "vendor",
    "amount",
    "exception_type",
    "status",
    "opened_at",
    "resolved_at",
    "root_cause",
    "owner",
    "minutes_spent",
)

OPTIONAL_COLUMNS: tuple[str, ...] = (
    "reopened",      # was the exception closed and then reopened
    "reviewer_note", # free text, reserved for later LLM-assisted classification
)

DATE_COLUMNS: tuple[str, ...] = ("opened_at", "resolved_at")
NUMERIC_COLUMNS: tuple[str, ...] = ("amount", "minutes_spent")

STATUSES: tuple[str, ...] = ("open", "in_review", "resolved")

ROOT_CAUSES: tuple[str, ...] = (
    "missing_po",
    "gl_coding",
    "vendor_details",
    "approval_routing",
    "duplicate_invoice",
)

# --- Modelling assumptions --------------------------------------------------
# A "recurrence cluster" is one (vendor, root_cause) pair. The second and later
# occurrences in a cluster are the addressable pool: a learning loop cannot
# prevent the first time a problem is ever seen.
MIN_CLUSTER_SIZE = 2

# Fixability prior: how much of a cause is plausibly addressable by an upstream
# control, given what Ramp's public docs already support. 1.0 would mean a
# submission-time control can fully remove the cause. These are the author's
# priors from AP workflow experience and must be replaced by interview data
# before anyone acts on the ranking. See CASESTUDY.md "What would change my mind".
FIXABILITY_PRIOR: dict[str, float] = {
    "missing_po": 0.80,        # a required-field rule at submission is a known control
    "gl_coding": 0.65,         # vendor-to-GL defaults and memory are well understood
    "vendor_details": 0.70,    # vendor-managed onboarding moves the work upstream
    "approval_routing": 0.55,  # policy config helps, org churn keeps re-breaking it
    "duplicate_invoice": 0.35, # genuinely hard: needs matching, not a form rule
}

# Loaded cost of one reviewer hour, used only to translate minutes into a figure
# finance teams recognise. Rough US AP-analyst midpoint; override in the sidebar.
DEFAULT_REVIEWER_HOURLY_COST = 48.0

# Working hours used for the full-time-equivalent translation.
HOURS_PER_FTE_MONTH = 160.0

# Default prevention assumption for the scenario slider, deliberately modest.
DEFAULT_REDUCTION_PCT = 10

# Sensitivity band applied around any scenario estimate, so a single point
# number never gets quoted on its own.
SENSITIVITY_BAND = 0.5  # +/- 50% of the chosen assumption

# --- Synthetic data generation ---------------------------------------------
RANDOM_SEED = 20261026
N_EXCEPTIONS = 300
MONTHS = 6
