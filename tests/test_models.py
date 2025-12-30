"""Tests for app/models.py module."""

import pytest

from app.models import AwtrixResponse, GlucoseData, HealthResponse


class TestGlucoseData:
    """Tests for GlucoseData model."""

    def test_minimal_creation(self):
        """Test creation with minimal fields."""
        data = GlucoseData(value=120)
        assert data.value == 120
        assert data.delta is None

    def test_full_creation(self):
        """Test creation with all fields."""
        data = GlucoseData(
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
        assert data.value == 120
        assert data.mmol_l == 6.7
        assert data.delta == 5

    def test_negative_delta(self):
        """Test negative delta values."""
        data = GlucoseData(value=100, delta=-10)
        assert data.delta == -10


class TestAwtrixResponse:
    """Tests for AwtrixResponse model."""

    def test_minimal_creation(self):
        """Test creation with minimal fields."""
        response = AwtrixResponse(
            text="120",
            color=[0, 255, 0],
        )
        assert response.text == "120"
        assert response.color == [0, 255, 0]

    def test_full_creation(self):
        """Test creation with all fields."""
        response = AwtrixResponse(
            text="120",
            color=[0, 255, 0],
            icon="glucose",
            duration=10,
            noScroll=True,
            center=True,
            lifetime=120,
            background=[32, 32, 32],
            blinkText=500,
            progress=50,
            progressC=[0, 255, 255],
            progressBC=[32, 32, 32],
            draw=[{"dt": [0, 0, "120", "#00ff00"]}],
        )
        assert response.progress == 50
        assert len(response.draw) == 1

    def test_default_values(self):
        """Test default values are applied."""
        response = AwtrixResponse(text="", color=[0, 0, 0])
        assert response.noScroll is True
        assert response.center is True
        assert response.duration == 10


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_creation(self):
        """Test basic creation."""
        response = HealthResponse(
            status="healthy",
            service="test-service",
        )
        assert response.status == "healthy"
        assert response.service == "test-service"
