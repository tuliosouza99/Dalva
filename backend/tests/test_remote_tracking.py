"""Tests for remote tracking feature (simplified HTTP-based).

This module tests the remote logging functionality where users can
track runs on a remote machine via SSH port forwarding.

Architecture:
- User starts dalva server locally (e.g., dalva server start)
- User SSH to remote machine with: ssh -R 8000:localhost:8000 remote
- On remote: dalva.init(server_url="http://localhost:8000", ...)
- All log/finish operations go through HTTP to the local server

The SDK (Run class) is a thin HTTP client - all DB operations happen
on the server side via API calls.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRunClient:
    """Tests for Run client with server_url."""

    def test_run_uses_http_client_when_server_url_provided(self):
        """Test that Run uses HTTP client when server_url is provided."""
        with patch("dalva.run.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 1,
                "run_id": "TEST-1",
                "name": "test",
            }
            mock_client.post.return_value = mock_response

            from dalva.run import Run

            with patch("dalva.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)

                run = Run(
                    project="test-project",
                    name="test-run",
                    server_url="http://localhost:8000",
                )

                assert run._server_url == "http://localhost:8000"
                mock_get.assert_called_once()

    def test_run_default_server_url(self):
        """Test that server_url defaults to http://localhost:8000."""
        with patch("dalva.run.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 1,
                "run_id": "TEST-1",
                "name": "test",
            }
            mock_client.post.return_value = mock_response

            from dalva.run import Run

            with patch("dalva.run.httpx.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200)

                run = Run(
                    project="test-project",
                    name="test-run",
                )

                assert run._server_url == "http://localhost:8000"


class TestAPILogEndpoint:
    """Tests for POST /api/runs/{run_id}/log endpoint."""

    def test_log_endpoint_accepts_metrics(self, api_client, sample_run):
        """Test that log endpoint accepts metrics and updates database."""
        from dalva.db.connection import session_scope
        from dalva.db.schema import Metric

        response = api_client.post(
            f"/api/runs/{sample_run['id']}/log",
            json={"metrics": {"loss": 0.5, "accuracy": 0.95}, "step": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify metrics were logged
        with session_scope() as session:
            metrics = (
                session.query(Metric).filter(Metric.run_id == sample_run["id"]).all()
            )
            assert len(metrics) == 2

            loss_metric = next(m for m in metrics if m.attribute_path == "loss")
            assert loss_metric.float_value == pytest.approx(0.5)

    def test_log_endpoint_updates_last_activity(self, api_client, sample_run):
        """Test that log endpoint updates last_activity_at."""
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
            run_after = session.query(Run).get(sample_run["id"])
            assert run_after.last_activity_at is not None


class TestAPIFinishEndpoint:
    """Tests for POST /api/runs/{run_id}/finish endpoint."""

    def test_finish_endpoint_marks_run_completed(self, api_client, sample_run):
        """Test that finish endpoint marks run as completed."""
        response = api_client.post(f"/api/runs/{sample_run['id']}/finish")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"


class TestAPIInitEndpoint:
    """Tests for POST /api/runs/init endpoint."""

    def test_init_endpoint_creates_run(self, api_client):
        """Test that init endpoint creates a new run."""
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
        """Test that init endpoint creates project if needed."""
        response = api_client.post(
            "/api/runs/init",
            json={"project": "brand-new-project", "name": "test-run"},
        )

        assert response.status_code == 200

        # Verify project was created
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
        """Test that init endpoint stores config."""
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
    """Tests for last_activity_at column in runs table."""

    def test_run_has_last_activity_at_column(self, db_session):
        """Test that the Run model has last_activity_at column."""
        from dalva.db.schema import Run

        assert hasattr(Run, "last_activity_at")

    def test_run_last_activity_at_defaults_to_none(self, db_session, sample_run):
        """Test that last_activity_at defaults to None on new runs."""
        from dalva.db.schema import Run

        run = db_session.query(Run).get(sample_run["id"])
        assert run.last_activity_at is None
