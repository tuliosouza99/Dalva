"""API endpoint tests for runs (log, finish, init, schema) — real DB."""

import time

import pytest

from dalva.db.connection import session_scope
from dalva.db.schema import Config, Metric, Project, Run


@pytest.mark.api
class TestAPILogEndpoint:
    def test_log_endpoint_accepts_metrics(self, api_client, sample_run):
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
        time.sleep(0.01)

        response = api_client.post(
            f"/api/runs/{sample_run['id']}/log",
            json={"metrics": {"loss": 0.5}},
        )

        assert response.status_code == 200

        with session_scope() as session:
            run_after = session.get(Run, sample_run["id"])
            assert run_after.last_activity_at is not None


@pytest.mark.api
class TestAPIFinishEndpoint:
    def test_finish_endpoint_marks_run_completed(self, api_client, sample_run):
        response = api_client.post(f"/api/runs/{sample_run['id']}/finish")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"


@pytest.mark.api
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

        with session_scope() as session:
            configs = (
                session.query(Config)
                .filter(Config.run_id == response.json()["id"])
                .all()
            )
            assert len(configs) == 2


@pytest.mark.api
class TestSchemaLastActivityAt:
    def test_run_has_last_activity_at_column(self, db_session):
        assert hasattr(Run, "last_activity_at")

    def test_run_last_activity_at_defaults_to_none(self, db_session, sample_run):
        run = db_session.get(Run, sample_run["id"])
        assert run.last_activity_at is None
