# Milestones and context budget

This file exists for two reasons. It sequences the build so each step ships
something verifiable, and it keeps the cost of working on the repo low — for a
person picking it up cold, and for an AI agent whose context window is the real
constraint. `AGENTS.md` holds the working rules; this file holds the plan.

## The token problem, stated plainly

The dataset is 56 KB of CSV, roughly 15,000 tokens. The app is 577 lines. An
agent that opens both before answering a question about the ranking formula has
spent most of a cheap session on files it did not need. Three structural choices
prevent that:

1. **Logic lives in `src/`, never in `app.py`.** Every number the app shows is
   produced by a pure function that takes a DataFrame and returns a DataFrame or
   a dict. Changing the ranking means reading 248 lines of `analytics.py`, not
   577 lines of Streamlit layout.
2. **Tests are the inspection channel.** `tests/conftest.py` holds a six-row
   frame whose correct answers can be counted by hand. Verifying a change means
   running `pytest`, not printing a 300-row DataFrame into the transcript.
3. **Assumptions are centralised.** Every arguable number sits in
   `src/config.py` with a comment saying where it came from. Tuning the model is
   an 89-line read.

## Read cost by file

Open the fewest of these that answers the question.

| File | Lines | Read it when |
| --- | --- | --- |
| `src/config.py` | 89 | Changing any assumption, threshold or path |
| `src/interventions.py` | 105 | Editing the proposed upstream changes |
| `src/loader.py` | 135 | Changing schema rules or ingestion |
| `src/scenario.py` | 131 | Changing the projection or power maths |
| `src/analytics.py` | 248 | Changing the recurrence model or the ranking |
| `src/theme.py` | 87 | Changing chart colours or fonts |
| `app.py` | 577 | Changing layout, copy or controls only |
| `data/exceptions.csv` | 300 rows | Almost never: use `head -3`, or the test frame |

## Milestones

Each milestone names its exit check. A milestone is not done until that command
passes.

### M0 — Product frame · done
Write the PRD before any code, so the build has something to be judged against.
Separate what Ramp publicly documents from the untested hypothesis.
- Files: `PRD.md`
- Exit check: the PRD names a primary metric, an out-of-scope list, and the one
  thing that would prove the hypothesis wrong.

### M1 — Reproducible data · done
A fixed-seed synthetic generator, stdlib only, with the recurrence structure the
hypothesis depends on built in and visible.
- Files: `src/config.py`, `src/generate_data.py`
- Exit check: `python -m src.generate_data && pytest tests/test_generate_data.py`

### M2 — Strict ingestion · done
Validate before analysing. A malformed file must stop the load rather than
produce a plausible chart.
- Files: `src/loader.py`, `tests/test_loader.py`
- Exit check: `pytest tests/test_loader.py` — 15 cases including the CSV
  round-trip blank-date bug that the first implementation had.

### M3 — Recurrence model · done
Separate first occurrences from repeats, measure concentration, rank causes by
what a fix would be worth rather than by volume.
- Files: `src/analytics.py`, `tests/test_analytics.py`
- Exit check: `pytest tests/test_analytics.py`

### M4 — Scenario and power · done
Band every projection, weight it by fixability, and compute the sample size the
proposed experiment would actually need.
- Files: `src/scenario.py`, `tests/test_scenario.py`
- Exit check: `pytest tests/test_scenario.py`

### M5 — Interface · done
Five tabs: baseline, ranking, worklist, scenario, gap map. Brand-aligned, with
the honest limits on the page rather than in a footnote.
- Files: `app.py`, `src/theme.py`, `assets/ramp.css`, `.streamlit/config.toml`,
  `tests/test_app_smoke.py`
- Exit check: `pytest tests/test_app_smoke.py` — runs the real script through
  Streamlit's harness and fails on any uncaught exception.

### M6 — Reopen-weighted ranking · not started
The current prevention index optimises for reviewer minutes and therefore ranks
approval routing last, even though it has the highest reopen rate in the
dataset at 23%. A cause that keeps coming back after being closed is a different
kind of cost and the model does not see it. Add reopen rate as a fourth factor,
or publish a second ranking beside the first, and say which one a reviewer
should act on.
- Files: `src/config.py`, `src/analytics.py`, `tests/test_analytics.py`
- Exit check: a test asserting that the two rankings disagree on approval
  routing, plus a line in the app explaining which to trust.
- Why it is not done yet: adding a factor to a scoring model with no validation
  data makes the model look more sophisticated without making it more right.
  The honest order is interviews first, then the factor.

### M7 — AI-assisted root-cause classification · not started
`reviewer_note` already carries synthetic free text and `root_cause` is the
label. That is a labelled evaluation set. Add a classifier that proposes a cause
from a note, measure it against a keyword baseline, and route low-confidence
cases to a human.
- Files: new `src/classify.py`, `tests/test_classify.py`
- Exit check: accuracy and a confusion matrix against the keyword baseline, both
  printed by a script in the repo, with the abstention rate reported.
- Why it is not done yet: it is the most impressive-looking addition and the
  least evidence-backed. Nobody has confirmed that classifying causes is the
  bottleneck. Build it after M8 says it is.

### M8 — Validation with real operators · not started
Five interviews with AP admins or controllers. Ask whether these five causes are
the real ones, whether repeats feel like the problem, and what they would do
with the worklist. Replace the fixability priors with their answers.
- Files: `CASESTUDY.md` findings section, `src/config.py` priors
- Exit check: every prior in `FIXABILITY_PRIOR` cites an interview rather than
  the author's estimate.

### M9 — Real data foundation: Ramp's own APIs · not started
Ramp's Audit Logs API (`GET /developer/v1/audit-logs/events`) returns
`actor_type` and `agent_details.agent_name` on every event, verified against
the live OpenAPI schema — a real foundation for pulling exception history
instead of generating it. Two limits came out of the same schema check: the
event-type enum's `Exception` family is policy-limit overrides, not invoice
exceptions, and the Bills API carries no root-cause or review-time field. A
real integration would read `GET /developer/v1/bills`, `GET /developer/v1/vendors`
and the audit log, then infer recurrence from proxies — repeated
`Violation from rule` events on the same vendor, repeated submission-policy
exemptions — rather than read a `root_cause` column that doesn't exist.
- Files: new `src/ramp_client.py` (read-only API client), new `src/infer.py`
  (proxy-based recurrence signal from audit events), `ASSUMPTIONS.md` §3 for
  the verified schema fields
- Exit check: a script that takes exported Bills/Vendors/Audit-log JSON (not
  live credentials — this project has no Ramp customer access) and produces
  the same `root_cause_table` shape `analytics.py` already outputs from the
  synthetic CSV, so the rest of the app is unchanged.
- Why it is not done yet: it requires authorized customer API access this
  project doesn't have, and building an inference layer before confirming
  with M8 that recurrence is the right lens would be solving a problem no
  operator has validated. Sequenced after M8 on purpose.

## Status

| Milestone | State | Verified by |
| --- | --- | --- |
| M0 Product frame | done | `PRD.md` |
| M1 Reproducible data | done | 8 tests |
| M2 Strict ingestion | done | 15 tests |
| M3 Recurrence model | done | 16 tests, plus 5 on the intervention catalogue |
| M4 Scenario and power | done | 9 tests |
| M5 Interface | done | 5 app tests |
| M6 Reopen-weighted ranking | not started | — |
| M7 AI root-cause assist | not started | — |
| M8 Operator validation | not started | — |
| M9 Real API data foundation | not started | — |

58 tests pass. Run `make test` to confirm.
