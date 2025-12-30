"""Tests for app/config.py module."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


class TestSettingsValidation:
    """Tests for Settings validation."""

    def test_valid_settings(self):
        """Test valid settings creation."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test_user",
            dexcom_password="test_password",
        )
        assert settings.dexcom_username == "test_user"
        assert settings.dexcom_region == "us"

    def test_account_id_auth(self):
        """Test authentication with account ID."""
        from app.config import Settings

        settings = Settings(
            dexcom_account_id="12345",
            dexcom_password="test_password",
        )
        assert settings.dexcom_account_id == "12345"

    def test_missing_auth_fails(self):
        """Test missing authentication credentials fails."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(dexcom_password="test_password")


class TestRegionValidation:
    """Tests for region validation."""

    def test_valid_regions(self):
        """Test valid region values."""
        from app.config import Settings

        for region in ["us", "ous", "jp"]:
            settings = Settings(
                dexcom_username="test",
                dexcom_password="test",
                dexcom_region=region,
            )
            assert settings.dexcom_region == region

    def test_region_case_insensitive(self):
        """Test region is case insensitive."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test",
            dexcom_password="test",
            dexcom_region="US",
        )
        assert settings.dexcom_region == "us"

    def test_invalid_region_fails(self):
        """Test invalid region fails validation."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                dexcom_region="invalid",
            )


class TestColorValidation:
    """Tests for color string validation."""

    def test_valid_color(self):
        """Test valid color string."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test",
            dexcom_password="test",
            color_normal="128,64,32",
        )
        assert settings.color_normal == "128,64,32"

    def test_invalid_color_format(self):
        """Test invalid color format fails."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                color_normal="not-a-color",
            )

    def test_color_out_of_range(self):
        """Test color values out of range fail."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                color_normal="256,0,0",
            )

    def test_color_negative_fails(self):
        """Test negative color values fail."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                color_normal="-1,0,0",
            )


class TestThresholdValidation:
    """Tests for threshold validation."""

    def test_valid_thresholds(self):
        """Test valid threshold ordering."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test",
            dexcom_password="test",
            glucose_critical_low=50,
            glucose_low=70,
            glucose_high=180,
            glucose_very_high=250,
        )
        assert settings.glucose_critical_low == 50

    def test_invalid_threshold_order_fails(self):
        """Test invalid threshold ordering fails."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                glucose_critical_low=100,  # Greater than low
                glucose_low=70,
            )

    def test_delta_threshold_order(self):
        """Test delta thresholds must be ordered."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                delta_stable_threshold=20,
                delta_rapid_threshold=10,  # Less than stable
            )


class TestIndicatorDotValidation:
    """Tests for indicator dot position validation."""

    def test_valid_dot_position(self):
        """Test valid dot position."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test",
            dexcom_password="test",
            indicator_dot_x=31,
            indicator_dot_y=0,
        )
        assert settings.indicator_dot_x == 31

    def test_dot_x_out_of_range(self):
        """Test dot X position out of range fails."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                indicator_dot_x=32,
            )

    def test_dot_y_out_of_range(self):
        """Test dot Y position out of range fails."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                indicator_dot_y=8,
            )


class TestLogLevelValidation:
    """Tests for log level validation."""

    def test_valid_log_levels(self):
        """Test valid log levels."""
        from app.config import Settings

        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(
                dexcom_username="test",
                dexcom_password="test",
                log_level=level,
            )
            assert settings.log_level == level

    def test_log_level_case_insensitive(self):
        """Test log level is case insensitive."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test",
            dexcom_password="test",
            log_level="info",
        )
        assert settings.log_level == "INFO"

    def test_invalid_log_level_fails(self):
        """Test invalid log level fails."""
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                dexcom_username="test",
                dexcom_password="test",
                log_level="INVALID",
            )


class TestParseColor:
    """Tests for parse_color helper method."""

    def test_parse_color(self):
        """Test parsing color string."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test",
            dexcom_password="test",
        )
        color = settings.parse_color("255,128,64")
        assert color == [255, 128, 64]

    def test_parse_color_with_spaces(self):
        """Test parsing color string with spaces."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test",
            dexcom_password="test",
        )
        color = settings.parse_color("255, 128, 64")
        assert color == [255, 128, 64]


class TestGetColorTuple:
    """Tests for get_color_tuple helper method."""

    def test_get_color_tuple(self):
        """Test getting color as tuple."""
        from app.config import Settings

        settings = Settings(
            dexcom_username="test",
            dexcom_password="test",
        )
        color = settings.get_color_tuple("255,128,64")
        assert color == (255, 128, 64)


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_caching(self):
        """Test settings are cached."""
        from app.config import get_settings

        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
