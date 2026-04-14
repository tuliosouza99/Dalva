"""Tests for dalva sync CLI command — replays pending WAL operations."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner

from dalva.cli.sync import sync


@pytest.fixture
def outbox_dir(tmp_path):
    d = tmp_path / "outbox"
    d.mkdir()
    return d


def _ok_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status.return_value = None
    return resp


def _write_wal(outbox_dir, name, entries):
    filepath = outbox_dir / f"{name}.jsonl"
    lines = []
    for i, entry in enumerate(entries, 1):
        entry.setdefault("seq", i)
        entry.setdefault("method", "POST")
        entry.setdefault("headers", None)
        entry.setdefault("batch_key", None)
        entry.setdefault("batch_count", 0)
        lines.append(json.dumps(entry))
    filepath.write_text("\n".join(lines) + "\n")
    return filepath


class TestSyncStatus:
    def test_status_no_pending(self, outbox_dir):
        runner = CliRunner()
        with patch("dalva.cli.sync.WALManager.list_pending", return_value=[]):
            result = runner.invoke(sync, ["--status", "--outbox", str(outbox_dir)])
        assert result.exit_code == 0
        assert "No pending operations" in result.output

    def test_status_shows_pending_files(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        info = [
            WALFileInfo(
                path=outbox_dir / "run_1.jsonl",
                resource_type="run",
                resource_id=1,
                entry_count=5,
            ),
            WALFileInfo(
                path=outbox_dir / "table_2.jsonl",
                resource_type="table",
                resource_id=2,
                entry_count=3,
            ),
        ]
        runner = CliRunner()
        with patch("dalva.cli.sync.WALManager.list_pending", return_value=info):
            result = runner.invoke(sync, ["--status", "--outbox", str(outbox_dir)])
        assert result.exit_code == 0
        assert "run_1.jsonl" in result.output
        assert "5 operation(s)" in result.output
        assert "table_2.jsonl" in result.output
        assert "3 operation(s)" in result.output


class TestSyncDryRun:
    def test_dry_run_shows_operations_without_sending(self, outbox_dir):
        _write_wal(
            outbox_dir,
            "run_1",
            [
                {
                    "url": "/api/runs/1/log",
                    "payload": {"metrics": {"loss": 0.5}, "step": 0},
                },
                {
                    "url": "/api/runs/1/log",
                    "payload": {"metrics": {"loss": 0.3}, "step": 1},
                },
            ],
        )
        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            from dalva.sdk.wal import WALFileInfo

            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "run_1.jsonl",
                    resource_type="run",
                    resource_id=1,
                    entry_count=2,
                )
            ]
            mock_read.return_value = [
                {
                    "seq": 1,
                    "method": "POST",
                    "url": "/api/runs/1/log",
                    "payload": {"metrics": {"loss": 0.5}, "step": 0},
                    "headers": None,
                    "batch_key": "run:1",
                    "batch_count": 0,
                },
                {
                    "seq": 2,
                    "method": "POST",
                    "url": "/api/runs/1/log",
                    "payload": {"metrics": {"loss": 0.3}, "step": 1},
                    "headers": None,
                    "batch_key": "run:1",
                    "batch_count": 0,
                },
            ]
            result = runner.invoke(sync, ["--dry-run", "--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        assert "Would sync" in result.output
        mock_client_cls.assert_not_called()


class TestSyncReplay:
    def test_replay_sends_requests(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.5}, "step": 0},
                "headers": None,
                "batch_key": "run:1",
                "batch_count": 0,
            },
            {
                "seq": 2,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.3}, "step": 1},
                "headers": None,
                "batch_key": "run:1",
                "batch_count": 0,
            },
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.return_value = _ok_response()

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "run_1.jsonl",
                    resource_type="run",
                    resource_id=1,
                    entry_count=2,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        assert "Synced" in result.output

    def test_replay_batches_batchable_entries(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.5}, "step": 0},
                "headers": None,
                "batch_key": "run:1",
                "batch_count": 0,
            },
            {
                "seq": 2,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.3}, "step": 1},
                "headers": None,
                "batch_key": "run:1",
                "batch_count": 0,
            },
            {
                "seq": 3,
                "method": "POST",
                "url": "/api/runs/1/finish",
                "payload": None,
                "headers": None,
                "batch_key": None,
                "batch_count": 0,
            },
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.return_value = _ok_response()

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "run_1.jsonl",
                    resource_type="run",
                    resource_id=1,
                    entry_count=3,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        batch_call = mock_client.post.call_args_list[0]
        assert "/log/batch" in batch_call[0][0]
        finish_call = mock_client.post.call_args_list[1]
        assert "/finish" in finish_call[0][0]

    def test_replay_409_treated_as_success(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.5}},
                "headers": None,
                "batch_key": None,
                "batch_count": 0,
            },
        ]
        conflict_resp = MagicMock()
        conflict_resp.status_code = 409
        conflict_resp.json.return_value = {"detail": "conflict"}
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "409", request=MagicMock(), response=conflict_resp
        )

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "run_1.jsonl",
                    resource_type="run",
                    resource_id=1,
                    entry_count=1,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        assert "already applied" in result.output or "Synced" in result.output

    def test_replay_partial_failure_keeps_failed(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.5}},
                "headers": None,
                "batch_key": None,
                "batch_count": 0,
            },
            {
                "seq": 2,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.3}},
                "headers": None,
                "batch_key": None,
                "batch_count": 0,
            },
        ]
        error_resp = MagicMock()
        error_resp.status_code = 500
        error_resp.json.return_value = {"detail": "error"}
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.side_effect = [
            _ok_response(),
            httpx.HTTPStatusError("500", request=MagicMock(), response=error_resp),
        ]

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "run_1.jsonl",
                    resource_type="run",
                    resource_id=1,
                    entry_count=2,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        _mock_rewrite.assert_called_once()
        rewritten = _mock_rewrite.call_args[0][1]
        assert len(rewritten) == 1

    def test_replay_server_unreachable_keeps_wal(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.5}},
                "headers": None,
                "batch_key": None,
                "batch_count": 0,
            },
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.side_effect = httpx.ConnectError("connection refused")

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "run_1.jsonl",
                    resource_type="run",
                    resource_id=1,
                    entry_count=1,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        assert "failed" in result.output.lower() or "error" in result.output.lower()
        _mock_rewrite.assert_called_once()
        rewritten = _mock_rewrite.call_args[0][1]
        assert len(rewritten) == 1

    def test_replay_with_finish_appends_finish(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.5}, "step": 0},
                "headers": None,
                "batch_key": "run:1",
                "batch_count": 0,
            },
            {
                "seq": 2,
                "method": "POST",
                "url": "/api/runs/1/finish",
                "payload": None,
                "headers": None,
                "batch_key": None,
                "batch_count": 0,
            },
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.return_value = _ok_response()

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "run_1.jsonl",
                    resource_type="run",
                    resource_id=1,
                    entry_count=2,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        post_calls = mock_client.post.call_args_list
        finish_call = [c for c in post_calls if "/finish" in c[0][0]]
        assert len(finish_call) >= 1

    def test_replay_deletes_wal_on_full_success(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/runs/1/log",
                "payload": {"metrics": {"loss": 0.5}},
                "headers": None,
                "batch_key": None,
                "batch_count": 0,
            },
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.return_value = _ok_response()

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "run_1.jsonl",
                    resource_type="run",
                    resource_id=1,
                    entry_count=1,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        _mock_rewrite.assert_called_once()
        remaining = _mock_rewrite.call_args[0][1]
        assert len(remaining) == 0

    def test_replay_table_entries(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/tables/5/log",
                "payload": '{"rows": [{"col1": 1}], "column_schema": [{"name": "col1", "type": "int"}]}',
                "headers": {"Content-Type": "application/json"},
                "batch_key": None,
                "batch_count": 0,
            },
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.return_value = _ok_response()

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "table_5.jsonl",
                    resource_type="table",
                    resource_id=5,
                    entry_count=1,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        mock_client.post.assert_called_once()
        call = mock_client.post.call_args
        assert "/api/tables/5/log" in call[0][0]

    def test_replay_table_with_custom_headers(self, outbox_dir):
        from dalva.sdk.wal import WALFileInfo

        entries = [
            {
                "seq": 1,
                "method": "POST",
                "url": "/api/tables/5/log",
                "payload": '{"rows": [{"col1": 1}]}',
                "headers": {"Content-Type": "application/json"},
                "batch_key": None,
                "batch_count": 0,
            },
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = _ok_response()
        mock_client.post.return_value = _ok_response()

        runner = CliRunner()
        with (
            patch("dalva.cli.sync.WALManager.list_pending") as mock_list,
            patch("dalva.cli.sync.WALManager.read") as mock_read,
            patch("dalva.cli.sync.WALManager.rewrite") as _mock_rewrite,
            patch("dalva.cli.sync.httpx.Client") as mock_client_cls,
        ):
            mock_list.return_value = [
                WALFileInfo(
                    path=outbox_dir / "table_5.jsonl",
                    resource_type="table",
                    resource_id=5,
                    entry_count=1,
                )
            ]
            mock_read.return_value = entries
            mock_client_cls.return_value = mock_client
            result = runner.invoke(sync, ["--outbox", str(outbox_dir)])

        assert result.exit_code == 0
        call = mock_client.post.call_args
        assert call[1].get("headers") == {"Content-Type": "application/json"}
