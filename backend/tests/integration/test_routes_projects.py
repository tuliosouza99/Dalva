"""Tests for projects API routes."""

from dalva.db.schema import Project, Run


class TestListProjects:
    """Tests for GET /api/projects endpoint."""

    def test_list_projects_empty(self, api_client):
        """Test listing projects when no projects exist."""
        response = api_client.get("/api/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(self, api_client, sample_project):
        """Test listing projects when projects exist."""
        response = api_client.get("/api/projects")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["name"] == "test-project"
        assert projects[0]["project_id"] == "test-project_abc123"

    def test_list_projects_with_pagination(self, api_client, db_session):
        """Test listing projects with pagination."""
        # Create multiple projects

        for i in range(5):
            project = Project(
                name=f"project-{i}",
                project_id=f"project_{i}",
            )
            db_session.add(project)
        db_session.commit()

        # Test limit
        response = api_client.get("/api/projects?limit=2")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 2

        # Test offset
        response = api_client.get("/api/projects?limit=2&offset=2")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 2


class TestGetProject:
    """Tests for GET /api/projects/{project_id} endpoint."""

    def test_get_project_success(self, api_client, sample_project):
        """Test getting a project by ID."""
        response = api_client.get(f"/api/projects/{sample_project['id']}")
        assert response.status_code == 200
        project = response.json()
        assert project["name"] == "test-project"
        assert project["project_id"] == "test-project_abc123"
        assert "total_runs" in project
        assert "running_runs" in project

    def test_get_project_not_found(self, api_client):
        """Test getting a non-existent project."""
        response = api_client.get("/api/projects/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"


class TestProjectSummary:
    """Tests for project summary statistics."""

    def test_project_summary_counts(self, api_client, sample_project, sample_run):
        """Test that project summary includes correct run counts."""
        response = api_client.get(f"/api/projects/{sample_project['id']}")
        assert response.status_code == 200
        project = response.json()

        assert project["total_runs"] == 1
        assert project["running_runs"] == 1
        assert project["completed_runs"] == 0
        assert project["failed_runs"] == 0

    def test_project_summary_with_multiple_runs(
        self, api_client, db_session, sample_project
    ):
        """Test project summary with multiple runs in different states."""

        # Create runs with different states
        states = ["running", "completed", "failed", "completed"]
        for i, state in enumerate(states):
            run = Run(
                project_id=sample_project["id"],
                run_id=f"TST-{i + 1}",
                name=f"Run {i + 1}",
                state=state,
            )
            db_session.add(run)
        db_session.commit()

        response = api_client.get(f"/api/projects/{sample_project['id']}")
        assert response.status_code == 200
        project = response.json()

        assert project["total_runs"] == 4
        assert project["running_runs"] == 1
        assert project["completed_runs"] == 2
        assert project["failed_runs"] == 1
