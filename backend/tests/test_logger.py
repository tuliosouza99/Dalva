"""Tests for LoggingService."""

import pytest
from dalva.db import connection
from dalva.db.connection import session_scope
from dalva.db.schema import Metric, Project
from dalva.services.logger import LoggingService


class TestGenerateAbbreviation:
    """Tests for _generate_abbreviation function."""

    @pytest.mark.parametrize(
        "input,expected",
        [
            ("testing", "TES"),
            ("ab", "ABX"),  # Pads to 3 chars
            ("a", "AXX"),
            (
                "my project",
                "MPY",
            ),  # Two words: first letter of each + second letter of first
            ("track ai", "TAR"),
            ("machine learning model", "MLM"),  # Three words: first letter of each
            ("one two three", "OTT"),
            ("my-project_123", "MPY"),  # Underscore removed, treated as one word
            ("test@#$%", "TES"),  # Special chars removed
            ("", "RUN"),  # Empty string defaults to RUN
            ("   ", "RUN"),  # Whitespace only defaults to RUN
            ("!@#$%", "RUN"),  # Special chars only defaults to RUN
        ],
    )
    def test_abbreviation(self, input, expected):
        """Test abbreviation generation for various project name formats."""
        from dalva.services.logger import _generate_abbreviation

        assert _generate_abbreviation(input) == expected


class TestLoggingServiceProject:
    """Tests for LoggingService project operations."""

    def test_get_or_create_project_new(self):
        """Test creating a new project."""

        # Patch session_scope to use our test session
        original_scope = connection.session_scope

        def test_scope():
            return original_scope().__enter__()

        connection.session_scope = test_scope

        try:
            service = LoggingService()
            project_id = service.get_or_create_project("new-project")

            assert project_id is not None
            assert isinstance(project_id, int)
        finally:
            connection.session_scope = original_scope

    def test_get_or_create_project_existing(self, db_session):
        """Test getting an existing project."""
        # Create project first
        project = Project(
            name="existing-project",
            project_id="existing_123",
        )
        db_session.add(project)
        db_session.commit()
        project_id = project.id

        # Try to get or create - should return existing
        service = LoggingService()
        result_id = service.get_or_create_project("existing-project")

        assert result_id == project_id


class TestLoggingServiceRun:
    """Tests for LoggingService run operations."""

    def test_create_run_new(self, db_session):
        """Test creating a new run."""
        # Create project first
        project = Project(name="test-project", project_id="test_123")
        db_session.add(project)
        db_session.commit()

        service = LoggingService()
        db_id, run_id, name = service.create_run(
            project_name="test-project",
            run_name="my-run",
        )

        assert db_id is not None
        assert isinstance(db_id, int)
        assert run_id is not None
        assert name == "my-run"

    def test_create_run_with_config(self, db_session):
        """Test creating a run with config dictionary."""
        # Create project first
        project = Project(name="config-test-project", project_id="config_123")
        db_session.add(project)
        db_session.commit()

        config = {
            "learning_rate": 0.001,
            "batch_size": 32,
            "optimizer": "adam",
        }

        service = LoggingService()
        db_id, run_id, name = service.create_run(
            project_name="config-test-project",
            run_name="config-run",
            config=config,
        )

        assert db_id is not None

    def test_create_run_with_nested_config(self, db_session):
        """Test creating a run with nested config dictionary."""
        # Create project first
        project = Project(name="nested-config-project", project_id="nested_123")
        db_session.add(project)
        db_session.commit()

        config = {
            "model": {
                "layers": 4,
                "hidden_size": 256,
            },
            "training": {
                "epochs": 100,
                "early_stopping": True,
            },
        }

        service = LoggingService()
        db_id, run_id, name = service.create_run(
            project_name="nested-config-project",
            config=config,
        )

        assert db_id is not None


