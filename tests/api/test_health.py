"""
tests/api/test_health.py

Smoke tests for the /health endpoint.

These are intentionally minimal — they verify that:
  1. The app starts without errors.
  2. The health route is reachable and returns the expected shape.
  3. The response carries the correct version string from config.

This file acts as the base commit for the test suite; controller-specific
tests will be added in subsequent commits.
"""

from fastapi.testclient import TestClient


class TestHealth:
    """Tests for GET /health."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint must respond with HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_shape(self, client: TestClient) -> None:
        """Response must contain 'status' and 'version' fields."""
        response = client.get("/health")
        body = response.json()
        assert "status" in body
        assert "version" in body

    def test_health_status_is_ok(self, client: TestClient) -> None:
        """'status' field must equal 'ok'."""
        response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_health_version_is_string(self, client: TestClient) -> None:
        """'version' field must be a non-empty string."""
        response = client.get("/health")
        version = response.json()["version"]
        assert isinstance(version, str)
        assert len(version) > 0

    def test_health_content_type_is_json(self, client: TestClient) -> None:
        """Response Content-Type must be application/json."""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]
