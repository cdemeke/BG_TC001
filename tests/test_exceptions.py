"""Tests for app/exceptions.py module."""

import pytest

from app.exceptions import (
    AwtrixConnectionError,
    AwtrixPushError,
    BridgeConfigError,
    BridgeFetchError,
    ConfigurationError,
    DexcomAPIError,
    DexcomAuthError,
    DexcomAwtrixError,
    DexcomConnectionError,
    DexcomNoDataError,
    DexcomRateLimitedError,
    ErrorCode,
    InvalidColorError,
    InvalidThresholdError,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_dexcom_error_codes(self):
        """Test Dexcom error codes are defined."""
        assert ErrorCode.DEXCOM_AUTH_FAILED.value == "DEXCOM_1001"
        assert ErrorCode.DEXCOM_API_ERROR.value == "DEXCOM_1002"
        assert ErrorCode.DEXCOM_NO_DATA.value == "DEXCOM_1003"

    def test_config_error_codes(self):
        """Test config error codes are defined."""
        assert ErrorCode.CONFIG_INVALID.value == "CONFIG_2001"
        assert ErrorCode.CONFIG_INVALID_COLOR.value == "CONFIG_2003"

    def test_awtrix_error_codes(self):
        """Test AWTRIX error codes are defined."""
        assert ErrorCode.AWTRIX_CONNECTION_ERROR.value == "AWTRIX_3001"
        assert ErrorCode.AWTRIX_PUSH_FAILED.value == "AWTRIX_3002"


class TestDexcomAwtrixError:
    """Tests for base DexcomAwtrixError exception."""

    def test_basic_creation(self):
        """Test basic error creation."""
        error = DexcomAwtrixError(
            message="Test error",
            error_code=ErrorCode.DEXCOM_API_ERROR,
        )
        assert error.message == "Test error"
        assert error.error_code == ErrorCode.DEXCOM_API_ERROR

    def test_with_details(self):
        """Test error with details."""
        error = DexcomAwtrixError(
            message="Test error",
            error_code=ErrorCode.DEXCOM_API_ERROR,
            details="Additional info",
        )
        assert error.details == "Additional info"
        assert "Additional info" in error.full_message

    def test_with_original_error(self):
        """Test error with original exception."""
        original = ValueError("Original error")
        error = DexcomAwtrixError(
            message="Test error",
            error_code=ErrorCode.DEXCOM_API_ERROR,
            original_error=original,
        )
        assert error.original_error is original
        assert "ValueError" in error.full_message

    def test_to_dict(self):
        """Test conversion to dictionary."""
        error = DexcomAwtrixError(
            message="Test error",
            error_code=ErrorCode.DEXCOM_API_ERROR,
            details="Extra info",
        )
        d = error.to_dict()
        assert d["error"] == "DEXCOM_1002"
        assert d["message"] == "Test error"
        assert d["details"] == "Extra info"


class TestDexcomAuthError:
    """Tests for DexcomAuthError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = DexcomAuthError()
        assert "authenticate" in error.message.lower()
        assert error.error_code == ErrorCode.DEXCOM_AUTH_FAILED

    def test_custom_message(self):
        """Test custom error message."""
        error = DexcomAuthError(message="Custom auth error")
        assert error.message == "Custom auth error"


class TestDexcomAPIError:
    """Tests for DexcomAPIError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = DexcomAPIError()
        assert "api" in error.message.lower() or "request" in error.message.lower()
        assert error.error_code == ErrorCode.DEXCOM_API_ERROR

    def test_with_original_error(self):
        """Test with original exception."""
        original = ConnectionError("Network error")
        error = DexcomAPIError(original_error=original)
        assert error.original_error is original


class TestDexcomNoDataError:
    """Tests for DexcomNoDataError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = DexcomNoDataError()
        assert "data" in error.message.lower()
        assert error.error_code == ErrorCode.DEXCOM_NO_DATA


class TestDexcomRateLimitedError:
    """Tests for DexcomRateLimitedError exception."""

    def test_includes_seconds(self):
        """Test error includes remaining seconds."""
        error = DexcomRateLimitedError(seconds_remaining=120)
        assert error.seconds_remaining == 120
        assert "120" in error.details
        assert error.error_code == ErrorCode.DEXCOM_RATE_LIMITED


class TestDexcomConnectionError:
    """Tests for DexcomConnectionError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = DexcomConnectionError()
        assert "connect" in error.message.lower()
        assert error.error_code == ErrorCode.DEXCOM_CONNECTION_ERROR


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_default_error_code(self):
        """Test default error code."""
        error = ConfigurationError()
        assert error.error_code == ErrorCode.CONFIG_INVALID


class TestInvalidColorError:
    """Tests for InvalidColorError exception."""

    def test_includes_color_info(self):
        """Test error includes color information."""
        error = InvalidColorError(color_name="color_normal", color_value="bad")
        assert "color_normal" in error.message
        assert "bad" in error.details
        assert error.error_code == ErrorCode.CONFIG_INVALID_COLOR


class TestInvalidThresholdError:
    """Tests for InvalidThresholdError exception."""

    def test_includes_message(self):
        """Test error includes message."""
        error = InvalidThresholdError(message="Low must be less than high")
        assert "Low must be less than high" in error.message
        assert error.error_code == ErrorCode.CONFIG_INVALID_THRESHOLD


class TestAwtrixConnectionError:
    """Tests for AwtrixConnectionError exception."""

    def test_includes_ip(self):
        """Test error includes AWTRIX IP."""
        error = AwtrixConnectionError(awtrix_ip="192.168.1.100")
        assert "192.168.1.100" in error.details
        assert error.error_code == ErrorCode.AWTRIX_CONNECTION_ERROR


class TestAwtrixPushError:
    """Tests for AwtrixPushError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = AwtrixPushError()
        assert "push" in error.message.lower()
        assert error.error_code == ErrorCode.AWTRIX_PUSH_FAILED


class TestBridgeFetchError:
    """Tests for BridgeFetchError exception."""

    def test_includes_url(self):
        """Test error includes cloud URL."""
        error = BridgeFetchError(cloud_url="https://example.com")
        assert "https://example.com" in error.details
        assert error.error_code == ErrorCode.BRIDGE_FETCH_ERROR


class TestBridgeConfigError:
    """Tests for BridgeConfigError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = BridgeConfigError()
        assert "config" in error.message.lower()
        assert error.error_code == ErrorCode.BRIDGE_CONFIG_ERROR
