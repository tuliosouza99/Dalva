"""Tests for run.get() and run.get_config() endpoints.

These tests verify that:
- GET /api/runs/{run_id}/metrics/{attribute_path} returns {key, value, step}
- GET /api/runs/{run_id}/config/{key} returns {key, value}
- Both return 404 when key does not exist
- SDK Run.get() returns dict or default
- SDK Run.get_config() returns dict or default
"""

import json

from dalva.db.schema import Config


class TestGetMetric:
    """Tests for GET /api/runs/{run_id}/metrics/{attribute_path}."""

    def test_get_scalar_metric(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"best_loss": 0.5}},
        )
        assert response.status_code == 200

        response = api_client.get(f"/api/runs/{run_id}/metrics/best_loss")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "best_loss"
        assert data["value"] == 0.5
        assert data["step"] is None

    def test_get_series_metric_with_specific_step(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.5}, "step": 0},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.3}, "step": 1},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.1}, "step": 2},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/loss?step=1")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "loss"
        assert data["value"] == 0.3
        assert data["step"] == 1

    def test_get_series_metric_without_step_returns_latest(
        self, api_client, sample_run
    ):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.5}, "step": 0},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.3}, "step": 1},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.1}, "step": 2},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/loss")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "loss"
        assert data["value"] == 0.1
        assert data["step"] == 2

    def test_get_int_metric(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"epoch": 5}},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/epoch")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "epoch"
        assert data["value"] == 5
        assert data["step"] is None

    def test_get_string_metric(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"status": "ok"}},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/status")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "status"
        assert data["value"] == "ok"

    def test_get_bool_metric(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"converged": True}},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/converged")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "converged"
        assert data["value"] is True

    def test_get_nonexistent_metric_returns_404(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.get(f"/api/runs/{run_id}/metrics/nonexistent")
        assert response.status_code == 404

    def test_get_nonexistent_step_returns_404(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.5}, "step": 0},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/loss?step=99")
        assert response.status_code == 404

    def test_get_metric_run_not_found(self, api_client, sample_run):
        response = api_client.get("/api/runs/99999/metrics/loss")
        assert response.status_code == 404


