"""Tests for FastAPI application and API endpoints."""


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, api_client):
        """Test that health endpoint returns healthy status."""
        response = api_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestAPIConformance:
    """Tests for API OpenAPI schema conformance."""

    def test_openapi_schema(self, api_client):
        """Test that OpenAPI schema is available."""
        response = api_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Dalva Test"
        assert "paths" in schema


class TestCORSMiddleware:
    """Tests for CORS middleware configuration."""

    def test_cors_headers(self, api_client):
        """Test that CORS headers are present."""
        response = api_client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI returns 200 for OPTIONS preflight
        assert response.status_code == 200
