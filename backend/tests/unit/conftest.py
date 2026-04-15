"""Auto-mark all tests in this directory as unit tests."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
