"""Smoke test: package imports cleanly. Replace/extend as modules land."""

import docket


def test_version_is_set() -> None:
    assert docket.__version__
