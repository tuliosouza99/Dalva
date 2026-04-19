"""Tests for SyncWorker background request processing."""

from __future__ import annotations

import warnings
from unittest.mock import MagicMock, patch

import httpx
import pytest

from dalva.sdk.worker import PendingRequest, SyncWorker


@pytest.fixture
def mock_httpx_client():
    with patch("dalva.sdk.worker.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


def _ok_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status.return_value = None
    return resp


def _error_response(status_code, detail="error"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"detail": detail}
    return resp


class TestPendingRequest:
    def test_can_retry_true(self):
        req = PendingRequest(method="POST", url="/test")
        assert req.can_retry is True

    def test_can_retry_false_at_max(self):
        req = PendingRequest(method="POST", url="/test", max_retries=3, retry_count=3)
        assert req.can_retry is False

    def test_can_retry_true_below_max(self):
        req = PendingRequest(method="POST", url="/test", max_retries=3, retry_count=2)
        assert req.can_retry is True


class TestSyncWorkerEnqueueAndDrain:
    def test_enqueue_and_drain(self, mock_httpx_client):
        mock_httpx_client.post.return_value = _ok_response()
        worker = SyncWorker("http://localhost:8000", max_queue_size=10)

        req = PendingRequest(method="POST", url="/test", payload={"key": "val"})
        worker.enqueue(req)
        drained = worker.drain(timeout=5)

        assert drained is True
        assert worker.errors == []
        mock_httpx_client.post.assert_called_once_with("/test", json={"key": "val"})
        worker.stop()

    def test_drain_empty_queue(self, mock_httpx_client):
        worker = SyncWorker("http://localhost:8000", max_queue_size=10)
        drained = worker.drain(timeout=2)
        assert drained is True
        worker.stop()

    def test_multiple_requests_processed_in_order(self, mock_httpx_client):
        mock_httpx_client.post.return_value = _ok_response()
        worker = SyncWorker("http://localhost:8000", max_queue_size=100)

        for i in range(5):
            worker.enqueue(
                PendingRequest(method="POST", url=f"/test/{i}", payload={"i": i})
            )

        drained = worker.drain(timeout=5)
        assert drained is True

        calls = mock_httpx_client.post.call_args_list
        assert len(calls) == 5
        for i, call in enumerate(calls):
            assert call[0][0] == f"/test/{i}"

        worker.stop()

    def test_queue_size_tracking(self, mock_httpx_client):
        mock_httpx_client.post.return_value = _ok_response()
        worker = SyncWorker("http://localhost:8000", max_queue_size=100)

        worker.enqueue(PendingRequest(method="POST", url="/a"))
        worker.enqueue(PendingRequest(method="POST", url="/b"))
        assert worker.queue_size == 2

        worker.drain(timeout=5)
        assert worker.queue_size == 0
        worker.stop()


class TestSyncWorkerRetry:
    def test_retries_on_network_error(self, mock_httpx_client):
        mock_httpx_client.post.side_effect = [
            httpx.ConnectError("connection refused"),
            _ok_response(),
        ]

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=3,
            base_backoff=0.01,
            max_backoff=0.1,
        )

        req = PendingRequest(method="POST", url="/test", payload={"x": 1})
        worker.enqueue(req)
        drained = worker.drain(timeout=10)

        assert drained is True
        assert worker.errors == []
        assert mock_httpx_client.post.call_count == 2
        worker.stop()

    def test_stores_error_after_max_retries(self, mock_httpx_client):
        mock_httpx_client.post.side_effect = httpx.ConnectError("connection refused")

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=2,
            base_backoff=0.01,
            max_backoff=0.1,
        )

        req = PendingRequest(method="POST", url="/test")
        worker.enqueue(req)
        drained = worker.drain(timeout=10)

        assert drained is True
        errors = worker.errors
        assert len(errors) == 1
        assert isinstance(errors[0][1], httpx.ConnectError)
        assert mock_httpx_client.post.call_count == 3  # 1 initial + 2 retries
        worker.stop()

    def test_retries_on_5xx(self, mock_httpx_client):
        error_resp = _error_response(500, "internal error")
        mock_httpx_client.post.side_effect = [
            httpx.HTTPStatusError("500", request=MagicMock(), response=error_resp),
            _ok_response(),
        ]

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=3,
            base_backoff=0.01,
            max_backoff=0.1,
        )

        req = PendingRequest(method="POST", url="/test")
        worker.enqueue(req)
        drained = worker.drain(timeout=10)

        assert drained is True
        assert worker.errors == []
        assert mock_httpx_client.post.call_count == 2
        worker.stop()

    def test_4xx_stored_immediately_no_retry(self, mock_httpx_client):
        error_resp = _error_response(400, "bad request")
        mock_httpx_client.post.side_effect = httpx.HTTPStatusError(
            "400", request=MagicMock(), response=error_resp
        )

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=3,
            base_backoff=0.01,
        )

        req = PendingRequest(method="POST", url="/test")
        worker.enqueue(req)
        drained = worker.drain(timeout=5)

        assert drained is True
        errors = worker.errors
        assert len(errors) == 1
        assert mock_httpx_client.post.call_count == 1
        worker.stop()


