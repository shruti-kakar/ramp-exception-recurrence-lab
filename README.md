# Exception Recurrence Lab

**From resolving exceptions to preventing them.**

An independent product-operations case study on Ramp Bill Pay. It asks a single
question: once an invoice exception has been resolved, what makes the same
exception stop happening — and which upstream fix is worth running an experiment
on first?

Not affiliated with Ramp. All data is synthetic. No figure in this project is a
measured result.

```
make install && make data && make test && make app
```

---

## Why this and not an exception detector

Ramp's public documentation already describes invoice field extraction, a
needs-review surface, AI approval recommendations, configurable submission
policies, approval routing and audit history. Building another exception
detector would rebuild a documented feature.

What I could not find in public material is anything that treats an exception's
**recurrence** as the unit of work — the difference between the first time a
vendor hits a problem and the eleventh. That distinction is what decides whether
a team resolves cases or prevents them, and it is the whole subject of this
project.

Absence from public docs is not evidence of absence from the product. This is a
conversation starter, not a claim about Ramp's internals.

## What it does

Five views over a reproducible synthetic exception history.

| View | What it answers |
| --- | --- |
| **Baseline** | How much review effort is spent on problems already seen, and is the repeat rate moving |
| **Where to fix** | Which root cause is worth fixing, ranked by preventability rather than volume, with a named upstream change for each |
| **Worklist** | Which specific vendor and cause pairs keep recurring, down to the individual cases |
| **Prevention scenario** | What a prevention assumption would be worth, banded, and whether a pilot could actually detect it |
| **Gap map** | What Ramp publicly documents, what this prototype adds, and what it deliberately does not do |

## The modelling decision that matters

A **recurrence cluster** is one vendor plus one root cause. The first occurrence
in a cluster is excluded from the addressable pool, because no feedback loop can
prevent a problem the first time it is ever seen. In the bundled dataset that
rule cuts 118 reviewer hours down to 75 addressable ones.

Causes are then ranked by a **prevention index**:

```
prevention index = addressable repeat hours per month
                 x vendor concentration      (share of repeat hours in the top 3 vendors)
                 x fixability prior           (how much an upstream control could remove)
```

The volume ranking stays on screen next to it. Where the two agree, this tool
adds nothing; the disagreements are the only place it earns its keep.

## Two findings that argued against the pitch

**The labour-savings case does not hold at single-customer scale.** Total
addressable effort is 12.6 reviewer hours a month. At a 10% prevention
assumption that is about $724 a year. The case has to be made on cycle time,
reopen rate, fraud exposure or platform-wide insight — not on hours saved.

**A 30-day pilot cannot measure the primary metric.** Detecting a 20%
improvement in the recurrence rate at 80% power needs roughly 14,500 bills per
arm. The modelled team processes 1,300 bills a month, so one arm would take
eleven months to fill. The power check is built into the app, and it is what
turned my own proposed experiment into a wrong one before anyone ran it.

`CASESTUDY.md` has the full reasoning, including what the model gets wrong.

## Run it

Requires Python 3.9 or newer.

```bash
make install      # create .venv and install dependencies
make data         # generate the synthetic dataset, fixed seed
make test         # 58 tests
make app          # open the Streamlit app
```

Without `make`:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m src.generate_data
.venv/bin/python -m pytest -q
.venv/bin/streamlit run app.py
```

The generated CSVs are gitignored. If they are missing, the app rebuilds them on
first load, so `streamlit run app.py` works from a fresh clone and on a hosted
deployment with no build step.

Bring your own CSV through the sidebar uploader. The required columns are the
ten in `src/config.py`; the loader reports every schema problem at once rather
than failing on the first.

## Deploy

`app.py` runs on Streamlit Community Cloud with no configuration: point it at
this repository, set the entrypoint to `app.py`, and the dataset regenerates on
first load. The app reads no secrets and makes no network calls.

## Repository map

| Path | Purpose |
| --- | --- |
| `PRD.md` | Product requirements, written before any code |
| `CASESTUDY.md` | Findings, including what the model gets wrong |
| `MILESTONES.md` | Build sequence, remaining work, and the context budget |
| `DESIGN.md` | Visual system, and why Ramp's real typefaces are not bundled |
| `AGENTS.md` | Working rules for anyone or anything editing this repo |
| `src/config.py` | Every arguable assumption, each with its source |
| `src/generate_data.py` | Fixed-seed synthetic data, stdlib only |
| `src/loader.py` | Strict CSV ingestion and schema validation |
| `src/analytics.py` | Recurrence model, concentration, prevention ranking |
| `src/scenario.py` | Banded projections and pilot sample size |
| `src/interventions.py` | Candidate upstream change per root cause |
| `app.py` | Streamlit interface |
| `tests/` | 58 tests, including an end-to-end app run |
| `assets/ramp.css` | Design tokens, mirrored in `src/theme.py` |

## Limits

No Ramp integration. No authentication. No real customer data. No AI inference.
No measured savings. The dataset is generated with a recurrence pattern built in,
so the pattern the app finds is the one it was given. The contribution is the
method and the findings that cut against the original pitch.

Nothing here uses or refers to proprietary information from any current or former
employer.
