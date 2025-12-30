"""
Dexcom API client with rate limiting, caching, and robust error handling.

This module provides a thread-safe wrapper around the pydexcom library
with built-in rate limiting to respect Dexcom API limits.
"""

import logging
import threading
from datetime import datetime
from typing import Optional, Tuple

from pydexcom import Dexcom

from .config import Settings
from .constants import (
    GLUCOSE_READINGS_COUNT,
    GLUCOSE_READINGS_MINUTES,
    MIN_API_INTERVAL_SECONDS,
)
from .exceptions import (
    DexcomAPIError,
    DexcomAuthError,
    DexcomConnectionError,
    DexcomNoDataError,
)
from .models import GlucoseData

logger = logging.getLogger(__name__)


class DexcomClient:
    """
    Thread-safe Dexcom API wrapper with rate limiting and caching.

    Features:
    - Rate limiting: Enforces 5-minute minimum interval between API calls
    - Caching: Returns cached data when rate limited
    - Thread safety: All state access is protected by locks
    - Graceful degradation: Returns cached data on API errors
    """

    def __init__(self, settings: Settings):
        """
        Initialize the Dexcom client.

        Args:
            settings: Application settings with Dexcom credentials
        """
        self.settings = settings
        self._dexcom: Optional[Dexcom] = None
        self._lock = threading.Lock()
        self._last_error: Optional[str] = None
        self._last_error_time: Optional[datetime] = None

        # Rate limiting state
        self._last_api_call: Optional[datetime] = None
        self._cached_data: Optional[GlucoseData] = None

        # Statistics for monitoring
        self._total_api_calls: int = 0
        self._cache_hits: int = 0
        self._api_errors: int = 0

    def _get_dexcom_client(self) -> Dexcom:
        """
        Lazily initialize the Dexcom client.

        Supports authentication via username/password or account_id/password.

        Returns:
            Initialized Dexcom client

        Raises:
            DexcomAuthError: If authentication fails
        """
        if self._dexcom is None:
            logger.info(
                "Initializing Dexcom client",
                extra={
                    "region": self.settings.dexcom_region,
                    "auth_method": "account_id" if self.settings.dexcom_account_id else "username",
                }
            )

            try:
                if self.settings.dexcom_account_id:
                    self._dexcom = Dexcom(
                        account_id=self.settings.dexcom_account_id,
                        password=self.settings.dexcom_password,
                        region=self.settings.dexcom_region,
                    )
                else:
                    self._dexcom = Dexcom(
                        username=self.settings.dexcom_username,
                        password=self.settings.dexcom_password,
                        region=self.settings.dexcom_region,
                    )
            except Exception as e:
                raise DexcomAuthError(
                    message="Failed to authenticate with Dexcom",
                    details=f"Region: {self.settings.dexcom_region}",
                    original_error=e,
                )

        return self._dexcom

    def get_seconds_until_next_call(self) -> int:
        """
        Get seconds remaining until next API call is allowed.

        Returns:
            Number of seconds until next refresh (0 if ready now)
        """
        with self._lock:
            return self._get_seconds_until_next_call_unlocked()

    def get_refresh_progress(self) -> int:
        """
        Get progress towards next refresh as percentage (0-100).

        Returns:
            Progress percentage where 100 = ready to refresh, 0 = just refreshed
        """
        with self._lock:
            return self._get_refresh_progress_unlocked()

    def get_statistics(self) -> dict:
        """
        Get client statistics for monitoring.

        Returns:
            Dictionary with API call statistics
        """
        with self._lock:
            return {
                "total_api_calls": self._total_api_calls,
                "cache_hits": self._cache_hits,
                "api_errors": self._api_errors,
                "cache_hit_rate": (
                    self._cache_hits / (self._total_api_calls + self._cache_hits)
                    if (self._total_api_calls + self._cache_hits) > 0
                    else 0
                ),
                "has_cached_data": self._cached_data is not None,
                "last_error": self._last_error,
                "last_error_time": self._last_error_time.isoformat() if self._last_error_time else None,
            }

    def _get_refresh_progress_unlocked(self) -> int:
        """Internal: Get refresh progress without acquiring lock."""
        if self._last_api_call is None:
            return 100

        elapsed = (datetime.now() - self._last_api_call).total_seconds()
        progress = min(100, int((elapsed / MIN_API_INTERVAL_SECONDS) * 100))
        return progress

    def _can_call_api_unlocked(self) -> bool:
        """Internal: Check if API call is allowed without acquiring lock."""
        if self._last_api_call is None:
            return True

        elapsed = (datetime.now() - self._last_api_call).total_seconds()
        return elapsed >= MIN_API_INTERVAL_SECONDS

    def _get_seconds_until_next_call_unlocked(self) -> int:
        """Internal: Get seconds until next call without acquiring lock."""
        if self._last_api_call is None:
            return 0

        elapsed = (datetime.now() - self._last_api_call).total_seconds()
        remaining = max(0, MIN_API_INTERVAL_SECONDS - elapsed)
        return int(remaining)

    def get_current_reading(self) -> Tuple[Optional[GlucoseData], int]:
        """
        Get current glucose reading with rate limiting.

        Returns:
            Tuple of (GlucoseData or None, progress_percentage)
            - progress_percentage: 0-100, where 100 = ready for next refresh

        Rate Limiting:
            - API calls are limited to once per 5 minutes
            - Returns cached data when rate limited
            - Returns cached data on API errors if available

        Raises:
            DexcomNoDataError: If no data available and no cache
            DexcomAPIError: If API call fails and no cache available
        """
        # Check rate limit
        with self._lock:
            if not self._can_call_api_unlocked():
                if self._cached_data is not None:
                    progress = self._get_refresh_progress_unlocked()
                    seconds_remaining = self._get_seconds_until_next_call_unlocked()
                    self._cache_hits += 1

                    logger.debug(
                        "Rate limited: returning cached data",
                        extra={
                            "seconds_remaining": seconds_remaining,
                            "progress_percent": progress,
                            "cached_value": self._cached_data.value,
                        }
                    )
                    return self._cached_data, progress

                # No cached data but rate limited - allow the call anyway
                logger.warning(
                    "Rate limited but no cached data available - allowing API call"
                )

        # Fetch fresh data from Dexcom
        try:
            dexcom = self._get_dexcom_client()
            glucose_data = self._fetch_glucose_readings(dexcom)

            # Update cache and statistics
            with self._lock:
                self._cached_data = glucose_data
                self._last_api_call = datetime.now()
                self._last_error = None
                self._last_error_time = None
                self._total_api_calls += 1

            self._log_successful_reading(glucose_data)
            return glucose_data, 0  # 0% = just refreshed

        except (DexcomNoDataError, DexcomAPIError, DexcomAuthError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            return self._handle_api_error(e)

    def _fetch_glucose_readings(self, dexcom: Dexcom) -> GlucoseData:
        """
        Fetch glucose readings from Dexcom API.

        Args:
            dexcom: Initialized Dexcom client

        Returns:
            GlucoseData with current reading and delta

        Raises:
            DexcomNoDataError: If no readings available
            DexcomAPIError: If API call fails
        """
        try:
            # Try to get last 2 readings to calculate delta
            readings = dexcom.get_glucose_readings(
                minutes=GLUCOSE_READINGS_MINUTES,
                max_count=GLUCOSE_READINGS_COUNT,
            )

            if not readings:
                # Fallback to single reading
                logger.info(
                    "get_glucose_readings returned empty, trying get_latest_glucose_reading"
                )
                latest = dexcom.get_latest_glucose_reading()
                if latest:
                    readings = [latest]
                else:
                    with self._lock:
                        self._last_api_call = datetime.now()  # Prevent hammering
                    raise DexcomNoDataError(
                        message="No glucose readings available",
                        details="Both get_glucose_readings and get_latest_glucose_reading returned empty",
                    )

        except DexcomNoDataError:
            raise
        except Exception as e:
            raise DexcomAPIError(
                message="Failed to fetch glucose readings from Dexcom",
                details=f"Region: {self.settings.dexcom_region}",
                original_error=e,
            )

        # Process readings
        current = readings[0]
        previous = readings[1] if len(readings) > 1 else None

        # Calculate delta
        delta = None
        previous_value = None
        if previous is not None:
            delta = current.value - previous.value
            previous_value = previous.value

        return GlucoseData(
            value=current.value,
            mmol_l=current.mmol_l,
            trend=current.trend,
            trend_direction=current.trend_direction,
            trend_description=current.trend_description,
            trend_arrow=current.trend_arrow,
            timestamp=current.datetime.isoformat() if current.datetime else None,
            delta=delta,
            previous_value=previous_value,
        )

    def _log_successful_reading(self, glucose_data: GlucoseData) -> None:
        """Log a successful glucose reading."""
        if glucose_data.delta is not None:
            logger.info(
                "Fetched glucose reading",
                extra={
                    "value": glucose_data.value,
                    "trend_arrow": glucose_data.trend_arrow,
                    "delta": glucose_data.delta,
                    "trend_direction": glucose_data.trend_direction,
                }
            )
        else:
            logger.info(
                "Fetched glucose reading (no delta)",
                extra={
                    "value": glucose_data.value,
                    "trend_arrow": glucose_data.trend_arrow,
                    "trend_direction": glucose_data.trend_direction,
                }
            )

    def _handle_api_error(self, error: Exception) -> Tuple[Optional[GlucoseData], int]:
        """
        Handle API errors with graceful fallback to cached data.

        Args:
            error: The exception that occurred

        Returns:
            Tuple of (cached_data, progress) if cache available

        Raises:
            DexcomAPIError: If no cached data available
        """
        with self._lock:
            self._last_error = str(error)
            self._last_error_time = datetime.now()
            self._api_errors += 1

        logger.error(
            "Error fetching from Dexcom API",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "region": self.settings.dexcom_region,
            },
            exc_info=True,
        )

        # Return cached data if available
        with self._lock:
            if self._cached_data is not None:
                logger.warning(
                    "Returning cached value due to API error",
                    extra={
                        "cached_value": self._cached_data.value,
                        "error": str(error),
                    }
                )
                return self._cached_data, self._get_refresh_progress_unlocked()

        # No cache available - raise error
        raise DexcomAPIError(
            message="Failed to fetch glucose data",
            details="No cached data available to return",
            original_error=error,
        )


# =============================================================================
# Dependency Injection
# =============================================================================

_client: Optional[DexcomClient] = None


def get_dexcom_client() -> DexcomClient:
    """
    Get the singleton DexcomClient instance.

    Returns:
        Configured DexcomClient instance
    """
    global _client
    if _client is None:
        from .config import get_settings
        _client = DexcomClient(get_settings())
    return _client


def reset_dexcom_client() -> None:
    """Reset the singleton client (useful for testing)."""
    global _client
    _client = None