class TestSyncWorkerConflictHandling:
    def test_409_drops_request_with_warning(self, mock_httpx_client):
        conflict_resp = _error_response(409, "duplicate metric")
        mock_httpx_client.post.side_effect = httpx.HTTPStatusError(
            "409", request=MagicMock(), response=conflict_resp
        )

        worker = SyncWorker("http://localhost:8000", max_queue_size=10)

        req = PendingRequest(method="POST", url="/api/runs/1/log")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            worker.enqueue(req)
            drained = worker.drain(timeout=5)

        assert drained is True
        assert worker.errors == []
        conflict_warnings = [x for x in w if "Conflict (409)" in str(x.message)]
        assert len(conflict_warnings) == 1
        worker.stop()


class TestSyncWorkerErrors:
    def test_clear_errors(self, mock_httpx_client):
        mock_httpx_client.post.side_effect = httpx.ConnectError("fail")

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=0,
        )

        worker.enqueue(PendingRequest(method="POST", url="/a"))
        worker.drain(timeout=5)

        assert len(worker.errors) == 1
        cleared = worker.clear_errors()
        assert len(cleared) == 1
        assert len(worker.errors) == 0
        worker.stop()


class TestSyncWorkerStop:
    def test_stop_cleans_up(self, mock_httpx_client):
        mock_httpx_client.post.return_value = _ok_response()
        worker = SyncWorker("http://localhost:8000")

        worker.enqueue(PendingRequest(method="POST", url="/test"))
        worker.drain(timeout=5)
        worker.stop(timeout=5)

        mock_httpx_client.close.assert_called_once()

    def test_enqueue_blocks_when_full(self, mock_httpx_client):
        import threading

        picked_up = threading.Event()
        block_release = threading.Event()

        def slow_post(*args, **kwargs):
            picked_up.set()
            block_release.wait(timeout=5)
            return _ok_response()

        mock_httpx_client.post.side_effect = slow_post
        worker = SyncWorker("http://localhost:8000", max_queue_size=2)

        req = PendingRequest(method="POST", url="/test")
        worker.enqueue(req)
        picked_up.wait(timeout=2)

        worker.enqueue(req)
        worker.enqueue(req)

        with pytest.raises(ConnectionError, match="Worker queue full"):
            worker.enqueue(req, timeout=0.1)

        block_release.set()
        worker.drain(timeout=5)
        worker.stop()


class TestSyncWorkerWAL:
    def test_wal_appended_on_process(self, mock_httpx_client, tmp_path):
        from dalva.sdk.wal import WALManager

        mock_httpx_client.post.return_value = _ok_response()
        wal = WALManager("run", 1, outbox_dir=tmp_path / "outbox")
        worker = SyncWorker("http://localhost:8000", wal_manager=wal)

        worker.enqueue(
            PendingRequest(
                method="POST",
                url="/api/runs/1/log",
                payload={"metrics": {"loss": 0.5}, "step": 0},
                batch_key="run:1",
            )
        )
        worker.drain(timeout=5)

        entries = WALManager.read(wal.path)
        assert len(entries) == 1
        assert entries[0]["url"] == "/api/runs/1/log"
        assert entries[0]["payload"] == {"metrics": {"loss": 0.5}, "step": 0}
        worker.stop()

    def test_wal_appends_all_batch_items(self, mock_httpx_client, tmp_path):
        from dalva.sdk.wal import WALManager

        mock_httpx_client.post.return_value = _ok_response()
        wal = WALManager("run", 1, outbox_dir=tmp_path / "outbox")
        worker = SyncWorker("http://localhost:8000", wal_manager=wal, batch_size=100)

        for i in range(5):
            worker.enqueue(
                PendingRequest(
                    method="POST",
                    url="/api/runs/1/log",
                    payload={"metrics": {"loss": float(i)}, "step": i},
                    batch_key="run:1",
                )
            )
        worker.drain(timeout=5)

        entries = WALManager.read(wal.path)
        assert len(entries) == 5
        urls = {e["url"] for e in entries}
        assert urls == {"/api/runs/1/log"}
        worker.stop()

    def test_wal_deleted_after_successful_drain(self, mock_httpx_client, tmp_path):
        from dalva.sdk.wal import WALManager

        mock_httpx_client.post.return_value = _ok_response()
        wal = WALManager("run", 1, outbox_dir=tmp_path / "outbox")
        worker = SyncWorker("http://localhost:8000", wal_manager=wal)

        worker.enqueue(
            PendingRequest(
                method="POST",
                url="/api/runs/1/log",
                payload={"metrics": {"loss": 0.5}},
                batch_key="run:1",
            )
        )
        worker.drain(timeout=5)
        worker.wal_delete()

        assert not wal.exists
        worker.stop()

    def test_dump_remaining_persists_queue(self, mock_httpx_client, tmp_path):
        import threading

        from dalva.sdk.wal import WALManager

        picked_up = threading.Event()
        block_release = threading.Event()

        def slow_post(*args, **kwargs):
            picked_up.set()
            block_release.wait(timeout=5)
            return _ok_response()

        mock_httpx_client.post.side_effect = slow_post
        wal = WALManager("run", 1, outbox_dir=tmp_path / "outbox")
        worker = SyncWorker("http://localhost:8000", wal_manager=wal)

        worker.enqueue(
            PendingRequest(
                method="POST",
                url="/api/runs/1/log",
                payload={"loss": 0.1},
                batch_key="run:1",
            )
        )
        picked_up.wait(timeout=2)

        worker.enqueue(
            PendingRequest(
                method="POST",
                url="/api/runs/1/log",
                payload={"loss": 0.2},
                batch_key="run:1",
            )
        )
        worker.enqueue(
            PendingRequest(
                method="POST",
                url="/api/runs/1/log",
                payload={"loss": 0.3},
                batch_key="run:1",
            )
        )

        count = worker.dump_remaining()
        assert count == 2

        entries = WALManager.read(wal.path)
        assert len(entries) >= 2

        block_release.set()
        worker.stop()

    def test_no_wal_when_wal_manager_is_none(self, mock_httpx_client):
        mock_httpx_client.post.return_value = _ok_response()
        worker = SyncWorker("http://localhost:8000", wal_manager=None)

        worker.enqueue(PendingRequest(method="POST", url="/test"))
        worker.drain(timeout=5)
        assert worker.errors == []
        worker.stop()


