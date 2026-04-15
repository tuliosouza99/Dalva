"""Integration tests for the new schema-based tables API — RED phase."""

import json

import pytest


def _init_table(client, project="test-project", **kwargs):
    payload = {"project": project, "column_schema": [{"name": "x", "type": "int"}]}
    payload.update(kwargs)
    return client.post("/api/tables/init", json=payload)


@pytest.mark.integration
class TestInitTableWithSchema:
    def test_init_table_with_column_schema(self, api_client):
        response = api_client.post(
            "/api/tables/init",
            json={
                "project": "schema-proj",
                "name": "schema-table",
                "column_schema": [
                    {"name": "name", "type": "str"},
                    {"name": "score", "type": "float"},
                    {"name": "count", "type": "int"},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "table_id" in data
        assert data["name"] == "schema-table"
        assert data["version"] == 0

    def test_init_table_without_schema_allowed_for_resume(self, api_client):
        init_resp = api_client.post(
            "/api/tables/init",
            json={
                "project": "resume-test-proj",
                "name": "original-table",
                "column_schema": [{"name": "x", "type": "int"}],
            },
        )
        assert init_resp.status_code == 200
        table_id = init_resp.json()["table_id"]

        resume_resp = api_client.post(
            "/api/tables/init",
            json={
                "project": "resume-test-proj",
                "resume_from": table_id,
            },
        )
        assert resume_resp.status_code == 200
        assert resume_resp.json()["table_id"] == table_id

    def test_init_table_no_log_mode_in_response(self, api_client):
        response = api_client.post(
            "/api/tables/init",
            json={
                "project": "no-logmode-proj",
                "column_schema": [{"name": "x", "type": "int"}],
            },
        )
        assert response.status_code == 200
        assert "log_mode" not in response.json()


@pytest.mark.integration
class TestLogTableRowsSimple:
    def test_log_rows_simple(self, api_client):
        init_resp = _init_table(api_client, name="simple")
        assert init_resp.status_code == 200
        table_id = init_resp.json()["id"]

        log_resp = api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 1}, {"x": 2}]},
        )
        assert log_resp.status_code == 200
        data = log_resp.json()
        assert data["success"] is True
        assert data["rows_added"] == 2

    def test_log_rows_validates_types(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        log_resp = api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": "not_int"}]},
        )
        assert log_resp.status_code == 400

    def test_log_rows_multiple_times(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        r1 = api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 1}]},
        )
        assert r1.status_code == 200

        r2 = api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 2}]},
        )
        assert r2.status_code == 200
        assert r2.json()["version"] == 2

    def test_log_rows_to_finished_table_fails(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        api_client.post(f"/api/tables/{table_id}/finish")

        log_resp = api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 1}]},
        )
        assert log_resp.status_code == 400


@pytest.mark.integration
class TestBatchLogTableRows:
    def test_batch_log_endpoint(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        batch_resp = api_client.post(
            f"/api/tables/{table_id}/log/batch",
            json={
                "entries": [
                    {"rows": [{"x": 1}]},
                    {"rows": [{"x": 2}, {"x": 3}]},
                ],
            },
        )
        assert batch_resp.status_code == 200
        data = batch_resp.json()
        assert data["success"] is True
        assert data["rows_added"] == 3


@pytest.mark.integration
class TestGetTableData:
    def test_get_table_data_returns_all_rows(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 1}, {"x": 2}, {"x": 3}]},
        )

        data_resp = api_client.get(f"/api/tables/{table_id}/data")
        assert data_resp.status_code == 200
        data = data_resp.json()
        assert data["total"] == 3
        assert len(data["rows"]) == 3


@pytest.mark.integration
class TestRemoveAllRows:
    def test_remove_all_rows(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 1}, {"x": 2}]},
        )

        del_resp = api_client.delete(f"/api/tables/{table_id}/rows")
        assert del_resp.status_code == 200

        data_resp = api_client.get(f"/api/tables/{table_id}/data")
        assert data_resp.json()["total"] == 0

        get_resp = api_client.get(f"/api/tables/{table_id}")
        table = get_resp.json()
        assert table["row_count"] == 0
        assert table["version"] == 0

    def test_remove_rows_then_log_again(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 1}]},
        )
        api_client.delete(f"/api/tables/{table_id}/rows")

        log_resp = api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 99}]},
        )
        assert log_resp.status_code == 200

        data_resp = api_client.get(f"/api/tables/{table_id}/data")
        assert data_resp.json()["total"] == 1
        assert data_resp.json()["rows"][0]["x"] == 99


@pytest.mark.integration
class TestStreamTableData:
    def test_stream_returns_ndjson(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        api_client.post(
            f"/api/tables/{table_id}/log",
            json={"rows": [{"x": 1}, {"x": 2}]},
        )

        stream_resp = api_client.get(f"/api/tables/{table_id}/data?stream=true")
        assert stream_resp.status_code == 200
        assert "application/x-ndjson" in stream_resp.headers.get("content-type", "")

        lines = stream_resp.text.strip().split("\n")
        assert len(lines) == 2
        row1 = json.loads(lines[0])
        assert row1["x"] == 1


@pytest.mark.integration
class TestTableResponseNoLogMode:
    def test_table_response_has_no_log_mode(self, api_client):
        init_resp = _init_table(api_client)
        table_id = init_resp.json()["id"]

        get_resp = api_client.get(f"/api/tables/{table_id}")
        assert get_resp.status_code == 200
        assert "log_mode" not in get_resp.json()

    def test_list_tables_no_log_mode(self, api_client):
        _init_table(api_client)

        list_resp = api_client.get("/api/tables/?project_id=1")
        assert list_resp.status_code == 200

        if list_resp.json()["total"] > 0:
            tables = list_resp.json()["tables"]
            for t in tables:
                assert "log_mode" not in t
