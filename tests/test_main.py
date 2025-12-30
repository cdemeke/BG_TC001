"""Tests for app/main.py API endpoints."""

import pytest
from unittest.mock import MagicMock, patch


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_health(self, test_client):
        """Test root endpoint returns healthy status."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "dexcom-awtrix-bridge"


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self, test_client):
        """Test health endpoint returns ok status."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


class TestGlucoseEndpoint:
    """Tests for the glucose AWTRIX endpoint."""

    def test_glucose_returns_awtrix_format(self, test_client):
        """Test glucose endpoint returns AWTRIX format."""
        response = test_client.get("/glucose")
        assert response.status_code == 200
        data = response.json()

        # Check AWTRIX response fields
        assert "text" in data
        assert "color" in data
        assert "draw" in data

    def test_glucose_has_progress(self, test_client):
        """Test glucose endpoint has progress bar."""
        response = test_client.get("/glucose")
        assert response.status_code == 200
        data = response.json()

        assert "progress" in data
        assert "progressC" in data
        assert "progressBC" in data

    def test_glucose_has_request_id_header(self, test_client):
        """Test glucose endpoint has request ID header."""
        response = test_client.get("/glucose")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_glucose_has_response_time_header(self, test_client):
        """Test glucose endpoint has response time header."""
        response = test_client.get("/glucose")
        assert "X-Response-Time" in response.headers
        assert "ms" in response.headers["X-Response-Time"]


class TestGlucoseRawEndpoint:
    """Tests for the raw glucose endpoint."""

    def test_raw_returns_glucose_data(self, test_client, sample_glucose_data):
        """Test raw endpoint returns glucose data."""
        response = test_client.get("/glucose/raw")
        assert response.status_code == 200
        data = response.json()

        assert data["value"] == sample_glucose_data.value
        assert data["delta"] == sample_glucose_data.delta
        assert "trend_arrow" in data


class TestGlucoseStatusEndpoint:
    """Tests for the glucose status endpoint."""

    def test_status_returns_timing_info(self, test_client):
        """Test status endpoint returns timing info."""
        response = test_client.get("/glucose/status")
        assert response.status_code == 200
        data = response.json()

        assert "seconds_until_next_refresh" in data
        assert "refresh_progress_percent" in data
        assert "can_refresh_now" in data
        assert "statistics" in data

    def test_status_has_next_refresh_time(self, test_client):
        """Test status endpoint has next refresh time."""
        response = test_client.get("/glucose/status")
        assert response.status_code == 200
        data = response.json()

        # Should have next_refresh_at since we mocked 150 seconds remaining
        if data["seconds_until_next_refresh"] > 0:
            assert "next_refresh_at" in data


class TestGlucoseStatisticsEndpoint:
    """Tests for the statistics endpoint."""

    def test_statistics_returns_counts(self, test_client):
        """Test statistics endpoint returns counts."""
        response = test_client.get("/glucose/statistics")
        assert response.status_code == 200
        data = response.json()

        assert "total_api_calls" in data
        assert "cache_hits" in data
        assert "api_errors" in data
        assert "cache_hit_rate" in data


class TestErrorHandling:
    """Tests for error handling."""

    def test_no_data_returns_503(self, test_client, mock_dexcom_client):
        """Test no data returns 503 status."""
        mock_dexcom_client.get_current_reading.return_value = (None, 0)

        response = test_client.get("/glucose")
        assert response.status_code == 503

    def test_no_data_has_error_format(self, test_client, mock_dexcom_client):
        """Test no data error has proper format."""
        mock_dexcom_client.get_current_reading.return_value = (None, 0)

        response = test_client.get("/glucose")
        data = response.json()

        assert "error" in data
        assert "message" in data


class TestMiddleware:
    """Tests for request middleware."""

    def test_all_endpoints_have_request_id(self, test_client):
        """Test all endpoints have request ID header."""
        endpoints = ["/", "/health", "/glucose", "/glucose/raw", "/glucose/status"]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            assert "X-Request-ID" in response.headers, f"Missing X-Request-ID for {endpoint}"

    def test_all_endpoints_have_response_time(self, test_client):
        """Test all endpoints have response time header."""
        endpoints = ["/", "/health", "/glucose", "/glucose/raw", "/glucose/status"]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            assert "X-Response-Time" in response.headers, f"Missing X-Response-Time for {endpoint}"
