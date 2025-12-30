"""
Pytest configuration and shared fixtures for the test suite.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set environment variables before importing app modules
os.environ["DEXCOM_USERNAME"] = "test_user"
os.environ["DEXCOM_PASSWORD"] = "test_password"
os.environ["DEXCOM_REGION"] = "us"


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from app.config import Settings

    # Clear the LRU cache
    from app.config import get_settings
    get_settings.cache_clear()

    return Settings(
        dexcom_username="test_user",
        dexcom_password="test_password",
        dexcom_region="us",
    )


@pytest.fixture
def sample_glucose_data():
    """Create sample glucose data for testing."""
    from app.models import GlucoseData

    return GlucoseData(
        value=120,
        mmol_l=6.7,
        trend=4,
        trend_direction="Flat",
        trend_description="Flat",
        trend_arrow="→",
        timestamp="2024-01-15T10:30:00",
        delta=5,
        previous_value=115,
    )


@pytest.fixture
def mock_dexcom_client(sample_glucose_data):
    """Create a mock DexcomClient."""
    from app.dexcom_client import DexcomClient, reset_dexcom_client

    reset_dexcom_client()

    mock_client = MagicMock(spec=DexcomClient)
    mock_client.get_current_reading.return_value = (sample_glucose_data, 50)
    mock_client.get_seconds_until_next_call.return_value = 150
    mock_client.get_refresh_progress.return_value = 50
    mock_client.get_statistics.return_value = {
        "total_api_calls": 10,
        "cache_hits": 50,
        "api_errors": 0,
        "cache_hit_rate": 0.83,
        "has_cached_data": True,
        "last_error": None,
        "last_error_time": None,
    }

    return mock_client


@pytest.fixture
def test_client(mock_dexcom_client, mock_settings):
    """Create a test client with mocked dependencies."""
    from app.main import app
    from app.dexcom_client import get_dexcom_client
    from app.config import get_settings

    def get_mock_client():
        return mock_dexcom_client

    def get_mock_settings():
        return mock_settings

    app.dependency_overrides[get_dexcom_client] = get_mock_client
    app.dependency_overrides[get_settings] = get_mock_settings

    client = TestClient(app)

    yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def glucose_values():
    """Provide test glucose values for different thresholds."""
    return {
        "critical_low": 50,
        "low": 65,
        "normal": 120,
        "high": 200,
        "very_high": 280,
    }


@pytest.fixture
def delta_values():
    """Provide test delta values for different arrow types."""
    return {
        "stable": 3,
        "moderate_up": 10,
        "moderate_down": -10,
        "rapid_up": 20,
        "rapid_down": -20,
    }
