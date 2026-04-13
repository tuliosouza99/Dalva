"""Tests for remote tracking feature (simplified HTTP-based).

The SDK (Run class) is an HTTP client with a background worker thread.
log() is async (enqueued), finish()/remove()/get() are synchronous.
"""

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


class TestAPILogEndpoint:
    def test_log_endpoint_accepts_metrics(self, api_client, sample_run):
        from dalva.db.connection import session_scope
        from dalva.db.schema import Metric

        response = api_client.post(
            f"/api/runs/{sample_run['id']}/log",
            json={"metrics": {"loss": 0.5, "accuracy": 0.95}, "step": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        with session_scope() as session:
            metrics = (
                session.query(Metric).filter(Metric.run_id == sample_run["id"]).all()
            )
            assert len(metrics) == 2
            loss_metric = next(m for m in metrics if m.attribute_path == "loss")
            assert loss_metric.float_value == pytest.approx(0.5)

    def test_log_endpoint_updates_last_activity(self, api_client, sample_run):
        import time

        from dalva.db.connection import session_scope
        from dalva.db.schema import Run

        time.sleep(0.01)

        response = api_client.post(
            f"/api/runs/{sample_run['id']}/log",
            json={"metrics": {"loss": 0.5}},
        )

        assert response.status_code == 200

        with session_scope() as session:
            run_after = session.get(Run, sample_run["id"])
            assert run_after.last_activity_at is not None


class TestAPIFinishEndpoint:
    def test_finish_endpoint_marks_run_completed(self, api_client, sample_run):
        response = api_client.post(f"/api/runs/{sample_run['id']}/finish")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"


class TestAPIInitEndpoint:
    def test_init_endpoint_creates_run(self, api_client):
        response = api_client.post(
            "/api/runs/init",
            json={"project": "init-test-project", "name": "init-run"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "run_id" in data
        assert data["name"] == "init-run"

    def test_init_endpoint_creates_project(self, api_client):
        response = api_client.post(
            "/api/runs/init",
            json={"project": "brand-new-project", "name": "test-run"},
        )

        assert response.status_code == 200

        from dalva.db.connection import session_scope
        from dalva.db.schema import Project

        with session_scope() as session:
            project = (
                session.query(Project)
                .filter(Project.name == "brand-new-project")
                .first()
            )
            assert project is not None

    def test_init_endpoint_with_config(self, api_client):
        response = api_client.post(
            "/api/runs/init",
            json={
                "project": "config-init-project",
                "name": "config-run",
                "config": {"lr": 0.001, "batch_size": 32},
            },
        )

        assert response.status_code == 200

        from dalva.db.connection import session_scope
        from dalva.db.schema import Config

        with session_scope() as session:
            configs = (
                session.query(Config)
                .filter(Config.run_id == response.json()["id"])
                .all()
            )
            assert len(configs) == 2


class TestSchemaLastActivityAt:
    def test_run_has_last_activity_at_column(self, db_session):
        from dalva.db.schema import Run

        assert hasattr(Run, "last_activity_at")

    def test_run_last_activity_at_defaults_to_none(self, db_session, sample_run):
        from dalva.db.schema import Run

        run = db_session.get(Run, sample_run["id"])
        assert run.last_activity_at is None
