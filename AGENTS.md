# AGENTS.md

Working rules for this repository. Written to be short on purpose: this file is
read into context on every session, so every line in it costs tokens on every
task. `MILESTONES.md` holds the plan and the per-file read costs.

## Commands

```bash
make install   # .venv + dependencies
make data      # regenerate the fixed-seed dataset
make test      # 58 tests, under a second
make app       # streamlit run app.py
```

Always use `.venv/bin/python`, never the system Python. The repo targets Python
3.9, so every module starts with `from __future__ import annotations`.

## Where things live

Logic is in `src/`. `app.py` is layout and copy only, and it is the most
expensive file in the repo to read at 577 lines. If a change is about a number,
it does not belong there.

| Change | File to open |
| --- | --- |
| An assumption, threshold, path or prior | `src/config.py` |
| The recurrence model or the ranking | `src/analytics.py` |
| Schema rules or ingestion | `src/loader.py` |
| Projections or pilot sizing | `src/scenario.py` |
| A proposed upstream change | `src/interventions.py` |
| Colours, fonts, chart defaults | `src/theme.py` and `assets/ramp.css` (both) |
| Layout, copy, controls | `app.py` |

## Token discipline

1. **Never read `data/exceptions.csv`.** It is 300 rows and about 15,000 tokens.
   Use `head -3` for the shape, or the six-row frame in `tests/conftest.py` whose
   correct answers can be counted by hand.
2. **Never print a DataFrame into the transcript to check a change.** Write or
   run a test instead. A test is cheaper than a table and it stays.
3. **Open the narrowest file that answers the question.** The table above exists
   so nobody has to grep for where the ranking lives.
4. **Do not read `app.py` to change a calculation.** It contains none.
5. **One milestone per session.** `MILESTONES.md` names each one's read set and
   its exit check.

## Invariants

Break any of these and the project stops being honest, which is the only thing
it has going for it.

- **First occurrences are never addressable.** `is_repeat` is false at
  `occurrence == 1` and every effort pool excludes those rows. This is the
  product argument; it is not a tunable.
- **Every assumption lives in `src/config.py` with a comment saying where it came
  from.** No magic numbers in analytics, scenario or app code.
- **Every projection carries a band and a disclaimer.** `scenario.project`
  returns low, point, high and `basis`. Do not add a code path that returns a
  bare point estimate.
- **No figure may be presented as measured.** Synthetic, projected and assumed
  are labelled as such in the UI, not in a footnote.
- **The loader fails loudly.** A schema problem stops the load. Never widen
  `validate` to let a malformed file through.
- **Rates need a denominator.** Per-1,000-bill metrics return `None` when no
  volume file is loaded. Never substitute the exception count.
- **No real company, customer or employer data.** Synthetic only, and no
  proprietary information from any current or former employer.
- **No claim that Ramp lacks a capability.** Public documentation is evidence
  about documentation, nothing more. Keep the hedge in the copy.

## Conventions

- Pure functions in `src/`: take a DataFrame, return a DataFrame or a dict. No
  Streamlit imports outside `app.py` and `src/theme.py`.
- Analytics functions accept either a raw or a derived frame and call
  `add_derived` themselves if the `is_repeat` column is missing. Keep that.
- Comments explain *why a number is what it is*, not what the line does. If a
  comment restates the code, delete it.
- Test names are sentences describing the behaviour being protected.
- `tests/test_app_smoke.py` runs the real app through Streamlit's harness. It is
  the only test that catches a bad column reference in the UI, so keep it green.

## Before finishing a change

```bash
make test
```

If the change touched `app.py` or `src/theme.py`, confirm
`tests/test_app_smoke.py` passed — unit tests stay green while the UI is broken.
If it touched a number that appears in `CASESTUDY.md` or `README.md`, update both
documents. Stale figures in the write-up are worse than no figures.
