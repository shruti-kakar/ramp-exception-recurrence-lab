"""End-to-end check that the app actually runs.

Unit tests on pure functions pass happily while the UI is broken, so this
executes the real script through Streamlit's test harness and fails on any
uncaught exception. It is the one test that would catch a bad column reference
or a chart encoding that pandas rejects.
"""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest  # noqa: E402

TIMEOUT = 60


@pytest.fixture(scope="module")
def app() -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT).run()
    return at


def test_app_runs_without_exceptions(app):
    assert not app.exception, [e.value for e in app.exception]


def test_headline_metrics_render(app):
    labels = [m.label for m in app.metric]
    assert "Exceptions" in labels
    assert "Repeat share" in labels


def test_every_tab_renders(app):
    titles = [t.label for t in app.tabs] if hasattr(app, "tabs") else []
    # Older Streamlit versions expose tabs differently; fall back to body text.
    rendered = " ".join(str(m.value) for m in app.markdown)
    for expected in ("Exception Recurrence Lab", "Prevention index", "Recurring vendor"):
        assert expected in rendered or expected in " ".join(titles)


def test_moving_the_prevention_slider_changes_the_projection():
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT).run()
    at.slider[0].set_value(0).run()
    zero = next(m for m in at.metric if m.label == "Hours avoided / month").value
    at.slider[0].set_value(30).run()
    thirty = next(m for m in at.metric if m.label == "Hours avoided / month").value
    assert float(zero) == 0.0
    assert float(thirty) > 0.0
    assert not at.exception


def test_clearing_every_filter_warns_instead_of_crashing():
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT).run()
    at.multiselect[0].set_value([]).run()
    assert not at.exception
    assert any("No exceptions match" in str(w.value) for w in at.warning)