class TestGetConfig:
    """Tests for GET /api/runs/{run_id}/config/{key}."""

    def test_get_config_key(self, api_client, sample_run):
        from dalva.db.connection import session_scope

        run_id = sample_run["id"]

        with session_scope() as session:
            session.add(Config(id=1, run_id=run_id, key="lr", value=json.dumps(0.001)))
            session.commit()

        response = api_client.get(f"/api/runs/{run_id}/config/lr")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "lr"
        assert data["value"] == 0.001

    def test_get_config_string_value(self, api_client, sample_run):
        from dalva.db.connection import session_scope

        run_id = sample_run["id"]

        with session_scope() as session:
            session.add(
                Config(id=1, run_id=run_id, key="model", value=json.dumps("resnet50"))
            )
            session.commit()

        response = api_client.get(f"/api/runs/{run_id}/config/model")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "model"
        assert data["value"] == "resnet50"

    def test_get_config_int_value(self, api_client, sample_run):
        from dalva.db.connection import session_scope

        run_id = sample_run["id"]

        with session_scope() as session:
            session.add(
                Config(id=1, run_id=run_id, key="batch_size", value=json.dumps(32))
            )
            session.commit()

        response = api_client.get(f"/api/runs/{run_id}/config/batch_size")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "batch_size"
        assert data["value"] == 32

    def test_get_config_list_value(self, api_client, sample_run):
        from dalva.db.connection import session_scope

        run_id = sample_run["id"]

        with session_scope() as session:
            session.add(
                Config(
                    id=1,
                    run_id=run_id,
                    key="layers",
                    value=json.dumps([64, 128, 256]),
                )
            )
            session.commit()

        response = api_client.get(f"/api/runs/{run_id}/config/layers")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "layers"
        assert data["value"] == [64, 128, 256]

    def test_get_nonexistent_config_returns_404(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.get(f"/api/runs/{run_id}/config/nonexistent")
        assert response.status_code == 404

    def test_get_config_run_not_found(self, api_client, sample_run):
        response = api_client.get("/api/runs/99999/config/lr")
        assert response.status_code == 404


class TestGetMetricSDK:
    """Tests for Run.get() SDK method via API client (simulating SDK calls)."""

    def test_get_scalar_returns_dict(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"best_loss": 0.5}},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/best_loss")
        data = response.json()
        assert data == {"key": "best_loss", "value": 0.5, "step": None}

    def test_get_series_no_step_returns_latest(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.8}, "step": 0},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.2}, "step": 5},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/loss")
        data = response.json()
        assert data == {"key": "loss", "value": 0.2, "step": 5}

    def test_get_series_specific_step(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.8}, "step": 0},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.2}, "step": 5},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/loss?step=0")
        data = response.json()
        assert data == {"key": "loss", "value": 0.8, "step": 0}

    def test_get_nonexistent_returns_default_none(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.get(f"/api/runs/{run_id}/metrics/missing_key")
        assert response.status_code == 404


class TestGetConfigSDK:
    """Tests for Run.get_config() SDK method via API client (simulating SDK calls)."""

    def test_get_config_returns_dict(self, api_client, sample_run):
        from dalva.db.connection import session_scope

        run_id = sample_run["id"]

        with session_scope() as session:
            session.add(Config(id=1, run_id=run_id, key="lr", value=json.dumps(0.001)))
            session.commit()

        response = api_client.get(f"/api/runs/{run_id}/config/lr")
        data = response.json()
        assert data == {"key": "lr", "value": 0.001}

    def test_get_config_nonexistent_returns_404(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.get(f"/api/runs/{run_id}/config/missing_key")
        assert response.status_code == 404


class TestNestedMetrics:
    """Tests for nested dict flattening in metric logging."""

    def test_log_nested_metrics_flattens_with_slash(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": 0.5, "acc": 0.9}}},
        )
        assert response.status_code == 200

        response = api_client.get(f"/api/runs/{run_id}/metrics/train/loss")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "train/loss"
        assert data["value"] == 0.5

        response = api_client.get(f"/api/runs/{run_id}/metrics/train/acc")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "train/acc"
        assert data["value"] == 0.9

    def test_log_deeply_nested_metrics(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"model": {"encoder": {"loss": 0.3}}}},
        )
        assert response.status_code == 200

        response = api_client.get(f"/api/runs/{run_id}/metrics/model/encoder/loss")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "model/encoder/loss"
        assert data["value"] == 0.3

    def test_log_nested_metrics_with_step(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": 0.5}}, "step": 0},
        )
        assert response.status_code == 200

        response = api_client.get(f"/api/runs/{run_id}/metrics/train/loss?step=0")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "train/loss"
        assert data["value"] == 0.5
        assert data["step"] == 0

    def test_log_nested_metrics_non_scalar_leaf_returns_422(
        self, api_client, sample_run
    ):
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": [0.5, 0.3]}}},
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "train/loss" in detail["invalid_keys"]

    def test_log_flat_metrics_still_work(self, api_client, sample_run):
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.5, "acc": 0.9}},
        )
        assert response.status_code == 200

    def test_nested_metrics_get_remove_relog(self, api_client, sample_run, db_session):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": 0.5}}, "step": 0},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/train/loss?step=0")
        assert response.status_code == 200
        assert response.json()["value"] == 0.5

        response = api_client.delete(
            f"/api/runs/{run_id}/metrics/train/loss?step=0",
        )
        assert response.status_code == 200

        db_session.commit()

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": 0.3}}, "step": 0},
        )
        assert response.status_code == 200

        response = api_client.get(f"/api/runs/{run_id}/metrics/train/loss?step=0")
        assert response.status_code == 200
        assert response.json()["value"] == 0.3

    def test_nested_metrics_remove_all_steps(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": 0.5}}, "step": 0},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": 0.3}}, "step": 1},
        )

        response = api_client.delete(
            f"/api/runs/{run_id}/metrics/train/loss",
        )
        assert response.status_code == 200
        assert response.json()["count"] == 2

        response = api_client.get(f"/api/runs/{run_id}/metrics/train/loss")
        assert response.status_code == 404

    def test_nested_metrics_get_latest_step(self, api_client, sample_run):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": 0.8}}, "step": 0},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"train": {"loss": 0.2}}, "step": 5},
        )

        response = api_client.get(f"/api/runs/{run_id}/metrics/train/loss")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 0.2
        assert data["step"] == 5


class TestNestedConfigRemoveAndRelog:
    """Tests for remove + relog pattern with nested config keys."""

    def test_remove_nested_config_key_and_relog(
        self, api_client, sample_run, db_session
    ):
        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/config",
            json={"config": {"optimizer": {"lr": 0.001}}},
        )

        response = api_client.get(f"/api/runs/{run_id}/config/optimizer/lr")
        assert response.status_code == 200
        assert response.json()["value"] == 0.001

        response = api_client.delete(f"/api/runs/{run_id}/config/optimizer/lr")
        assert response.status_code == 200

        db_session.commit()

        response = api_client.post(
            f"/api/runs/{run_id}/config",
            json={"config": {"optimizer": {"lr": 0.01}}},
        )
        assert response.status_code == 200

        response = api_client.get(f"/api/runs/{run_id}/config/optimizer/lr")
        assert response.status_code == 200
        assert response.json()["value"] == 0.01


class TestNestedConfigViaInit:
    """Tests for nested config via POST /api/runs/init."""

    def test_init_with_nested_config(self, api_client):
        response = api_client.post(
            "/api/runs/init",
            json={
                "project": "test-nested-config",
                "config": {"optimizer": {"lr": 0.001, "betas": [0.9, 0.999]}},
            },
        )
        assert response.status_code == 200
        run_id = response.json()["id"]

        response = api_client.get(f"/api/runs/{run_id}/config/optimizer/lr")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "optimizer/lr"
        assert data["value"] == 0.001

        response = api_client.get(f"/api/runs/{run_id}/config/optimizer/betas")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "optimizer/betas"
        assert data["value"] == [0.9, 0.999]
