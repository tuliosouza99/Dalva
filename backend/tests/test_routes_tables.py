"""Tests for tables API routes."""

from dalva.db.schema import DalvaTable


class TestListTables:
    """Tests for GET /api/tables/ endpoint."""

    def test_list_tables_requires_project_or_run(self, api_client):
        response = api_client.get("/api/tables/")
        assert response.status_code == 400

    def test_list_tables_by_project(self, api_client, sample_project, sample_table):
        response = api_client.get(f"/api/tables/?project_id={sample_project['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["tables"][0]["table_id"] == "TST-T1"

    def test_list_tables_by_project_empty(self, api_client, sample_project):
        response = api_client.get(f"/api/tables/?project_id={sample_project['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["tables"] == []

    def test_list_tables_by_nonexistent_project(self, api_client):
        response = api_client.get("/api/tables/?project_id=99999")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_tables_by_run(
        self, api_client, sample_project, sample_run, db_session
    ):
        table = DalvaTable(
            project_id=sample_project["id"],
            table_id="TST-T2",
            name="Linked Table",
            run_id=sample_run["id"],
            log_mode="IMMUTABLE",
            version=0,
            row_count=0,
            column_schema="[]",
            state="active",
        )
        db_session.add(table)
        db_session.commit()

        response = api_client.get(f"/api/tables/?run_id={sample_run['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["tables"][0]["name"] == "Linked Table"

    def test_list_tables_pagination(self, api_client, sample_project, db_session):
        for i in range(5):
            table = DalvaTable(
                project_id=sample_project["id"],
                table_id=f"TST-T{i + 1}",
                name=f"Table {i + 1}",
                log_mode="IMMUTABLE",
                version=0,
                row_count=0,
                column_schema="[]",
                state="active",
            )
            db_session.add(table)
        db_session.commit()

        response = api_client.get(
            f"/api/tables/?project_id={sample_project['id']}&limit=2"
        )
        data = response.json()
        assert len(data["tables"]) == 2
        assert data["has_more"] is True

        response = api_client.get(
            f"/api/tables/?project_id={sample_project['id']}&limit=2&offset=2"
        )
        data = response.json()
        assert len(data["tables"]) == 2
        assert data["total"] == 5


class TestGetTable:
    """Tests for GET /api/tables/{table_id} endpoint."""

    def test_get_table_success(self, api_client, sample_table):
        response = api_client.get(f"/api/tables/{sample_table['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["table_id"] == "TST-T1"
        assert data["name"] == "Test Table"
        assert data["log_mode"] == "IMMUTABLE"
        assert data["state"] == "active"

    def test_get_table_not_found(self, api_client):
        response = api_client.get("/api/tables/99999")
        assert response.status_code == 404


class TestInitTable:
    """Tests for POST /api/tables/init endpoint."""

    def test_init_table_minimal(self, api_client):
        response = api_client.post(
            "/api/tables/init",
            json={"project": "new-project", "log_mode": "IMMUTABLE"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["table_id"] is not None
        assert data["log_mode"] == "IMMUTABLE"
        assert data["version"] == 0

    def test_init_table_with_name(self, api_client):
        response = api_client.post(
            "/api/tables/init",
            json={"project": "new-project", "name": "My Table", "log_mode": "MUTABLE"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Table"
        assert data["log_mode"] == "MUTABLE"

    def test_init_table_default_log_mode(self, api_client):
        response = api_client.post(
            "/api/tables/init",
            json={"project": "new-project"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["log_mode"] == "IMMUTABLE"

    def test_init_table_with_run_id(self, api_client, sample_run):
        response = api_client.post(
            "/api/tables/init",
            json={
                "project": "test-project",
                "name": "Run Table",
                "run_id": sample_run["id"],
                "log_mode": "INCREMENTAL",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["table_id"] is not None

    def test_init_table_resume_mutable(self, api_client):
        init_resp = api_client.post(
            "/api/tables/init",
            json={"project": "resume-proj", "name": "T1", "log_mode": "MUTABLE"},
        )
        table_id = init_resp.json()["table_id"]

        resume_resp = api_client.post(
            "/api/tables/init",
            json={"project": "resume-proj", "resume_from": table_id},
        )
        assert resume_resp.status_code == 200
        assert resume_resp.json()["table_id"] == table_id

    def test_init_table_resume_immutable_fails(self, api_client):
        init_resp = api_client.post(
            "/api/tables/init",
            json={"project": "resume-proj", "name": "T1", "log_mode": "IMMUTABLE"},
        )
        table_id = init_resp.json()["table_id"]

        resume_resp = api_client.post(
            "/api/tables/init",
            json={"project": "resume-proj", "resume_from": table_id},
        )
        assert resume_resp.status_code == 400


class TestLogTableRows:
    """Tests for POST /api/tables/{table_id}/log endpoint."""

    def test_log_rows_immutable(self, api_client, sample_table):
        response = api_client.post(
            f"/api/tables/{sample_table['id']}/log",
            json={
                "rows": [
                    {"col1": 1, "col2": "a"},
                    {"col1": 2, "col2": "b"},
                ],
                "column_schema": [
                    {"name": "col1", "type": "int"},
                    {"name": "col2", "type": "str"},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["rows_added"] == 2
        assert data["version"] == 1

    def test_log_rows_immutable_twice_fails(self, api_client, sample_table):
        api_client.post(
            f"/api/tables/{sample_table['id']}/log",
            json={
                "rows": [{"col1": 1}],
                "column_schema": [{"name": "col1", "type": "int"}],
            },
        )
        response = api_client.post(
            f"/api/tables/{sample_table['id']}/log",
            json={
                "rows": [{"col1": 2}],
                "column_schema": [{"name": "col1", "type": "int"}],
            },
        )
        assert response.status_code == 400

    def test_log_rows_mutable(self, api_client):
        init_resp = api_client.post(
            "/api/tables/init",
            json={"project": "mutable-proj", "name": "M1", "log_mode": "MUTABLE"},
        )
        table_id = init_resp.json()["id"]

        for i in range(3):
            resp = api_client.post(
                f"/api/tables/{table_id}/log",
                json={
                    "rows": [{"x": i}],
                    "column_schema": [{"name": "x", "type": "int"}],
                },
            )
            assert resp.status_code == 200
            assert resp.json()["version"] == i + 1

    def test_log_rows_incremental(self, api_client):
        init_resp = api_client.post(
            "/api/tables/init",
            json={"project": "inc-proj", "name": "I1", "log_mode": "INCREMENTAL"},
        )
        table_id = init_resp.json()["id"]

        resp1 = api_client.post(
            f"/api/tables/{table_id}/log",
            json={
                "rows": [{"x": 1}],
                "column_schema": [{"name": "x", "type": "int"}],
            },
        )
        assert resp1.status_code == 200

        resp2 = api_client.post(
            f"/api/tables/{table_id}/log",
            json={
                "rows": [{"x": 2}],
                "column_schema": [{"name": "x", "type": "int"}],
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["rows_added"] == 1

    def test_log_rows_incremental_schema_mismatch(self, api_client):
        init_resp = api_client.post(
            "/api/tables/init",
            json={"project": "inc-proj2", "name": "I2", "log_mode": "INCREMENTAL"},
        )
        table_id = init_resp.json()["id"]

        api_client.post(
            f"/api/tables/{table_id}/log",
            json={
                "rows": [{"x": 1}],
                "column_schema": [{"name": "x", "type": "int"}],
            },
        )

        resp = api_client.post(
            f"/api/tables/{table_id}/log",
            json={
                "rows": [{"x": "hi"}],
                "column_schema": [{"name": "x", "type": "str"}],
            },
        )
        assert resp.status_code == 400

    def test_log_rows_finished_table_fails(self, api_client, sample_table, db_session):
        table = db_session.query(DalvaTable).get(sample_table["id"])
        table.state = "finished"
        db_session.commit()

        response = api_client.post(
            f"/api/tables/{sample_table['id']}/log",
            json={
                "rows": [{"col1": 1}],
                "column_schema": [{"name": "col1", "type": "int"}],
            },
        )
        assert response.status_code == 400

    def test_log_rows_table_not_found(self, api_client):
        response = api_client.post(
            "/api/tables/99999/log",
            json={
                "rows": [{"col1": 1}],
                "column_schema": [{"name": "col1", "type": "int"}],
            },
        )
        assert response.status_code == 404


class TestGetTableData:
    """Tests for GET /api/tables/{table_id}/data endpoint."""

    def _create_table_with_data(self, api_client, project="data-proj"):
        init_resp = api_client.post(
            "/api/tables/init",
            json={"project": project, "name": "D1", "log_mode": "IMMUTABLE"},
        )
        table_id = init_resp.json()["id"]

        api_client.post(
            f"/api/tables/{table_id}/log",
            json={
                "rows": [
                    {"name": "alice", "score": 95},
                    {"name": "bob", "score": 80},
                    {"name": "charlie", "score": 90},
                ],
                "column_schema": [
                    {"name": "name", "type": "str"},
                    {"name": "score", "type": "int"},
                ],
            },
        )
        return table_id

    def test_get_table_data_basic(self, api_client):
        table_id = self._create_table_with_data(api_client)
        response = api_client.get(f"/api/tables/{table_id}/data")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["rows"]) == 3
        assert len(data["column_schema"]) == 2

    def test_get_table_data_pagination(self, api_client):
        table_id = self._create_table_with_data(api_client)
        response = api_client.get(f"/api/tables/{table_id}/data?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["rows"]) == 2
        assert data["has_more"] is True

        response = api_client.get(f"/api/tables/{table_id}/data?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["rows"]) == 1
        assert data["has_more"] is False

    def test_get_table_data_sort_asc(self, api_client):
        table_id = self._create_table_with_data(api_client)
        response = api_client.get(
            f"/api/tables/{table_id}/data?sort_by=score&sort_order=asc"
        )
        assert response.status_code == 200
        rows = response.json()["rows"]
        assert rows[0]["name"] == "bob"
        assert rows[-1]["name"] == "alice"

    def test_get_table_data_sort_desc(self, api_client):
        table_id = self._create_table_with_data(api_client)
        response = api_client.get(
            f"/api/tables/{table_id}/data?sort_by=score&sort_order=desc"
        )
        assert response.status_code == 200
        rows = response.json()["rows"]
        assert rows[0]["name"] == "alice"
        assert rows[-1]["name"] == "bob"

    def test_get_table_data_not_found(self, api_client):
        response = api_client.get("/api/tables/99999/data")
        assert response.status_code == 404


class TestFinishTable:
    """Tests for POST /api/tables/{table_id}/finish endpoint."""

    def test_finish_table(self, api_client, sample_table):
        response = api_client.post(f"/api/tables/{sample_table['id']}/finish")
        assert response.status_code == 200
        assert response.json()["state"] == "finished"

    def test_finish_table_not_found(self, api_client):
        response = api_client.post("/api/tables/99999/finish")
        assert response.status_code == 404


class TestDeleteTable:
    """Tests for DELETE /api/tables/{table_id} endpoint."""

    def test_delete_table(self, api_client, sample_table):
        response = api_client.delete(f"/api/tables/{sample_table['id']}")
        assert response.status_code == 200

        response = api_client.get(f"/api/tables/{sample_table['id']}")
        assert response.status_code == 404

    def test_delete_table_not_found(self, api_client):
        response = api_client.delete("/api/tables/99999")
        assert response.status_code == 404


class TestGetRunTables:
    """Tests for GET /api/runs/{run_id}/tables endpoint."""

    def test_get_run_tables(self, api_client, sample_project, sample_run, db_session):
        table = DalvaTable(
            project_id=sample_project["id"],
            table_id="TST-RT1",
            name="Run Table",
            run_id=sample_run["id"],
            log_mode="IMMUTABLE",
            version=0,
            row_count=0,
            column_schema="[]",
            state="active",
        )
        db_session.add(table)
        db_session.commit()

        response = api_client.get(f"/api/runs/{sample_run['id']}/tables")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Run Table"

    def test_get_run_tables_empty(self, api_client, sample_run):
        response = api_client.get(f"/api/runs/{sample_run['id']}/tables")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_run_tables_run_not_found(self, api_client):
        response = api_client.get("/api/runs/99999/tables")
        assert response.status_code == 404
