"""Tests for dalva query CLI commands — read-only experiment queries."""

import json
from unittest.mock import MagicMock, patch

import httpx
from click.testing import CliRunner

from dalva.cli.query import query


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _mock_client(responses):
    """Create a mock httpx.Client that returns responses in order."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    if isinstance(responses, list):
        client.request.side_effect = responses
    else:
        client.request.return_value = responses
    return client


SAMPLE_PROJECTS = [
    {
        "id": 1,
        "name": "my-project",
        "project_id": "my-project_abc123",
        "total_runs": 5,
        "running_runs": 1,
        "completed_runs": 3,
        "failed_runs": 1,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
]

SAMPLE_RUNS = {
    "runs": [
        {
            "id": 1,
            "project_id": 1,
            "run_id": "RUN-1",
            "name": "baseline",
            "group_name": None,
            "tags": None,
            "state": "completed",
            "fork_from": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
    ],
    "total": 1,
    "has_more": False,
}

SAMPLE_RUN_SUMMARY = {
    "id": 1,
    "project_id": 1,
    "run_id": "RUN-1",
    "name": "baseline",
    "state": "completed",
    "metrics": {"loss": 0.5, "accuracy": 0.95},
    "config": {"lr": 0.001, "epochs": 10},
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00",
}

SAMPLE_METRICS_LIST = [
    {"path": "loss", "attribute_type": "float"},
    {"path": "accuracy", "attribute_type": "float"},
]

SAMPLE_METRIC_HISTORY = {
    "data": [
        {
            "step": 0,
            "value": 0.8,
            "timestamp": "2025-01-01T00:00:00",
            "attribute_type": "float",
        },
        {
            "step": 1,
            "value": 0.5,
            "timestamp": "2025-01-01T00:01:00",
            "attribute_type": "float",
        },
    ],
    "has_more": False,
    "attribute_type": "float",
}

SAMPLE_CONFIG = {"lr": 0.001, "epochs": 10, "batch_size": 32}

SAMPLE_CONFIG_KEY = {"key": "lr", "value": 0.001}

SAMPLE_TABLES = {
    "tables": [
        {
            "id": 1,
            "project_id": 1,
            "table_id": "TBL-1",
            "name": "predictions",
            "run_id": 1,
            "version": 3,
            "row_count": 150,
            "column_schema": '[{"name": "epoch", "type": "int"}, {"name": "pred", "type": "float"}]',
            "config": None,
            "state": "active",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
    ],
    "total": 1,
    "has_more": False,
}

SAMPLE_TABLE_DETAIL = SAMPLE_TABLES["tables"][0]

SAMPLE_TABLE_DATA = {
    "rows": [{"epoch": 0, "pred": 0.9}, {"epoch": 1, "pred": 0.85}],
    "total": 2,
    "column_schema": [
        {"name": "epoch", "type": "int"},
        {"name": "pred", "type": "float"},
    ],
    "has_more": False,
}

SAMPLE_TABLE_STATS = {
    "columns": {
        "epoch": {"type": "numeric", "min": 0, "max": 1, "bins": [], "null_count": 0},
        "pred": {
            "type": "numeric",
            "min": 0.85,
            "max": 0.9,
            "bins": [
                {"start": 0.85, "end": 0.875, "count": 1},
                {"start": 0.875, "end": 0.9, "count": 1},
            ],
            "null_count": 0,
        },
    }
}


class TestProjects:
    def test_projects_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_PROJECTS))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["projects", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "my-project"

    def test_projects_table_format(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_PROJECTS))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query,
                [
                    "projects",
                    "--format",
                    "table",
                    "--server-url",
                    "http://localhost:8000",
                ],
            )
        assert result.exit_code == 0
        assert "my-project" in result.output


class TestRuns:
    def test_runs_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_RUNS))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["runs", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total"] == 1
        assert data["runs"][0]["run_id"] == "RUN-1"

    def test_runs_with_filters(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_RUNS))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query,
                [
                    "runs",
                    "--state",
                    "completed",
                    "--limit",
                    "10",
                    "--server-url",
                    "http://localhost:8000",
                ],
            )
        assert result.exit_code == 0
        call_kwargs = mock_client.request.call_args
        assert (
            call_kwargs[1].get("params", {}).get("state") == "completed"
            or (call_kwargs[0] if len(call_kwargs[0]) > 2 else {}).get("state")
            == "completed"
            or "state=completed" in str(call_kwargs)
        )


class TestRunDetail:
    def test_run_summary_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_RUN_SUMMARY))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["run", "1", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["metrics"]["loss"] == 0.5
        assert data["config"]["lr"] == 0.001


class TestMetricsList:
    def test_metrics_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_METRICS_LIST))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["metrics", "1", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["path"] == "loss"


class TestMetricHistory:
    def test_metric_history_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_METRIC_HISTORY))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["metric", "1", "loss", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["data"]) == 2
        assert data["data"][0]["step"] == 0

    def test_metric_history_with_step_range(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_METRIC_HISTORY))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query,
                [
                    "metric",
                    "1",
                    "loss",
                    "--step-min",
                    "0",
                    "--step-max",
                    "5",
                    "--server-url",
                    "http://localhost:8000",
                ],
            )
        assert result.exit_code == 0


class TestConfig:
    def test_config_all_keys(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_CONFIG))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["config", "1", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["lr"] == 0.001

    def test_config_specific_key(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_CONFIG_KEY))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["config", "1", "lr", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["key"] == "lr"


class TestTablesList:
    def test_tables_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_TABLES))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["tables", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total"] == 1
        assert data["tables"][0]["table_id"] == "TBL-1"

    def test_tables_with_run_filter(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_TABLES))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query,
                ["tables", "--run-id", "1", "--server-url", "http://localhost:8000"],
            )
        assert result.exit_code == 0


class TestTableDetail:
    def test_table_detail_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_TABLE_DETAIL))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["table", "1", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["table_id"] == "TBL-1"
        assert data["row_count"] == 150


class TestTableData:
    def test_table_data_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_TABLE_DATA))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["table-data", "1", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["rows"]) == 2

    def test_table_data_table_format(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_TABLE_DATA))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query,
                [
                    "table-data",
                    "1",
                    "--format",
                    "table",
                    "--server-url",
                    "http://localhost:8000",
                ],
            )
        assert result.exit_code == 0
        assert "epoch" in result.output


class TestTableStats:
    def test_table_stats_json(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_TABLE_STATS))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["table-stats", "1", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "epoch" in data["columns"]
        assert data["columns"]["epoch"]["type"] == "numeric"

    def test_table_stats_table_format(self):
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_TABLE_STATS))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query,
                [
                    "table-stats",
                    "1",
                    "--format",
                    "table",
                    "--server-url",
                    "http://localhost:8000",
                ],
            )
        assert result.exit_code == 0
        assert "epoch" in result.output
        assert "numeric" in result.output


class TestErrors:
    def test_server_unreachable(self):
        runner = CliRunner()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = httpx.ConnectError("connection refused")
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["projects", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code != 0
        assert (
            "Cannot reach" in result.output
            or "connection refused" in str(result.exception).lower()
            or "Cannot reach" in str(result.exception)
        )

    def test_not_found(self):
        runner = CliRunner()
        mock_client = _mock_client(
            _mock_response({"detail": "not found"}, status_code=404)
        )
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(
                query, ["run", "999", "--server-url", "http://localhost:8000"]
            )
        assert result.exit_code != 0

    def test_env_var_server_url(self, monkeypatch):
        monkeypatch.setenv("DALVA_SERVER_URL", "http://custom:9999")
        runner = CliRunner()
        mock_client = _mock_client(_mock_response(SAMPLE_PROJECTS))
        with patch("dalva.cli.query.httpx.Client", return_value=mock_client):
            result = runner.invoke(query, ["projects"])
        assert result.exit_code == 0
        call_args = mock_client.request.call_args
        url = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("url", "")
        assert "custom:9999" in url or "custom:9999" in str(call_args)
