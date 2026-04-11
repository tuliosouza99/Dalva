"""Tests for metrics API routes."""


class TestListMetrics:
    """Tests for GET /api/metrics/runs/{run_id} endpoint."""

    def test_list_metrics_empty(self, api_client, sample_run):
        """Test listing metrics when no metrics exist."""
        response = api_client.get(f"/api/metrics/runs/{sample_run['id']}")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_metrics_with_data(
        self,
        api_client,
        sample_run,
        sample_metrics,
    ):
        """Test listing metrics when metrics exist."""
        response = api_client.get(f"/api/metrics/runs/{sample_run['id']}")
        assert response.status_code == 200
        metrics = response.json()
        assert len(metrics) == 2
        paths = [m["path"] for m in metrics]
        assert "loss" in paths
        assert "accuracy" in paths
        for m in metrics:
            assert "path" in m
            assert "attribute_type" in m

    def test_list_metrics_run_not_found(self, api_client):
        """Test listing metrics for non-existent run."""
        response = api_client.get("/api/metrics/runs/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Run not found"


class TestGetMetricValues:
    """Tests for GET /api/metrics/runs/{run_id}/metric/{metric_path} endpoint."""

    def test_get_metric_values_success(self, api_client, sample_run, sample_metrics):
        """Test getting metric values."""
        response = api_client.get(f"/api/metrics/runs/{sample_run['id']}/metric/loss")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["has_more"] is False

        # Check first value (loss at step 0 is 0.5)
        first_value = data["data"][0]
        assert first_value["step"] == 0
        assert first_value["value"] == 0.5

    def test_get_metric_values_with_pagination(
        self, api_client, sample_run, sample_metrics
    ):
        """Test getting metric values with pagination."""
        response = api_client.get(
            f"/api/metrics/runs/{sample_run['id']}/metric/loss?limit=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["has_more"] is True

    def test_get_metric_values_with_step_filter(
        self, api_client, sample_run, sample_metrics
    ):
        """Test getting metric values with step range filter."""
        response = api_client.get(
            f"/api/metrics/runs/{sample_run['id']}/metric/loss?step_min=1&step_max=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["step"] == 1

    def test_get_metric_values_run_not_found(self, api_client):
        """Test getting metric values for non-existent run."""
        response = api_client.get("/api/metrics/runs/99999/metric/loss")
        assert response.status_code == 404
        assert response.json()["detail"] == "Run not found"

    def test_get_metric_values_metric_not_found(self, api_client, sample_run):
        """Test getting values for non-existent metric."""
        response = api_client.get(
            f"/api/metrics/runs/{sample_run['id']}/metric/nonexistent"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


class TestMetricValuesResponse:
    """Tests for metric value response format."""

    def test_metric_values_response_format(self, api_client, sample_run):
        """Test that metric values response has correct format."""
        response = api_client.get(f"/api/metrics/runs/{sample_run['id']}/metric/loss")
        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "has_more" in data
        assert isinstance(data["data"], list)

        if data["data"]:
            value = data["data"][0]
            assert "step" in value
            assert "value" in value
            assert "timestamp" in value

    def test_metric_values_ordering(self, api_client, sample_run):
        """Test that metric values are ordered by step."""
        response = api_client.get(f"/api/metrics/runs/{sample_run['id']}/metric/loss")
        data = response.json()

        steps = [v["step"] for v in data["data"]]
        assert steps == sorted(steps)
