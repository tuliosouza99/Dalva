"""Integration test: crash -> WAL -> dalva sync -> data recovered.

Uses real WAL files on disk, then replays via the sync logic against the
real FastAPI TestClient (real DB). No mocks for the server or DB layer.
"""

import json
from unittest.mock import MagicMock

import httpx
import pytest

from dalva.cli.sync import _replay_file
from dalva.sdk.wal import WALManager
from dalva.sdk.worker import PendingRequest, SyncWorker


class TestCrashAndSyncRun:
    def test_manual_wal_then_sync_recovers_metrics(
        self, api_client, sample_run, tmp_path
    ):
        """Simulate: worker wrote WAL entries then crashed.
        Sync replays them against the real API -> data recovered."""
        db_id = sample_run["id"]
        outbox = tmp_path / "outbox"

        wal = WALManager("run", db_id, outbox_dir=outbox)
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/log",
                payload={"metrics": {"loss": 0.9}, "step": 0},
                batch_key=f"run:{db_id}",
            )
        )
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/log",
                payload={"metrics": {"loss": 0.6}, "step": 1},
                batch_key=f"run:{db_id}",
            )
        )
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/log",
                payload={"metrics": {"loss": 0.3}, "step": 2},
                batch_key=f"run:{db_id}",
            )
        )
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/finish",
            )
        )
        assert wal.exists

        pending = WALManager.list_pending(outbox_dir=outbox)
        assert len(pending) == 1
        assert pending[0].entry_count == 4

        ok, fail, _ = _replay_file(api_client, pending[0])
        assert ok == 4
        assert fail == 0

        assert not wal.exists

        get_resp = api_client.get(f"/api/runs/{db_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["state"] == "completed"

        from dalva.db.connection import session_scope
        from dalva.db.schema import Metric

        with session_scope() as session:
            metrics = (
                session.query(Metric)
                .filter(Metric.run_id == db_id)
                .order_by(Metric.step)
                .all()
            )
            assert len(metrics) == 3
            assert metrics[0].float_value == pytest.approx(0.9)
            assert metrics[1].float_value == pytest.approx(0.6)
            assert metrics[2].float_value == pytest.approx(0.3)

    def test_partial_delivery_then_sync(self, api_client, sample_run, tmp_path):
        """Some metrics already delivered before crash. Sync fills the gap."""
        db_id = sample_run["id"]
        outbox = tmp_path / "outbox"

        api_client.post(
            f"/api/runs/{db_id}/log",
            json={"metrics": {"loss": 0.8}, "step": 0},
        )

        wal = WALManager("run", db_id, outbox_dir=outbox)
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/log",
                payload={"metrics": {"loss": 0.5}, "step": 1},
                batch_key=f"run:{db_id}",
            )
        )
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/log",
                payload={"metrics": {"loss": 0.2}, "step": 2},
                batch_key=f"run:{db_id}",
            )
        )
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/finish",
            )
        )

        pending = WALManager.list_pending(outbox_dir=outbox)
        ok, fail, _ = _replay_file(api_client, pending[0])
        assert ok == 3
        assert fail == 0

        from dalva.db.connection import session_scope
        from dalva.db.schema import Metric

        with session_scope() as session:
            metrics = (
                session.query(Metric)
                .filter(Metric.run_id == db_id)
                .order_by(Metric.step)
                .all()
            )
            assert len(metrics) == 3
            assert metrics[0].float_value == pytest.approx(0.8)
            assert metrics[1].float_value == pytest.approx(0.5)
            assert metrics[2].float_value == pytest.approx(0.2)

    def test_real_worker_crash_then_sync(
        self, api_client, sample_run, tmp_path, monkeypatch
    ):
        """Real SyncWorker can't reach server (ConnectError), writes to WAL.
        Sync replays WAL against real API -> all data recovered."""
        db_id = sample_run["id"]
        outbox = tmp_path / "outbox"
        wal = WALManager("run", db_id, outbox_dir=outbox)

        with monkeypatch.context() as m:
            mock_client = MagicMock()
            mock_client.post.side_effect = httpx.ConnectError("server down")
            m.setattr("dalva.sdk.worker.httpx.Client", lambda **kw: mock_client)

            worker = SyncWorker(
                "http://localhost:9999",
                wal_manager=wal,
                max_retries=0,
                flush_interval=0.05,
            )

            worker.enqueue(
                PendingRequest(
                    method="POST",
                    url=f"/api/runs/{db_id}/log",
                    payload={"metrics": {"loss": 0.9}, "step": 0},
                    batch_key=f"run:{db_id}",
                )
            )
            worker.enqueue(
                PendingRequest(
                    method="POST",
                    url=f"/api/runs/{db_id}/log",
                    payload={"metrics": {"loss": 0.7}, "step": 1},
                    batch_key=f"run:{db_id}",
                )
            )
            worker.enqueue(
                PendingRequest(
                    method="POST",
                    url=f"/api/runs/{db_id}/log",
                    payload={"metrics": {"loss": 0.4}, "step": 2},
                    batch_key=f"run:{db_id}",
                )
            )

            drained = worker.drain(timeout=5)
            assert drained is True
            assert len(worker.errors) == 1

            worker.dump_remaining()
            worker.stop()

        assert wal.exists

        pending = WALManager.list_pending(outbox_dir=outbox)
        assert len(pending) == 1

        wal_entries = WALManager.read(wal.path)
        assert len(wal_entries) >= 3

        ok, fail, _ = _replay_file(api_client, pending[0])
        assert ok >= 3
        assert fail == 0

        assert not wal.exists

        from dalva.db.connection import session_scope
        from dalva.db.schema import Metric

        with session_scope() as session:
            metrics = (
                session.query(Metric)
                .filter(Metric.run_id == db_id)
                .order_by(Metric.step)
                .all()
            )
            assert len(metrics) == 3
            assert metrics[0].float_value == pytest.approx(0.9)
            assert metrics[1].float_value == pytest.approx(0.7)
            assert metrics[2].float_value == pytest.approx(0.4)


