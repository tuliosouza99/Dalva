"""Unit tests for SDK Run/Table classes — mocked HTTP, no DB."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from dalva.sdk.run import DalvaError


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


INIT_RESPONSE = _mock_response(json_data={"id": 1, "run_id": "TEST-1", "name": "test"})
FINISH_RESPONSE = _mock_response(json_data={"state": "completed"})


def _mock_worker(pending=0, errors=None, drain_result=True):
    w = MagicMock()
    w.pending = pending
    w.drain_with_progress.return_value = drain_result
    w.clear_errors.return_value = errors or []
    return w


def _make_run_mock_client():
    mock_client = MagicMock()
    mock_client.post.side_effect = lambda url, **kw: (
        FINISH_RESPONSE if "finish" in url else INIT_RESPONSE
    )
    mock_client.get.return_value = _mock_response(json_data={})
    mock_client.delete.return_value = _mock_response(json_data={})
    return mock_client


@pytest.mark.unit
class TestRunClient:
    def test_run_uses_http_client_when_server_url_provided(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker"),
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(
                    project="test-project",
                    name="test-run",
                    server_url="http://localhost:8000",
                )
                assert run._server_url == "http://localhost:8000"
                mock_get.assert_called_once()

    def test_run_default_server_url(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker"),
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project", name="test-run")
                assert run._server_url == "http://localhost:8000"


@pytest.mark.unit
class TestRunAsyncLog:
    def test_log_enqueues_request(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client_class.return_value = _make_run_mock_client()
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            run.log({"loss": 0.5}, step=0)
            mock_worker.enqueue.assert_called_once()
            req = mock_worker.enqueue.call_args[0][0]
            assert req.method == "POST"
            assert req.url == "/api/runs/1/log"
            assert req.payload == {"metrics": {"loss": 0.5}, "step": 0}

    def test_log_raises_on_finished_run(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client_class.return_value = _make_run_mock_client()
            mock_worker_class.return_value = _mock_worker()

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            run._finished = True
            with pytest.raises(RuntimeError, match="Cannot log to a finished run"):
                run.log({"loss": 0.5}, step=0)


@pytest.mark.unit
class TestRunFlush:
    def test_flush_drains_worker_and_returns_errors(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client_class.return_value = _make_run_mock_client()
            mock_worker = _mock_worker(pending=3)
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            errors = run.flush(timeout=30)
            mock_worker.drain_with_progress.assert_called_once_with(
                label="Flushing", timeout=30
            )
            assert errors == []


@pytest.mark.unit
class TestRunFinish:
    def test_finish_drains_worker_then_sends_finish(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker(pending=3)
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            run.finish()

            mock_worker.drain_with_progress.assert_called_once_with(
                label="Finishing run", timeout=120
            )
            mock_worker.clear_errors.assert_called_once()
            mock_worker.stop.assert_called_once()
            assert run._finished is True
            assert run._worker is None

    def test_finish_only_sets_finished_on_success(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            run.finish()
            assert run._finished is True

    def test_finish_does_not_set_finished_on_failure(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.post.side_effect = lambda url, **kw: (
                INIT_RESPONSE
                if "init" in url
                else _mock_response(status_code=500, json_data={"detail": "oops"})
            )
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            with pytest.raises(ConnectionError):
                run.finish()

            assert run._finished is False
            assert run._worker is None

    def test_finish_warns_on_accumulated_errors(self):
        import warnings

        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client

            from dalva.sdk.worker import PendingRequest

            failed_req = PendingRequest(method="POST", url="/api/runs/1/log")
            mock_worker = _mock_worker(
                errors=[(failed_req, httpx.ConnectError("fail"))]
            )
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                run.finish(on_error="warn")

            assert run._finished is True
            warn_msgs = [
                str(x.message) for x in w if "Request failed" in str(x.message)
            ]
            assert len(warn_msgs) == 1

    def test_finish_raises_dalva_error_on_accumulated_errors(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client

            from dalva.sdk.worker import PendingRequest

            failed_req = PendingRequest(method="POST", url="/api/runs/1/log")
            mock_worker = _mock_worker(
                errors=[(failed_req, httpx.ConnectError("fail"))]
            )
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            with pytest.raises(DalvaError, match="1 request\\(s\\) failed"):
                run.finish(on_error="raise")

            assert run._finished is True

    def test_finish_retriable_after_network_failure(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            error_resp = _mock_response(
                status_code=500, json_data={"detail": "internal error"}
            )
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "500", request=MagicMock(), response=error_resp
            )

            with pytest.raises(ConnectionError):
                run.finish()

            assert run._finished is False
            assert run._worker is None

            mock_client.post.side_effect = lambda url, **kw: FINISH_RESPONSE
            run.finish()
            assert run._finished is True

    def test_finish_is_idempotent(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            run.finish()
            assert run._finished is True

            init_call_count = mock_worker.drain_with_progress.call_count
            run.finish()
            assert mock_worker.drain_with_progress.call_count == init_call_count


@pytest.mark.unit
class TestRunRemove:
    def test_remove_drains_queue_first(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            run.remove("loss", step=0)
            mock_worker.drain.assert_called_once()


@pytest.mark.unit
class TestRunLogConfig:
    def test_log_config_drains_queue_first(self):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project")

            run.log_config({"lr": 0.01})
            mock_worker.drain.assert_called_once()


@pytest.mark.unit
class TestRunWALUnit:
    def test_run_creates_wal_manager(self, tmp_path):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.run.WALManager") as mock_wal_class,
        ):
            mock_client_class.return_value = _make_run_mock_client()
            mock_worker_class.return_value = _mock_worker()
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                Run(project="test-project", outbox_dir=tmp_path / "outbox")

            mock_wal_class.assert_called_once_with(
                "run", 1, outbox_dir=tmp_path / "outbox"
            )
            mock_worker_class.assert_called_once()
            assert mock_worker_class.call_args.kwargs.get("wal_manager") is mock_wal

    def test_finish_deletes_wal_on_success(self, tmp_path):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.run.WALManager") as mock_wal_class,
        ):
            mock_client_class.return_value = _make_run_mock_client()
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project", outbox_dir=tmp_path / "outbox")

            run.finish()

            mock_worker.wal_delete.assert_called_once()

    def test_finish_dumps_remaining_on_timeout(self, tmp_path):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.run.WALManager") as mock_wal_class,
        ):
            mock_client = _make_run_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker(pending=10)
            mock_worker.drain_with_progress.return_value = False
            mock_worker.dump_remaining.return_value = 7
            mock_worker_class.return_value = mock_worker
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project", outbox_dir=tmp_path / "outbox")

            run.finish(timeout=5)

            mock_worker.dump_remaining.assert_called_once()
            mock_wal.delete.assert_not_called()
            assert run._finished is False

    def test_flush_dumps_remaining_on_timeout(self, tmp_path):
        with (
            patch("dalva.sdk.run.httpx.Client") as mock_client_class,
            patch("dalva.sdk.run.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.run.WALManager") as mock_wal_class,
        ):
            mock_client_class.return_value = _make_run_mock_client()
            mock_worker = _mock_worker(pending=5)
            mock_worker.drain_with_progress.return_value = False
            mock_worker.dump_remaining.return_value = 3
            mock_worker_class.return_value = mock_worker
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.run import Run

            with patch("dalva.sdk.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                run = Run(project="test-project", outbox_dir=tmp_path / "outbox")

            run.flush(timeout=5)
            mock_worker.dump_remaining.assert_called_once()


@pytest.mark.unit
class TestTableWALUnit:
    def test_table_creates_wal_manager(self, tmp_path):
        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager") as mock_wal_class,
        ):
            mock_client = MagicMock()
            mock_client.get.side_effect = lambda url, **kw: (
                _mock_response(status_code=200)
                if "health" in url
                else _mock_response(json_data=[])
            )
            mock_client.post.return_value = _mock_response(
                json_data={
                    "id": 7,
                    "table_id": "T-1",
                    "name": "test",
                    "log_mode": "IMMUTABLE",
                    "version": 0,
                }
            )
            mock_client_class.return_value = mock_client
            mock_worker_class.return_value = MagicMock()
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.table import Table

            with patch("dalva.sdk.table.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                Table(project="test-project", outbox_dir=tmp_path / "outbox")

            mock_wal_class.assert_called_once_with(
                "table", 7, outbox_dir=tmp_path / "outbox"
            )

    def test_finish_deletes_wal_on_success(self, tmp_path):
        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager") as mock_wal_class,
        ):
            mock_client = MagicMock()
            mock_client.get.side_effect = lambda url, **kw: _mock_response(
                status_code=200
            )
            mock_client.post.side_effect = lambda url, **kw: (
                _mock_response(
                    json_data={
                        "id": 7,
                        "table_id": "T-1",
                        "name": "test",
                        "log_mode": "IMMUTABLE",
                        "version": 0,
                    }
                )
                if "init" in url
                else _mock_response(json_data={"state": "finished"})
            )
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.table import Table

            with patch("dalva.sdk.table.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                table = Table(project="test-project", outbox_dir=tmp_path / "outbox")

            table.finish()

            mock_worker.wal_delete.assert_called_once()

    def test_finish_dumps_remaining_on_timeout(self, tmp_path):
        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager") as mock_wal_class,
        ):
            mock_client = MagicMock()
            mock_client.get.side_effect = lambda url, **kw: _mock_response(
                status_code=200
            )
            mock_client.post.side_effect = lambda url, **kw: (
                _mock_response(
                    json_data={
                        "id": 7,
                        "table_id": "T-1",
                        "name": "test",
                        "log_mode": "IMMUTABLE",
                        "version": 0,
                    }
                )
                if "init" in url
                else _mock_response(json_data={"state": "finished"})
            )
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker(pending=10)
            mock_worker.drain_with_progress.return_value = False
            mock_worker.dump_remaining.return_value = 5
            mock_worker_class.return_value = mock_worker
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.table import Table

            with patch("dalva.sdk.table.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)
                table = Table(project="test-project", outbox_dir=tmp_path / "outbox")

            table.finish(timeout=5)

            mock_worker.dump_remaining.assert_called_once()
            mock_wal.delete.assert_not_called()
