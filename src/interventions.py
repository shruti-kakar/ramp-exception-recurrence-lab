"""Catalogue of candidate upstream interventions, one per root cause.

This is a product artefact, not code that changes anything. Each entry names the
upstream control, the Ramp surface it would plausibly live on, the signal that
would confirm it worked, and the way it could fail. Nothing here is a Ramp
roadmap item or a claim about Ramp's internals.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Intervention:
    root_cause: str
    label: str
    upstream_change: str
    owner: str
    surface: str
    confirming_signal: str
    failure_mode: str
    effort: str  # low | medium | high, author's estimate

    def as_dict(self) -> dict:
        return asdict(self)


INTERVENTIONS: dict[str, Intervention] = {
    "missing_po": Intervention(
        root_cause="missing_po",
        label="Require a PO reference before submission for PO-backed vendors",
        upstream_change=(
            "Mark vendors as PO-required, then block or warn at invoice submission "
            "when no PO reference is present, instead of catching it in review."
        ),
        owner="AP admin + Product Ops",
        surface="Bill submission form / submission policy",
        confirming_signal="Repeat missing-PO exceptions per 1,000 bills falls for PO-required vendors only",
        failure_mode="Vendors mis-flagged as PO-required create submission friction and shadow email invoices",
        effort="low",
    ),
    "gl_coding": Intervention(
        root_cause="gl_coding",
        label="Pre-fill GL coding from the vendor's last approved bill",
        upstream_change=(
            "Default the GL account and department from the vendor's most recent "
            "approved coding, shown as an editable suggestion with its source."
        ),
        owner="Controller + Product",
        surface="Bill coding step",
        confirming_signal="Share of bills edited at the coding step falls without a rise in post-close reclasses",
        failure_mode="A wrong default is accepted silently, moving the error from review into the ledger",
        effort="medium",
    ),
    "vendor_details": Intervention(
        root_cause="vendor_details",
        label="Move bank and tax detail collection to vendor self-service",
        upstream_change=(
            "Send vendors a one-time request for banking and tax details with "
            "validation at entry, so AP stops re-chasing the same fields."
        ),
        owner="AP admin",
        surface="Vendor onboarding",
        confirming_signal="Repeat vendor-detail exceptions per vendor drops after onboarding completion",
        failure_mode="Self-service collection widens the surface for payment-redirect fraud; needs verification controls",
        effort="medium",
    ),
    "approval_routing": Intervention(
        root_cause="approval_routing",
        label="Reconcile approval rules against the current org chart monthly",
        upstream_change=(
            "Flag approval rules pointing at departed or reorganised approvers "
            "before a bill routes to them, rather than after it stalls."
        ),
        owner="Product Ops",
        surface="Approval policy configuration",
        confirming_signal="Median time-to-first-approval falls and stalled-routing reopens decline",
        failure_mode="Over-eager reassignment routes bills to approvers without real authority",
        effort="low",
    ),
    "duplicate_invoice": Intervention(
        root_cause="duplicate_invoice",
        label="Warn on near-duplicate bills at submission, with the match shown",
        upstream_change=(
            "Compare vendor, amount and invoice number against recent bills and "
            "surface the suspected match to the submitter before review."
        ),
        owner="Product + Engineering",
        surface="Bill submission",
        confirming_signal="Duplicate exceptions caught pre-review rise while duplicate payments stay at zero",
        failure_mode="False positives on legitimate recurring invoices train submitters to dismiss the warning",
        effort="high",
    ),
}


def for_cause(root_cause: str) -> Intervention | None:
    """Return the candidate intervention for a root cause, if one is catalogued."""
    return INTERVENTIONS.get(root_cause)


def catalogue_rows() -> list[dict]:
    """Flat rows for display or export."""
    return [i.as_dict() for i in INTERVENTIONS.values()]
