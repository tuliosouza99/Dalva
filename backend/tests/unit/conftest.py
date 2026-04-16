"""Auto-mark all tests in this directory as unit tests."""

from unittest.mock import MagicMock

import httpx
import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


def _mock_response(status_code=200, json_data=None, raise_on_status=True):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if raise_on_status and status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            str(status_code), request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _mock_worker(pending=0, errors=None, drain_result=True):
    w = MagicMock()
    w.pending = pending
    w.drain_with_progress.return_value = drain_result
    w.clear_errors.return_value = errors or []
    return w


@pytest.fixture
def mock_response():
    return _mock_response


@pytest.fixture
def mock_worker():
    return _mock_worker
