"""Every ranked cause needs a named change, an owner and a way to fail.
A ranking with no proposed action is a dashboard, not a product."""

from __future__ import annotations

from src import interventions
from src.config import FIXABILITY_PRIOR, ROOT_CAUSES


def test_every_root_cause_has_a_catalogued_intervention():
    assert set(interventions.INTERVENTIONS) == set(ROOT_CAUSES)


def test_every_cause_with_a_fixability_prior_has_an_intervention():
    assert set(FIXABILITY_PRIOR) == set(interventions.INTERVENTIONS)


def test_each_intervention_names_an_owner_a_signal_and_a_failure_mode():
    for iv in interventions.INTERVENTIONS.values():
        assert iv.owner and iv.confirming_signal and iv.failure_mode
        assert iv.effort in {"low", "medium", "high"}


def test_unknown_cause_returns_none_rather_than_guessing():
    assert interventions.for_cause("cosmic_rays") is None


def test_catalogue_rows_are_flat_and_exportable():
    rows = interventions.catalogue_rows()
    assert len(rows) == len(interventions.INTERVENTIONS)
    assert all(isinstance(v, str) for row in rows for v in row.values())
