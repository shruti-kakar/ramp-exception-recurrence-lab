# Case study 01 — Exception Recurrence Lab

**Area:** Ramp Bill Pay · **Discipline:** Product Operations · **Date:** 26 October 2026
**Author:** Shruti Kakar · **Status:** independent, unofficial, synthetic data only

A short account of how I looked for a gap in a product I do not work on, what I
built to test whether the gap mattered, and the two findings that argued against
my own pitch.

---

## 1. How I looked for the gap

I started from a constraint rather than an idea: I have no access to Ramp's
internals, so anything I claim has to be falsifiable from public material and
honest about what it cannot see.

So I read Ramp's public help centre and marketing pages and wrote down every
exception-handling capability they describe. Invoice field extraction. A
needs-review surface. AI approval recommendations. Configurable submission
policies. Approval routing. Audit history. That list is the reason I did not
build an invoice exception detector: it already exists, and rebuilding a
documented feature is a demo, not a product argument.

What I could not find documented was anything that treats an exception's
**recurrence** as the unit of work. Every surface I found is organised around
closing the case in front of you. None of the public material describes
distinguishing the first time a vendor hits a problem from the eleventh, which
is the distinction that decides whether you resolve or prevent.

That became the hypothesis. I want to be precise about its status: absence from
public documentation is not evidence of absence from the product. It is a
reasonable place to start a conversation, and nothing more.

## 2. The hypothesis

> Operations teams spend a measurable share of review effort on exceptions they
> have already seen from the same vendor for the same reason. If that share is
> both large and concentrated, ranking root causes by *preventability* rather
> than by volume changes which fix a team ships first.

Two conditions have to hold for this to be worth building. The repeat share has
to be large, and the repeats have to concentrate in a short list of vendors. If
repeats were rare, or spread evenly across hundreds of vendors, the thesis fails
and the right answer is to keep improving case resolution.

## 3. What I built

A Python and Streamlit application over a reproducible 300-record synthetic
dataset: six months, 36 vendors, 7,962 bills processed, five root causes.

The modelling decisions are the substance, and each is arguable on purpose.

**Only repeats are addressable.** A recurrence cluster is one vendor and one root
cause. The first occurrence in a cluster is excluded from the addressable pool,
because no feedback loop can prevent a problem the first time it is ever seen.
This single rule is what separates the tool from a category counter, and it cuts
the apparent opportunity by more than a third.

**Concentrated causes are cheaper to fix.** For each cause I measure the share of
its repeat hours sitting with its three heaviest vendors. A cause driven by three
vendors is a conversation. The same hours spread across thirty vendors is a
platform change.

**Causes differ in how fixable they are at all.** A required-field rule at
submission can remove most missing-PO cases. Nothing resembling a form rule will
remove duplicate invoices, which need matching. That difference lives in a
documented prior per cause, and it is the weakest number in the project.

The ranking multiplies the three: addressable repeat hours per month ×
concentration × fixability. The naive volume ranking is kept on screen beside it,
because where the two agree, this tool adds nothing.

## 4. What the prototype found

### The repeat share is large and highly concentrated

| Measure | Value |
| --- | --- |
| Exceptions in the window | 300 |
| Share that are repeat occurrences | 63% |
| Total reviewer hours | 118 |
| Addressable reviewer hours (repeats only) | 75 |
| Recurring vendor/cause pairs | 51 of 110 |
| Share of repeat hours in the top 10 pairs | 73% |
| Repeat exceptions per 1,000 bills | 23.9 |

Both conditions hold in this dataset, which is the expected result: I generated
the data with that structure deliberately, and the generator says so in its
docstring. The finding is not that recurrence is concentrated in the real world.
The finding is that *if* it is, the worklist is ten vendor conversations rather
than a platform programme — and that is a cheap thing to check against real data
before committing to anything.

### The ranking disagrees with the volume ranking, and the disagreement is the point

| Rank | Root cause | Repeat h/month | Concentration | Fixability | Index | Rank by volume |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Missing PO | 3.74 | 67% | 0.80 | 2.02 | 1 |
| 2 | Vendor details | 2.65 | 85% | 0.70 | 1.58 | 3 |
| 3 | GL coding | 2.27 | 80% | 0.65 | 1.18 | 2 |
| 4 | Duplicate invoice | 3.15 | 84% | 0.35 | 0.93 | 4 |
| 5 | Approval routing | 0.77 | 92% | 0.55 | 0.39 | 5 |

Duplicate invoices are the second-largest addressable pool at 3.15 reviewer hours
a month, ahead of GL coding and vendor details. They rank fourth to act on,
because the upstream control is genuinely hard. Vendor details and GL coding swap
places. A team working purely from a volume report would start in the wrong
place twice over.