class TestLoggingServiceMetrics:
    """Tests for LoggingService metric logging."""

    def test_log_metrics_float(self, sample_run):
        """Test logging float metrics with step=0 (series type)."""
        service = LoggingService()
        service.log_metrics(
            run_id=sample_run["id"],
            metrics={"loss": 0.5, "accuracy": 0.95},
            step=0,
        )

        # Verify metrics were logged using session_scope for consistency
        with session_scope() as session:
            metrics = (
                session.query(Metric).filter(Metric.run_id == sample_run["id"]).all()
            )
            assert len(metrics) == 2

            loss_metric = next(m for m in metrics if m.attribute_path == "loss")
            assert loss_metric.float_value == 0.5
            assert loss_metric.attribute_type == "float_series"

    def test_log_metrics_int(self, sample_run):
        """Test logging integer metrics with step=0 (series type)."""
        service = LoggingService()
        service.log_metrics(
            run_id=sample_run["id"],
            metrics={"epoch": 42, "steps_per_epoch": 100},
            step=0,
        )

        with session_scope() as session:
            metrics = (
                session.query(Metric).filter(Metric.run_id == sample_run["id"]).all()
            )
            epoch_metric = next(m for m in metrics if m.attribute_path == "epoch")
            assert epoch_metric.int_value == 42
            assert epoch_metric.attribute_type == "int_series"

    def test_log_metrics_bool(self, sample_run):
        """Test logging boolean metrics with step=0 (series type)."""
        service = LoggingService()
        service.log_metrics(
            run_id=sample_run["id"],
            metrics={"early_stopping": True, "use_cuda": False},
            step=0,
        )

        with session_scope() as session:
            metrics = (
                session.query(Metric).filter(Metric.run_id == sample_run["id"]).all()
            )
            es_metric = next(m for m in metrics if m.attribute_path == "early_stopping")
            assert es_metric.bool_value is True
            assert es_metric.attribute_type == "bool_series"

    def test_log_metrics_string(self, sample_run):
        """Test logging string metrics with step=0 (series type)."""
        service = LoggingService()
        service.log_metrics(
            run_id=sample_run["id"],
            metrics={"status": "training", "model_name": "resnet50"},
            step=0,
        )

        with session_scope() as session:
            metrics = (
                session.query(Metric).filter(Metric.run_id == sample_run["id"]).all()
            )
            status_metric = next(m for m in metrics if m.attribute_path == "status")
            assert status_metric.string_value == "training"
            assert status_metric.attribute_type == "string_series"

    def test_log_metrics_multiple_steps(self, sample_run):
        """Test logging metrics at multiple steps."""
        service = LoggingService()

        for step in range(3):
            service.log_metrics(
                run_id=sample_run["id"],
                metrics={"loss": 1.0 - step * 0.3},
                step=step,
            )

        with session_scope() as session:
            metrics = (
                session.query(Metric).filter(Metric.run_id == sample_run["id"]).all()
            )
            assert len(metrics) == 3

            steps = {m.step for m in metrics}
            assert steps == {0, 1, 2}

    def test_log_metrics_summary_no_step(self, sample_run):
        """Test logging summary metrics without step (scalar type)."""
        service = LoggingService()
        service.log_metrics(
            run_id=sample_run["id"],
            metrics={"final_loss": 0.1, "final_accuracy": 0.99},
        )

        with session_scope() as session:
            metrics = (
                session.query(Metric).filter(Metric.run_id == sample_run["id"]).all()
            )
            loss_metric = next(m for m in metrics if m.attribute_path == "final_loss")
            assert loss_metric.float_value == pytest.approx(0.1)
            assert loss_metric.attribute_type == "float"
            assert loss_metric.step is None


class TestLoggingServiceConfigFlattening:
    """Tests for nested config flattening."""

    def test_flatten_simple_dict(self):
        """Test flattening a simple dictionary."""
        service = LoggingService()
        flat = {}
        service._flatten({"a": 1, "b": 2}, "", flat)
        assert flat == {"a": 1, "b": 2}

    def test_flatten_nested_dict(self):
        """Test flattening a nested dictionary."""
        service = LoggingService()
        flat = {}
        service._flatten(
            {"model": {"layers": 4, "hidden": 256}, "lr": 0.001},
            "",
            flat,
        )
        assert "model/layers" in flat
        assert "model/hidden" in flat
        assert flat["model/layers"] == 4
        assert flat["model/hidden"] == 256
        assert flat["lr"] == 0.001

    def test_flatten_deeply_nested_dict(self):
        """Test flattening a deeply nested dictionary."""
        service = LoggingService()
        flat = {}
        service._flatten(
            {"a": {"b": {"c": {"d": 1}}}},
            "",
            flat,
        )
        assert "a/b/c/d" in flat
        assert flat["a/b/c/d"] == 1

    def test_flatten_with_prefix(self):
        """Test flattening with a prefix."""
        service = LoggingService()
        flat = {}
        service._flatten({"lr": 0.001}, "hyperparameters/", flat)
        assert "hyperparameters/lr" in flat
        assert flat["hyperparameters/lr"] == 0.001
