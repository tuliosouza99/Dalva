"""Tests for runs API routes."""


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
        from trackai.db.schema import Run

        run = db_session.query(Run).get(sample_run["id"])
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
        from trackai.db.schema import Run

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
        from trackai.db.schema import Run

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