### Finding that argued against the pitch: the labour-savings case does not survive contact with the arithmetic

Total addressable effort is 12.6 reviewer hours a month. At a 10% prevention
assumption that is 1.3 hours a month, about **$724 a year** at a loaded reviewer
cost of $48 an hour. For one mid-market accounts-payable team, that is not a
business case. It is a rounding error.

I built the model expecting it to support an efficiency pitch and it does not. So
the pitch has to change rather than the number. The defensible versions are:

- **Platform aggregation.** The same analysis across a customer base is a product
  insight about which submission controls to build, not a per-customer saving.
- **Cycle time, not headcount.** Median time to resolution is 23 hours and the
  reopen rate is 12%. Bills that stall and bills that come back are the costs
  that an AP team actually feels.
- **Risk.** Duplicate invoices and vendor banking details are fraud-adjacent.
  Their value is not measured in reviewer minutes.

Any version of this project that leads with hours saved at a single customer is
overstating what the model supports.

### Finding that broke the plan: a 30-day pilot cannot measure the primary metric

My own PRD proposed a four-week experiment measuring recurrence per 1,000 bills.
I wrote the sample-size calculation into the tool to check it, and the plan does
not survive.

| Relative improvement to detect | Bills per arm | Months of volume per arm |
| --- | --- | --- |
| 20% | 14,483 | 10.9 |
| 30% | 6,087 | 4.6 |
| 50% | 1,938 | 1.5 |

At 80% power and a 5% significance level, detecting a 20% improvement in the
recurrence rate needs about 14,500 bills per arm. This team processes roughly
1,300 bills a month. One arm would take eleven months to fill. Even a 50%
improvement — implausibly large — needs six weeks.

The experiment has to change, in one of three ways: pool several customers into
one study, pick a cohort an order of magnitude larger, or judge the 30-day window
on a leading indicator such as the share of exceptions caught before review and
read recurrence only later. I would choose the third, and I would say up front
that the 30-day result is directional.

This is the finding I would lead with in an interview. Not because the maths is
hard, but because writing the power check into the tool is what turned a
plausible-sounding plan into a wrong one, before anyone spent a month on it.

## 5. What my own model gets wrong

**The prevention index cannot see reopens.** Approval routing has the highest
reopen rate in the dataset at 23%, nearly double every other cause, and the model
ranks it last because it is cheap in reviewer minutes. A cause that keeps coming
back after being closed is a different kind of cost and my scoring function is
blind to it. It is logged as M6 in `MILESTONES.md` and deliberately not fixed:
adding a fourth factor to a scoring model that no operator has validated makes it
look more sophisticated without making it more right.

**The fixability priors are my estimates.** Five numbers between 0.35 and 0.80,
sourced from my own judgement about AP workflows. They move the ranking. Until
five operators have argued with them they are the softest part of the project,
which is why they sit in one named dictionary in `src/config.py` rather than
buried in the scoring code.

**Synthetic data is tidy and real exception data is not.** Every record here has
exactly one root cause. Real cases are ambiguous, multi-cause and sometimes
mislabelled by whoever closed them. A real version needs multi-label support and
a record of how each cause was validated.

**Root cause is a label, not a diagnosis.** The dataset treats the cause as
known. In practice someone inferred it from a symptom, and the inference can be
wrong in a way that quietly misdirects every number downstream.

## 6. What I would do next, in order

1. **Five operator interviews.** Are these the real causes? Does recurrence feel
   like the problem, or is it cycle time? What would you do with the worklist?
   Replace my priors with their answers. Nothing else should move first.
2. **Re-rank on whatever they say the cost actually is.** If they say reopens, the
   model gets a reopen factor and the ranking changes.
3. **Rewrite the experiment** around a leading indicator, with the power
   calculation shown rather than assumed.
4. **Then, and only then, the AI layer.** `reviewer_note` plus `root_cause` is
   already a labelled evaluation set, so a classifier can be measured against a
   keyword baseline rather than demoed. It is the most impressive-looking
   addition and the least evidence-backed, so it goes last.

## 7. What this is not

No Ramp integration, no authentication, no real customer data, no AI inference,
no measured savings. Every figure in this document comes from synthetic data
generated by `src/generate_data.py` with a fixed seed, and the generator builds in
the recurrence pattern the app then finds. The contribution is the method and the
two findings that cut against the original pitch, not the numbers.

Nothing here uses or refers to any proprietary information from a current or
former employer.

## Reproducing every number in this document

```
make install
make data
make test
make app
```

`make test` runs 58 tests. The figures in sections 4 and 5 come from the bundled
seed, so they will match exactly.