class TestSyncWorkerSendMethods:
    def test_post_with_custom_headers(self, mock_httpx_client):
        mock_httpx_client.post.return_value = _ok_response()
        worker = SyncWorker("http://localhost:8000")

        req = PendingRequest(
            method="POST",
            url="/test",
            payload='{"data": 1}',
            headers={"Content-Type": "application/json"},
        )
        worker.enqueue(req)
        worker.drain(timeout=5)

        mock_httpx_client.post.assert_called_once_with(
            "/test",
            content='{"data": 1}',
            headers={"Content-Type": "application/json"},
        )
        worker.stop()

    def test_delete_request(self, mock_httpx_client):
        mock_httpx_client.delete.return_value = _ok_response()
        worker = SyncWorker("http://localhost:8000")

        req = PendingRequest(
            method="DELETE",
            url="/test/1",
            payload={"step": 5},
        )
        worker.enqueue(req)
        worker.drain(timeout=5)

        mock_httpx_client.delete.assert_called_once_with("/test/1", params={"step": 5})
        worker.stop()


class TestSyncWorkerTimeout:
    def test_timeout_not_retried_stored_as_error(self, mock_httpx_client):
        mock_httpx_client.post.side_effect = httpx.ReadTimeout("read timed out")

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=3,
            base_backoff=0.01,
        )

        req = PendingRequest(method="POST", url="/test", payload={"x": 1})
        worker.enqueue(req)
        drained = worker.drain(timeout=10)

        assert drained is True
        assert mock_httpx_client.post.call_count == 1
        errors = worker.errors
        assert len(errors) == 1
        assert isinstance(errors[0][1], httpx.ReadTimeout)
        worker.stop()

    def test_batch_timeout_not_retried_stored_as_error(self, mock_httpx_client):
        mock_httpx_client.post.side_effect = httpx.ReadTimeout("read timed out")

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=3,
            base_backoff=0.01,
            batch_size=100,
        )

        for i in range(3):
            worker.enqueue(
                PendingRequest(
                    method="POST",
                    url="/api/runs/1/log",
                    payload={"metrics": {"loss": float(i)}, "step": i},
                    batch_key="run:1",
                )
            )
        drained = worker.drain(timeout=10)

        assert drained is True
        assert mock_httpx_client.post.call_count == 1
        errors = worker.errors
        assert len(errors) == 1
        assert isinstance(errors[0][1], httpx.ReadTimeout)
        worker.stop()

    def test_connect_error_still_retried(self, mock_httpx_client):
        mock_httpx_client.post.side_effect = [
            httpx.ConnectError("connection refused"),
            _ok_response(),
        ]

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=3,
            base_backoff=0.01,
            max_backoff=0.1,
        )

        req = PendingRequest(method="POST", url="/test", payload={"x": 1})
        worker.enqueue(req)
        drained = worker.drain(timeout=10)

        assert drained is True
        assert worker.errors == []
        assert mock_httpx_client.post.call_count == 2
        worker.stop()

    def test_connect_timeout_not_retried(self, mock_httpx_client):
        mock_httpx_client.post.side_effect = httpx.ConnectTimeout("connect timed out")

        worker = SyncWorker(
            "http://localhost:8000",
            max_queue_size=10,
            max_retries=3,
            base_backoff=0.01,
        )

        req = PendingRequest(method="POST", url="/test", payload={"x": 1})
        worker.enqueue(req)
        drained = worker.drain(timeout=10)

        assert drained is True
        assert mock_httpx_client.post.call_count == 1
        errors = worker.errors
        assert len(errors) == 1
        assert isinstance(errors[0][1], httpx.ConnectTimeout)
        worker.stop()
