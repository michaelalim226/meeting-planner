"""UI tests for app.py via streamlit.testing.v1.AppTest (SPEC.md §6 / F6)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parent / "app.py"
DEFAULT_TIMEOUT = 15


def run_app() -> AppTest:
    return AppTest.from_file(str(APP_PATH)).run(timeout=DEFAULT_TIMEOUT)


def test_no_warning_when_overlap_exists():
    at = run_app()
    assert not at.exception
    assert str(at.metric[1].value) == "5.0 h"
    assert len(at.warning) == 0


def test_warning_when_no_overlap_tokyo_london():
    at = run_app()
    at.sidebar.multiselect[0].set_value(["Tokyo", "London"]).run()
    assert not at.exception
    assert str(at.metric[1].value) == "0.0 h"
    assert len(at.warning) == 1
    assert "No overlapping hours" in at.warning[0].value
    assert at.sidebar.caption[0].value == "2 of 36 cities selected"
