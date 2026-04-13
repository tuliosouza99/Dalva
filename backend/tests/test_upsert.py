"""Tests for strict insert behavior when logging metrics and config.

These tests verify that:
- Logging a duplicate metric/config key raises 409 Conflict
- Type conflicts (int vs float, float vs string, etc.) raise 409 Conflict
- Scalar/series conflicts raise 409 Conflict
- Remove works correctly
- After remove, logging works again (strict insert)
"""

import json

from sqlalchemy import text

import pytest


class TestMetricStrictInsert:
    """Tests for strict insert on metrics."""

    def test_log_metric_same_path_and_step_returns_409(self, api_client, sample_run):
        """Logging the same metric path with the same step returns 409 Conflict."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.5}, "step": 0},
        )
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.3}, "step": 0},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]["conflicts"][0]

    def test_log_metric_same_path_different_step_creates_new_row(
        self, api_client, sample_run
    ):
        """Logging the same metric path with a different step creates a new row."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.5}, "step": 0},
        )
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.3}, "step": 1},
        )
        assert response.status_code == 200

    def test_log_metric_summary_same_path_returns_409(self, api_client, sample_run):
        """Logging the same metric path twice (no step) returns 409 Conflict."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"best_loss_scalar": 0.5}},
        )
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"best_loss_scalar": 0.2}},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]["conflicts"][0]

    def test_log_series_then_scalar_returns_409(self, api_client, sample_run):
        """Logging series then scalar on same key returns 409 Conflict."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"acc_series_scalar": 0.5}, "step": 0},
        )
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"acc_series_scalar": 0.9}},
        )
        assert response.status_code == 409
        assert "already has series" in response.json()["detail"]["conflicts"][0]

    def test_log_scalar_then_series_returns_409(self, api_client, sample_run):
        """Logging scalar then series on same key returns 409 Conflict."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"metric_scalar_series": 0.5}},
        )
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"metric_scalar_series": 0.3}, "step": 0},
        )
        assert response.status_code == 409
        assert "already has scalar" in response.json()["detail"]["conflicts"][0]

    def test_log_int_then_float_same_key_returns_409(self, api_client, sample_run):
        """Logging int then float on same key returns 409 Conflict."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"m_int_float": 5}, "step": 0},
        )
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"m_int_float": 5.5}, "step": 0},
        )
        assert response.status_code == 409
        assert "Type conflict" in response.json()["detail"]["conflicts"][0]

    def test_log_float_then_int_same_key_returns_409(self, api_client, sample_run):
        """Logging float then int on same key returns 409 Conflict."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"m_float_int": 5.5}, "step": 0},
        )
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"m_float_int": 5}, "step": 0},
        )
        assert response.status_code == 409


class TestRemoveMetric:
    """Tests for metric removal."""

    def test_remove_metric_by_step(self, api_client, sample_run):
        """Removing a specific step removes only that step."""
        from dalva.db.connection import session_scope
        from dalva.db.schema import Metric

        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.5}, "step": 0},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.3}, "step": 1},
        )

        response = api_client.delete(
            f"/api/runs/{run_id}/metrics/loss?step=0",
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1

        with session_scope() as session:
            remaining = (
                session.query(Metric)
                .filter(Metric.run_id == run_id, Metric.attribute_path == "loss")
                .all()
            )
            assert len(remaining) == 1
            assert remaining[0].step == 1

    def test_remove_metric_all_steps(self, api_client, sample_run):
        """Removing without step removes all entries for the metric."""
        from dalva.db.connection import session_scope
        from dalva.db.schema import Metric

        run_id = sample_run["id"]

        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.5}, "step": 0},
        )
        api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss": 0.3}, "step": 1},
        )

        response = api_client.delete(
            f"/api/runs/{run_id}/metrics/loss",
        )
        assert response.status_code == 200
        assert response.json()["count"] == 2

        with session_scope() as session:
            remaining = (
                session.query(Metric)
                .filter(Metric.run_id == run_id, Metric.attribute_path == "loss")
                .all()
            )
            assert len(remaining) == 0

    def test_after_remove_can_log_again(self, api_client, sample_run, db_session):
        """After removing a metric, logging a new value succeeds."""
        from dalva.db.schema import Metric

        run_id = sample_run["id"]

        metric = Metric(
            id=9999,
            run_id=run_id,
            attribute_path="loss_relog2",
            attribute_type="float_series",
            step=50,
            float_value=0.5,
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.delete(
            f"/api/runs/{run_id}/metrics/loss_relog2?step=50",
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1

        response = api_client.post(
            f"/api/runs/{run_id}/log",
            json={"metrics": {"loss_relog2": 0.3}, "step": 50},
        )
        assert response.status_code == 200

    def test_remove_nonexistent_metric_returns_404(self, api_client, sample_run):
        """Removing a non-existent metric returns 404."""
        run_id = sample_run["id"]

        response = api_client.delete(
            f"/api/runs/{run_id}/metrics/nonexistent?step=0",
        )
        assert response.status_code == 404


class TestConfigStrictInsert:
    """Tests for strict insert on configs."""

    def test_config_raises_on_duplicate_key(self, api_client, sample_run):
        """Adding a config key that already exists raises ValueError."""
        from dalva.db.connection import session_scope
        from dalva.db.schema import Config

        run_id = sample_run["id"]

        with session_scope() as session:
            session.add(Config(id=1, run_id=run_id, key="lr", value='"0.001"'))
            session.commit()

        with pytest.raises(Exception):
            from dalva.services.logger import _log_config

            _log_config(run_id, {"lr": 0.01})

    def test_config_duplicate_returns_409_via_init(self, api_client, sample_run):
        """Creating a run with config, then trying to log same key via _log_config raises."""
        from dalva.db.connection import session_scope
        from dalva.db.schema import Config
        from dalva.services.logger import _log_config

        run_id = sample_run["id"]

        with session_scope() as session:
            session.add(Config(id=1, run_id=run_id, key="lr", value='"0.001"'))
            session.add(Config(id=2, run_id=run_id, key="batch_size", value="32"))
            session.commit()

        with pytest.raises(ValueError, match="already exists"):
            _log_config(run_id, {"lr": 0.01})


class TestRemoveConfig:
    """Tests for config removal."""

    def test_remove_config_by_key(self, api_client, sample_run):
        """Removing a config key by name works."""
        from dalva.db.connection import session_scope
        from dalva.db.schema import Config

        run_id = sample_run["id"]

        with session_scope() as session:
            session.add(Config(id=1, run_id=run_id, key="lr", value='"0.001"'))
            session.add(Config(id=2, run_id=run_id, key="batch_size", value="32"))
            session.commit()

        response = api_client.delete(f"/api/runs/{run_id}/config/lr")
        assert response.status_code == 200
        assert "lr" in response.json()["message"]

        with session_scope() as session:
            remaining = session.query(Config).filter(Config.run_id == run_id).all()
            assert len(remaining) == 1
            assert remaining[0].key == "batch_size"

    def test_remove_nonexistent_config_returns_404(self, api_client, sample_run):
        """Removing a non-existent config key returns 404."""
        run_id = sample_run["id"]

        response = api_client.delete(f"/api/runs/{run_id}/config/nonexistent")
        assert response.status_code == 404


class TestLogConfig:
    """Tests for log_config endpoint."""

    def test_log_config_adds_new_keys(self, api_client, sample_run):
        """Logging new config keys succeeds."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/config",
            json={"config": {"lr": 0.001, "batch_size": 32}},
        )
        assert response.status_code == 200

        from dalva.db.connection import session_scope
        from dalva.db.schema import Config

        with session_scope() as session:
            configs = session.query(Config).filter(Config.run_id == run_id).all()
            keys = {c.key for c in configs}
            assert "lr" in keys
            assert "batch_size" in keys

    def test_log_config_nested_dict(self, api_client, sample_run):
        """Nested dicts are flattened with / separator."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/config",
            json={"config": {"optimizer": {"lr": 0.001, "betas": [0.9, 0.999]}}},
        )
        assert response.status_code == 200

        from dalva.db.connection import session_scope
        from dalva.db.schema import Config

        with session_scope() as session:
            configs = session.query(Config).filter(Config.run_id == run_id).all()
            keys = {c.key for c in configs}
            assert "optimizer/lr" in keys
            assert "optimizer/betas" in keys

    def test_log_config_duplicate_key_returns_409(self, api_client, sample_run):
        """Logging a key that already exists returns 409."""
        from dalva.db.connection import session_scope
        from dalva.db.schema import Config

        run_id = sample_run["id"]

        with session_scope() as session:
            c = Config(id=1, run_id=run_id, key="lr", value='"0.001"')
            session.add(c)
            session.commit()
            session.execute(text("DROP SEQUENCE IF EXISTS configs_id_seq"))
            session.execute(text("CREATE SEQUENCE configs_id_seq START 2"))
            session.commit()

        response = api_client.post(
            f"/api/runs/{run_id}/config",
            json={"config": {"lr": 0.01}},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]["conflicts"][0]

    def test_log_config_partial_duplicate_returns_409(self, api_client, sample_run):
        """If any key in the request conflicts, entire request fails."""
        run_id = sample_run["id"]

        response = api_client.post(
            f"/api/runs/{run_id}/config",
            json={"config": {"lr": 0.001, "batch_size": 32}},
        )
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/config",
            json={"config": {"lr": 0.01, "epochs": 100}},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]["conflicts"][0]

        from dalva.db.connection import session_scope
        from dalva.db.schema import Config

        with session_scope() as session:
            configs = session.query(Config).filter(Config.run_id == run_id).all()
            keys = {c.key for c in configs}
            assert "lr" in keys
            assert "batch_size" in keys
            assert "epochs" not in keys

    def test_log_config_after_remove(self, api_client, sample_run, db_session):
        """After removing a key, logging a new value for that key succeeds."""
        from dalva.db.schema import Config

        run_id = sample_run["id"]

        c = Config(id=1, run_id=run_id, key="lr", value='"0.001"')
        db_session.add(c)
        db_session.commit()
        db_session.execute(text("DROP SEQUENCE IF EXISTS configs_id_seq"))
        db_session.execute(text("CREATE SEQUENCE configs_id_seq START 2"))
        db_session.commit()

        response = api_client.delete(f"/api/runs/{run_id}/config/lr")
        assert response.status_code == 200

        response = api_client.post(
            f"/api/runs/{run_id}/config",
            json={"config": {"lr": 0.01}},
        )
        assert response.status_code == 200

        db_session.expire_all()
        configs = db_session.query(Config).filter(Config.run_id == run_id).all()
        lr_config = next(cfg for cfg in configs if cfg.key == "lr")
        assert json.loads(lr_config.value) == 0.01
