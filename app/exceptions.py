"""
Custom exceptions for the Dexcom AWTRIX Bridge application.

This module provides structured error handling with clear error codes
and user-friendly messages for better debugging and UX.
"""

from enum import Enum
from typing import Optional


class ErrorCode(str, Enum):
    """Standardized error codes for the application."""

    # Dexcom API Errors (1xxx)
    DEXCOM_AUTH_FAILED = "DEXCOM_1001"
    DEXCOM_API_ERROR = "DEXCOM_1002"
    DEXCOM_NO_DATA = "DEXCOM_1003"
    DEXCOM_RATE_LIMITED = "DEXCOM_1004"
    DEXCOM_CONNECTION_ERROR = "DEXCOM_1005"

    # Configuration Errors (2xxx)
    CONFIG_INVALID = "CONFIG_2001"
    CONFIG_MISSING_REQUIRED = "CONFIG_2002"
    CONFIG_INVALID_COLOR = "CONFIG_2003"
    CONFIG_INVALID_THRESHOLD = "CONFIG_2004"

    # AWTRIX Errors (3xxx)
    AWTRIX_CONNECTION_ERROR = "AWTRIX_3001"
    AWTRIX_PUSH_FAILED = "AWTRIX_3002"

    # Bridge Errors (4xxx)
    BRIDGE_FETCH_ERROR = "BRIDGE_4001"
    BRIDGE_CONFIG_ERROR = "BRIDGE_4002"


class DexcomAwtrixError(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details
        self.original_error = original_error
        super().__init__(self.full_message)

    @property
    def full_message(self) -> str:
        """Returns the complete error message with code and details."""
        parts = [f"[{self.error_code.value}] {self.message}"]
        if self.details:
            parts.append(f"Details: {self.details}")
        if self.original_error:
            parts.append(f"Caused by: {type(self.original_error).__name__}: {self.original_error}")
        return " | ".join(parts)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }


class DexcomAuthError(DexcomAwtrixError):
    """Raised when Dexcom authentication fails."""

    def __init__(
        self,
        message: str = "Failed to authenticate with Dexcom",
        details: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.DEXCOM_AUTH_FAILED,
            details=details,
            original_error=original_error,
        )


class DexcomAPIError(DexcomAwtrixError):
    """Raised when Dexcom API call fails."""

    def __init__(
        self,
        message: str = "Dexcom API request failed",
        details: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.DEXCOM_API_ERROR,
            details=details,
            original_error=original_error,
        )


class DexcomNoDataError(DexcomAwtrixError):
    """Raised when no glucose data is available from Dexcom."""

    def __init__(
        self,
        message: str = "No glucose data available",
        details: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.DEXCOM_NO_DATA,
            details=details,
        )


class DexcomRateLimitedError(DexcomAwtrixError):
    """Raised when rate limit is hit (informational, usually returns cached data)."""

    def __init__(
        self,
        seconds_remaining: int,
        message: str = "Rate limited by Dexcom API policy",
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.DEXCOM_RATE_LIMITED,
            details=f"Next refresh available in {seconds_remaining} seconds",
        )
        self.seconds_remaining = seconds_remaining


class DexcomConnectionError(DexcomAwtrixError):
    """Raised when connection to Dexcom fails."""

    def __init__(
        self,
        message: str = "Failed to connect to Dexcom servers",
        details: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.DEXCOM_CONNECTION_ERROR,
            details=details,
            original_error=original_error,
        )


class ConfigurationError(DexcomAwtrixError):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str = "Invalid configuration",
        error_code: ErrorCode = ErrorCode.CONFIG_INVALID,
        details: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
        )


class InvalidColorError(ConfigurationError):
    """Raised when a color configuration is invalid."""

    def __init__(self, color_name: str, color_value: str):
        super().__init__(
            message=f"Invalid color value for '{color_name}'",
            error_code=ErrorCode.CONFIG_INVALID_COLOR,
            details=f"Expected 'R,G,B' format with values 0-255, got: '{color_value}'",
        )


class InvalidThresholdError(ConfigurationError):
    """Raised when threshold values are invalid."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIG_INVALID_THRESHOLD,
            details=details,
        )


class AwtrixConnectionError(DexcomAwtrixError):
    """Raised when connection to AWTRIX device fails."""

    def __init__(
        self,
        awtrix_ip: str,
        message: str = "Failed to connect to AWTRIX device",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.AWTRIX_CONNECTION_ERROR,
            details=f"AWTRIX IP: {awtrix_ip}",
            original_error=original_error,
        )


class AwtrixPushError(DexcomAwtrixError):
    """Raised when pushing data to AWTRIX fails."""

    def __init__(
        self,
        message: str = "Failed to push data to AWTRIX display",
        details: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.AWTRIX_PUSH_FAILED,
            details=details,
            original_error=original_error,
        )


class BridgeFetchError(DexcomAwtrixError):
    """Raised when bridge fails to fetch data from cloud service."""

    def __init__(
        self,
        cloud_url: str,
        message: str = "Failed to fetch glucose data from cloud service",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.BRIDGE_FETCH_ERROR,
            details=f"Cloud URL: {cloud_url}",
            original_error=original_error,
        )


class BridgeConfigError(DexcomAwtrixError):
    """Raised when bridge configuration is invalid."""

    def __init__(
        self,
        message: str = "Invalid bridge configuration",
        details: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.BRIDGE_CONFIG_ERROR,
            details=details,
        )
