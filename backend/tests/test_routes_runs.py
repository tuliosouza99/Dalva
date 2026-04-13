"""Tests for runs API routes."""

from datetime import datetime, timezone


class TestForkRun:
    """Tests for POST /api/runs/init with fork_from."""

    def test_fork_run_basic(self, api_client, sample_run, sample_project):
        """Test forking a run with fork_from creates a new run with copied data."""
        response = api_client.post(
            "/api/runs/init",
            json={
                "project": sample_project["name"],
                "name": "forked-run",
                "fork_from": sample_run["run_id"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "forked-run"
        assert data["id"] != sample_run["id"]

        forked_run_id = data["id"]
        forked_run = api_client.get(f"/api/runs/{forked_run_id}").json()
        assert forked_run["name"] == "forked-run"
        assert forked_run["state"] == "running"
        assert forked_run["fork_from"] == sample_run["id"]

    def test_fork_run_copies_configs(self, api_client, db_session):
        """Test that forked run has copies of source run's configs."""
        from dalva.db.schema import Config, Project, Run

        project = Project(name="config-fork-project", project_id="cfg_fork_123")
        db_session.add(project)
        db_session.commit()

        source_run = Run(project_id=project.id, run_id="SRC-1", name="Source Run")
        db_session.add(source_run)
        db_session.commit()

        db_session.add(Config(run_id=source_run.id, key="lr", value="0.001"))
        db_session.add(Config(run_id=source_run.id, key="batch_size", value="32"))
        db_session.commit()

        response = api_client.post(
            "/api/runs/init",
            json={"project": "config-fork-project", "fork_from": "SRC-1"},
        )
        assert response.status_code == 200
        forked_id = response.json()["id"]

        configs_response = api_client.get(f"/api/runs/{forked_id}/config")
        configs = configs_response.json()
        assert "lr" in configs
        assert configs["lr"] == 0.001
        assert "batch_size" in configs
        assert configs["batch_size"] == 32

    def test_fork_run_copies_metrics(self, api_client, db_session):
        """Test that forked run has copies of source run's metrics."""
        from dalva.db.schema import Metric, Project, Run

        project = Project(name="metric-fork-project", project_id="mtr_fork_123")
        db_session.add(project)
        db_session.commit()

        source_run = Run(project_id=project.id, run_id="SRC-2", name="Source Run")
        db_session.add(source_run)
        db_session.commit()

        db_session.add(
            Metric(
                run_id=source_run.id,
                attribute_path="loss",
                attribute_type="float",
                step=None,
                float_value=0.5,
                timestamp=datetime.now(timezone.utc),
            )
        )
        db_session.add(
            Metric(
                run_id=source_run.id,
                attribute_path="accuracy",
                attribute_type="float",
                step=None,
                float_value=0.95,
                timestamp=datetime.now(timezone.utc),
            )
        )
        db_session.commit()

        response = api_client.post(
            "/api/runs/init",
            json={"project": "metric-fork-project", "fork_from": "SRC-2"},
        )
        assert response.status_code == 200
        forked_id = response.json()["id"]

        summary = api_client.get(f"/api/runs/{forked_id}/summary").json()
        assert "loss" in summary["metrics"]
        assert "accuracy" in summary["metrics"]

    def test_fork_run_with_copy_tables_true(
        self, api_client, db_session, sample_project
    ):
        """Test forking with copy_tables_on_fork=true copies all tables and rows."""
        from dalva.db.schema import DalvaTable, DalvaTableRow, Run

        source_run = Run(
            project_id=sample_project["id"], run_id="TBL-1", name="Table Source"
        )
        db_session.add(source_run)
        db_session.commit()

        table = DalvaTable(
            project_id=sample_project["id"],
            run_id=source_run.id,
            table_id="MY-TABLE-1",
            name="My Table",
            column_schema='[{"name": "col1", "type": "int"}]',
        )
        db_session.add(table)
        db_session.commit()

        row = DalvaTableRow(table_id=table.id, row_data='{"col1": 100}')
        db_session.add(row)
        db_session.commit()

        response = api_client.post(
            "/api/runs/init",
            json={
                "project": sample_project["name"],
                "name": "table-fork-run",
                "fork_from": "TBL-1",
                "copy_tables_on_fork": True,
            },
        )
        assert response.status_code == 200
        forked_id = response.json()["id"]

        tables = api_client.get(f"/api/runs/{forked_id}/tables").json()
        assert len(tables) == 1
        assert tables[0]["name"] == "My Table"
        assert tables[0]["row_count"] == 1

    def test_fork_run_with_copy_tables_list(
        self, api_client, db_session, sample_project
    ):
        """Test forking with copy_tables_on_fork=[id] copies only specified table."""
        from dalva.db.schema import DalvaTable, Run

        source_run = Run(
            project_id=sample_project["id"], run_id="TBL-2", name="Multi Table Source"
        )
        db_session.add(source_run)
        db_session.commit()

        table1 = DalvaTable(
            project_id=sample_project["id"],
            run_id=source_run.id,
            table_id="KEEP-ME",
            name="Keep Me",
        )
        table2 = DalvaTable(
            project_id=sample_project["id"],
            run_id=source_run.id,
            table_id="SKIP-ME",
            name="Skip Me",
        )
        db_session.add(table1)
        db_session.add(table2)
        db_session.commit()

        response = api_client.post(
            "/api/runs/init",
            json={
                "project": sample_project["name"],
                "fork_from": "TBL-2",
                "copy_tables_on_fork": [table1.id],
            },
        )
        assert response.status_code == 200
        forked_id = response.json()["id"]

        tables = api_client.get(f"/api/runs/{forked_id}/tables").json()
        assert len(tables) == 1
        assert tables[0]["name"] == "Keep Me"

    def test_fork_run_not_found(self, api_client):
        """Test forking from non-existent run returns 404."""
        response = api_client.post(
            "/api/runs/init",
            json={"project": "ghost-project", "fork_from": "NONEXISTENT-1"},
        )
        assert response.status_code == 404

    def test_fork_run_default_name(self, api_client, sample_run, sample_project):
        """Test that forked run without name gets 'fork of {source_name}'."""
        response = api_client.post(
            "/api/runs/init",
            json={"project": sample_project["name"], "fork_from": sample_run["run_id"]},
        )
        assert response.status_code == 200
        assert response.json()["name"] == f"fork of {sample_run['name']}"

    def test_fork_run_no_tables_when_false(
        self, api_client, db_session, sample_project
    ):
        """Test that fork with copy_tables_on_fork=false does not copy tables."""
        from dalva.db.schema import DalvaTable, Run

        source_run = Run(
            project_id=sample_project["id"], run_id="NO-TBL", name="No Table Source"
        )
        db_session.add(source_run)
        db_session.commit()

        table = DalvaTable(
            project_id=sample_project["id"],
            run_id=source_run.id,
            table_id="ORPHAN-TABLE",
            name="Orphan Table",
        )
        db_session.add(table)
        db_session.commit()

        response = api_client.post(
            "/api/runs/init",
            json={
                "project": sample_project["name"],
                "fork_from": "NO-TBL",
                "copy_tables_on_fork": False,
            },
        )
        assert response.status_code == 200
        forked_id = response.json()["id"]

        tables = api_client.get(f"/api/runs/{forked_id}/tables").json()
        assert len(tables) == 0


class TestListRuns:
    """Tests for GET /api/runs endpoint."""

    def test_list_runs_empty(self, api_client):
        """Test listing runs when no runs exist."""
        response = api_client.get("/api/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["total"] == 0
        assert data["has_more"] is False

    def test_list_runs_with_data(self, api_client, sample_run):
        """Test listing runs when runs exist."""
        response = api_client.get("/api/runs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == "TST-1"
        assert data["total"] == 1

    def test_list_runs_filter_by_project(self, api_client, sample_project, sample_run):
        """Test filtering runs by project_id."""
        response = api_client.get(f"/api/runs?project_id={sample_project['id']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 1

        # Filter by non-existent project
        response = api_client.get("/api/runs?project_id=99999")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 0

    def test_list_runs_filter_by_state(self, api_client, sample_run):
        """Test filtering runs by state."""
        response = api_client.get("/api/runs?state=running")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 1

        response = api_client.get("/api/runs?state=completed")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 0

    def test_list_runs_filter_by_group(self, api_client, db_session, sample_run):
        """Test filtering runs by group name."""
        # Update run with group
        sample_run["group_name"] = "experiment-a"
        from dalva.db.schema import Run

        run = db_session.get(Run, sample_run["id"])
        run.group_name = "experiment-a"
        db_session.commit()

        response = api_client.get("/api/runs?group=experiment-a")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 1

        response = api_client.get("/api/runs?group=experiment-b")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 0

    def test_list_runs_search(self, api_client, sample_run):
        """Test searching runs by run_id or name."""
        response = api_client.get("/api/runs?search=TST")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 1

        response = api_client.get("/api/runs?search=Test")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 1

        response = api_client.get("/api/runs?search=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 0

    def test_list_runs_pagination(self, api_client, db_session, sample_project):
        """Test pagination of runs list."""
        from dalva.db.schema import Run

        # Create 5 runs
        for i in range(5):
            run = Run(
                project_id=sample_project["id"],
                run_id=f"TST-{i + 1}",
                name=f"Run {i + 1}",
                state="running",
            )
            db_session.add(run)
        db_session.commit()

        # Test limit
        response = api_client.get("/api/runs?limit=2")
        data = response.json()
        assert len(data["runs"]) == 2
        assert data["has_more"] is True

        # Test offset
        response = api_client.get("/api/runs?limit=2&offset=2")
        data = response.json()
        assert len(data["runs"]) == 2
        assert data["total"] == 5

    def test_list_runs_sorting(self, api_client, db_session, sample_project):
        """Test sorting of runs list."""
        from dalva.db.schema import Run

        # Create runs with different names
        names = ["aaa-run", "zzz-run", "mmm-run"]
        for name in names:
            run = Run(
                project_id=sample_project["id"],
                run_id=name.replace("-", ""),
                name=name,
                state="running",
            )
            db_session.add(run)
        db_session.commit()

        # Sort ascending
        response = api_client.get("/api/runs?sort_by=name&sort_order=asc")
        data = response.json()
        assert data["runs"][0]["name"] == "aaa-run"

        # Sort descending
        response = api_client.get("/api/runs?sort_by=name&sort_order=desc")
        data = response.json()
        assert data["runs"][0]["name"] == "zzz-run"


class TestGetRun:
    """Tests for GET /api/runs/{run_id} endpoint."""

    def test_get_run_success(self, api_client, sample_run):
        """Test getting a run by ID."""
        response = api_client.get(f"/api/runs/{sample_run['id']}")
        assert response.status_code == 200
        run = response.json()
        assert run["run_id"] == "TST-1"
        assert run["name"] == "Test Run"
        assert run["state"] == "running"

    def test_get_run_not_found(self, api_client):
        """Test getting a non-existent run."""
        response = api_client.get("/api/runs/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Run not found"
