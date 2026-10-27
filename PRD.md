# PRD: Exception Recurrence Lab
**Date:** 26 October 2026  
**Author:** Shruti Kakar  
**Status:** Independent, unofficial Ramp Product Operations case study and working prototype

## Executive summary
**Product question:** Once an invoice/payment exception is identified or reviewed, how can operations teams identify repeated upstream causes and reduce future recurrence? Ramp publicly documents AI approval intelligence, Bill Pay review/payment queues, configurable policies, and audit trails. This PRD tests an additional **root-cause learning loop**, not the unsupported claim that Ramp lacks existing exception handling or internal reporting.

## Why this problem
My work validating exception-heavy financial workflows at JPMorgan showed me that closing individual exceptions is different from fixing recurring causes. I wanted to investigate whether that distinction could inform a Bill Pay product-operations workflow at Ramp. This project uses entirely synthetic data and makes no claim to represent JPMorgan or Ramp systems.

## Target users and jobs
- Ramp Bill Pay Product Ops: prioritize recurring friction and size workflow improvements.
- AP admin/controller: spot repeated missing PO/vendor/coding or routing issues and decide what to change.
- Product/Engineering: evaluate improvement hypotheses with auditable examples and clear measurements.

## Known public capabilities vs hypothesis
Verified directly against live Ramp pages, not assumed: a Needs Review queue triages payments needing intervention ([support.ramp.com/managing-bills-and-payments-on-bill-pay](https://support.ramp.com/managing-bills-and-payments-on-bill-pay)); an AP Review Agent checks bills against policy, contracts, POs and supporting documents, editable through Ask Ramp ([support.ramp.com/ap-agents-available-in-ramp-bill-pay](https://support.ramp.com/ap-agents-available-in-ramp-bill-pay)); Smart OCR and auto-coding extract invoice data and learn GL coding from corrections; submission policies validate required fields and record overrides; and an Audit Logs API (`GET /developer/v1/audit-logs/events`, confirmed against the live schema) records `actor_type` and `agent_details.agent_name` on every event — a real foundation for a recurrence analysis Ramp doesn't yet expose.

**Refined hypothesis, narrowed after that research:** no public Ramp page shows all four of (1) grouping historical exceptions into recurring root-cause patterns, (2) estimating which patterns create the most avoidable work, (3) recommending an upstream change per pattern, and (4) tracking whether that change reduced recurrence, together, as one feedback loop. Any one or two of those four may already exist privately. Confirm with actual Ramp users before advocating a product change. Full sourcing and the verified API schema findings are in `ASSUMPTIONS.md` and `CASESTUDY.md`.

## In scope (implemented in prototype)
- CSV ingestion with schema checks; reproducible synthetic exception records.
- Root-cause breakdown ranked by reviewer minutes, count, vendors affected, value associated with cases.
- Filters and case-level inspection via root-cause selection.
- Suggested prevention experiments for common categories (not automated policy changes).
- Counterfactual slider estimating review time avoided if repeat cases declined by a chosen percentage.
- CSV summary export and reproducible unit tests.

## Out of scope
Ramp API access, authentication, production workflow, AI inference, actual invoice duplicate detection, payment execution, policy writes, causal savings claims, real customer data.

## Primary workflow
1. Open app; see baseline metrics.
2. Find top root cause by review effort.
3. Inspect individual cases and the suggested intervention.
4. Change a hypothetical prevention assumption; inspect scenario estimate, clearly labeled.
5. Export and describe a 30-day pilot to test whether the intervention really works.

## Data model
`invoice_id`, `vendor`, `amount`, `exception_type`, `status`, `opened_at`, `resolved_at`, `root_cause`, `owner`, `minutes_spent`. All sample cases are simulated. In real operations, distinguish risk signals from proven root causes and record how each root cause was validated.

## Success metrics for a real pilot (not yet observed)
- Primary: repeat exception rate per 1,000 bills by root cause, adjusted for volume.
- Secondary: median hands-on handling minutes; median time to resolution; reopen rate; false routing rate; reviewer satisfaction.
- Guardrail: missed high-risk exceptions, unexpected policy bypasses, increased payment delays.
- Compare a pre-intervention baseline to a similar post-intervention window or control cohort; use confidence ranges where feasible.
- Thresholds should be defined only after interviews and baseline analysis, not invented as achieved results.

## 30-day experiment proposal
- Week 1: 3-5 AP/operator interviews; validate categorization and get baseline exception volume.
- Week 2: instrument exception cause tags, reviewer time, and reopen events in a pilot workflow.
- Week 3: ship one upstream change, such as improved PO-required submission guidance, to a small cohort.
- Week 4: compare recurrence and review effort with baseline/control, document misses, and recommend launch, iterate, or stop.

## Risks and safeguards
- Root causes inferred from symptoms may be wrong: reviewers must validate tags.
- Synthetic data creates tidy categories: real data needs ambiguous/multi-cause labeling.
- Savings slider is a scenario: no projection should be labeled observed impact.
- Avoid all JPMorgan and Ramp proprietary information; comply with employer outside-activity rules.
- No evidence from public docs that this precise tool does not already exist internally.

## Shipping package
Public GitHub repo (upload manually), reproducible `make demo`, tests, screenshots and 2-minute walkthrough, and one-page hiring-manager memo. Apply for the Ramp role while it remains open rather than waiting for this prototype.