class TestCrashAndSyncTable:
    def test_table_crash_then_sync(self, api_client, sample_table, tmp_path):
        db_id = sample_table["id"]
        outbox = tmp_path / "outbox"

        wal = WALManager("table", db_id, outbox_dir=outbox)
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/tables/{db_id}/log",
                payload=json.dumps(
                    {
                        "rows": [{"col1": 1, "col2": "a"}, {"col1": 2, "col2": "b"}],
                        "column_schema": [
                            {"name": "col1", "type": "int"},
                            {"name": "col2", "type": "str"},
                        ],
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
        )
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/tables/{db_id}/finish",
            )
        )

        pending = WALManager.list_pending(outbox_dir=outbox)
        ok, fail, _ = _replay_file(api_client, pending[0])
        assert ok == 2
        assert fail == 0

        get_resp = api_client.get(f"/api/tables/{db_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["state"] == "finished"

        data_resp = api_client.get(f"/api/tables/{db_id}/data")
        assert data_resp.status_code == 200
        rows = data_resp.json()["rows"]
        assert len(rows) == 2


class TestSyncIdempotency:
    def test_409_conflict_treated_as_success(self, api_client, sample_run, tmp_path):
        db_id = sample_run["id"]
        outbox = tmp_path / "outbox"

        api_client.post(
            f"/api/runs/{db_id}/log",
            json={"metrics": {"loss": 0.5}, "step": 0},
        )

        wal = WALManager("run", db_id, outbox_dir=outbox)
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/log",
                payload={"metrics": {"loss": 0.5}, "step": 0},
                batch_key=f"run:{db_id}",
            )
        )

        pending = WALManager.list_pending(outbox_dir=outbox)
        ok, fail, _ = _replay_file(api_client, pending[0])
        assert ok == 1
        assert fail == 0
        assert not wal.exists


class TestSyncPartialFailure:
    def test_partial_failure_keeps_failed_in_wal(
        self, api_client, sample_run, tmp_path
    ):
        db_id = sample_run["id"]
        outbox = tmp_path / "outbox"

        wal = WALManager("run", db_id, outbox_dir=outbox)
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/log",
                payload={"metrics": {"loss": 0.5}, "step": 0},
            )
        )
        wal.append(
            PendingRequest(
                method="POST",
                url="/api/runs/999999/log",
                payload={"metrics": {"loss": 0.3}, "step": 1},
            )
        )
        wal.append(
            PendingRequest(
                method="POST",
                url=f"/api/runs/{db_id}/log",
                payload={"metrics": {"loss": 0.2}, "step": 2},
            )
        )

        pending = WALManager.list_pending(outbox_dir=outbox)
        ok, fail, failed_entries = _replay_file(api_client, pending[0])
        assert fail == 1
        assert len(failed_entries) == 1
        assert "/999999/" in failed_entries[0]["url"]

        assert wal.exists
        remaining = WALManager.read(wal.path)
        assert len(remaining) == 1
