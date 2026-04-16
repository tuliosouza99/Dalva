"""Unit tests for the schema-based Table SDK."""

import json
from unittest.mock import MagicMock, patch

import pytest

from dalva.sdk.errors import DalvaError

from .conftest import _mock_response, _mock_worker


TABLE_INIT_RESPONSE = _mock_response(
    json_data={
        "id": 7,
        "table_id": "TST-T1",
        "name": "test-table",
        "version": 0,
    }
)
TABLE_FINISH_RESPONSE = _mock_response(json_data={"state": "finished"})


def _make_table_mock_client():
    mock_client = MagicMock()
    mock_client.post.side_effect = lambda url, **kw: (
        TABLE_INIT_RESPONSE if "init" in url else TABLE_FINISH_RESPONSE
    )
    mock_client.get.return_value = _mock_response(json_data={})
    mock_client.delete.return_value = _mock_response(json_data={})
    return mock_client


@pytest.mark.unit
class TestTableRequiresSchema:
    def test_table_constructor_requires_schema(self, tmp_path):
        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker"),
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client_class.return_value = _make_table_mock_client()

            from dalva.sdk.table import Table

            with pytest.raises(TypeError, match="schema"):
                Table(project="test-project", outbox_dir=tmp_path / "outbox")

    def test_table_rejects_non_dalva_schema(self, tmp_path):
        from pydantic import BaseModel

        class NotDalva(BaseModel):
            name: str

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker"),
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client_class.return_value = _make_table_mock_client()

            from dalva.sdk.table import Table

            with pytest.raises(TypeError, match="DalvaSchema"):
                Table(
                    project="test-project",
                    schema=NotDalva,
                    outbox_dir=tmp_path / "outbox",
                )


@pytest.mark.unit
class TestTableInit:
    def test_table_sends_column_schema_on_init(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            score: float

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client = _make_table_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker_class.return_value = _mock_worker()

            from dalva.sdk.table import Table

            Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )

            init_call = mock_client.post.call_args_list[0]
            payload = init_call[1]["json"]
            assert payload["column_schema"] == [
                {"name": "name", "type": "str"},
                {"name": "score", "type": "float"},
            ]
            assert "log_mode" not in payload

    def test_table_no_log_mode_on_init(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            x: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client = _make_table_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker_class.return_value = _mock_worker()

            from dalva.sdk.table import Table

            Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )

            init_call = mock_client.post.call_args_list[0]
            payload = init_call[1]["json"]
            assert "log_mode" not in payload


@pytest.mark.unit
class TestTableLogRow:
    def test_log_row_enqueues_single_row(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            score: float

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client_class.return_value = _make_table_mock_client()
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            t.log_row({"name": "test", "score": 0.5})

            mock_worker.enqueue.assert_called_once()
            req = mock_worker.enqueue.call_args[0][0]
            assert req.method == "POST"
            assert f"/api/tables/{t._db_id}/log" in req.url
            assert req.batch_key == f"table:{t._db_id}"

            payload = json.loads(req.payload)
            assert len(payload["rows"]) == 1
            assert payload["rows"][0]["name"] == "test"
            assert payload["rows"][0]["score"] == 0.5

    def test_log_row_validates_against_schema(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            count: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client_class.return_value = _make_table_mock_client()
            mock_worker_class.return_value = _mock_worker()

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            with pytest.raises(Exception, match=""):
                t.log_row({"count": "not_a_number"})

    def test_log_row_raises_on_finished(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            x: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client_class.return_value = _make_table_mock_client()
            mock_worker_class.return_value = _mock_worker()

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            t._finished = True
            with pytest.raises(RuntimeError, match="finished"):
                t.log_row({"x": 1})


@pytest.mark.unit
class TestTableLogRows:
    def test_log_rows_enqueues_multiple_rows(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            val: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client_class.return_value = _make_table_mock_client()
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            t.log_rows(
                [
                    {"name": "a", "val": 1},
                    {"name": "b", "val": 2},
                    {"name": "c", "val": 3},
                ]
            )

            mock_worker.enqueue.assert_called_once()
            req = mock_worker.enqueue.call_args[0][0]
            payload = json.loads(req.payload)
            assert len(payload["rows"]) == 3
            assert payload["rows"][0]["name"] == "a"

    def test_log_rows_validates_all_rows(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            x: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client_class.return_value = _make_table_mock_client()
            mock_worker_class.return_value = _mock_worker()

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            with pytest.raises(Exception, match=""):
                t.log_rows(
                    [
                        {"x": 1},
                        {"x": "bad"},
                        {"x": 3},
                    ]
                )


@pytest.mark.unit
class TestTableGetTable:
    def test_get_table_returns_list_of_dicts(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            x: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client = _make_table_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker_class.return_value = _mock_worker()

            data_response = _mock_response(
                json_data={
                    "rows": [{"x": 1}, {"x": 2}],
                    "total": 2,
                    "column_schema": [{"name": "x", "type": "int"}],
                    "has_more": False,
                }
            )
            mock_client.get.side_effect = lambda url, **kw: (
                data_response if "/data" in url else _mock_response(json_data={})
            )

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            rows = t.get_table()
            assert rows == [{"x": 1}, {"x": 2}]

    def test_get_table_with_pagination(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            x: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client = _make_table_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker_class.return_value = _mock_worker()

            page1 = _mock_response(
                json_data={
                    "rows": [{"x": i} for i in range(100)],
                    "total": 150,
                    "column_schema": [{"name": "x", "type": "int"}],
                    "has_more": True,
                }
            )
            page2 = _mock_response(
                json_data={
                    "rows": [{"x": i} for i in range(100, 150)],
                    "total": 150,
                    "column_schema": [{"name": "x", "type": "int"}],
                    "has_more": False,
                }
            )
            mock_client.get.side_effect = [page1, page2]

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            rows = t.get_table()
            assert len(rows) == 150


@pytest.mark.unit
class TestTableRemoveTable:
    def test_remove_table_calls_delete_rows_endpoint(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            x: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager"),
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client = _make_table_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker_class.return_value = _mock_worker()

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            t.remove_table()

            mock_client.delete.assert_called_once()
            call_url = mock_client.delete.call_args[0][0]
            assert f"/api/tables/{t._db_id}/rows" in call_url


@pytest.mark.unit
class TestTableFinish:
    def test_finish_matches_run_pattern(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            x: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager") as mock_wal_class,
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client = _make_table_mock_client()
            mock_client_class.return_value = mock_client
            mock_worker = _mock_worker()
            mock_worker_class.return_value = mock_worker
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            t.finish()

            assert t._finished is True
            mock_worker.wal_delete.assert_called_once()

    def test_finish_with_errors_raises_dalva_error(self, tmp_path):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            x: int

        with (
            patch("dalva.sdk.table.httpx.Client") as mock_client_class,
            patch("dalva.sdk.table.SyncWorker") as mock_worker_class,
            patch("dalva.sdk.table.WALManager") as mock_wal_class,
            patch("dalva.sdk.table.httpx.get") as mock_get,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_client = _make_table_mock_client()
            mock_client_class.return_value = mock_client

            error = Exception("boom")
            req = MagicMock()
            mock_worker = _mock_worker(errors=[(req, error)])
            mock_worker_class.return_value = mock_worker
            mock_wal = MagicMock()
            mock_wal_class.return_value = mock_wal

            from dalva.sdk.table import Table

            t = Table(
                project="test-project",
                schema=MySchema,
                outbox_dir=tmp_path / "outbox",
            )
            with pytest.raises(DalvaError):
                t.finish(on_error="raise")
