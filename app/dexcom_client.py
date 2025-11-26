import logging
import threading
from datetime import datetime
from typing import Optional, Tuple

from pydexcom import Dexcom

from .config import Settings
from .models import GlucoseData

logger = logging.getLogger(__name__)

# Minimum interval between API calls (5 minutes)
MIN_API_INTERVAL_SECONDS = 300


class DexcomClient:
    """Wrapper around pydexcom with rate limiting and caching support."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._dexcom: Optional[Dexcom] = None
        self._lock = threading.Lock()
        self._last_error: Optional[str] = None
        self._last_error_time: Optional[datetime] = None

        # Rate limiting: store last API call time and cached data
        self._last_api_call: Optional[datetime] = None
        self._cached_data: Optional[GlucoseData] = None

    def _get_dexcom_client(self) -> Dexcom:
        """Lazy initialization of Dexcom client."""
        if self._dexcom is None:
            logger.info(
                f"Initializing Dexcom client for region: {self.settings.dexcom_region}"
            )

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
        return self._dexcom

    def get_seconds_until_next_call(self) -> int:
        """Get seconds remaining until next API call is allowed."""
        with self._lock:
            if self._last_api_call is None:
                return 0

            elapsed = (datetime.now() - self._last_api_call).total_seconds()
            remaining = max(0, MIN_API_INTERVAL_SECONDS - elapsed)
            return int(remaining)

    def get_refresh_progress(self) -> int:
        """
        Get progress towards next refresh as percentage (0-100).
        100 means ready to refresh, 0 means just refreshed.
        """
        with self._lock:
            return self._get_refresh_progress_unlocked()

    def _get_refresh_progress_unlocked(self) -> int:
        """Internal method - must be called while holding _lock."""
        if self._last_api_call is None:
            return 100

        elapsed = (datetime.now() - self._last_api_call).total_seconds()
        progress = min(100, int((elapsed / MIN_API_INTERVAL_SECONDS) * 100))
        return progress

    def _can_call_api_unlocked(self) -> bool:
        """Check if enough time has passed since last API call. Must hold _lock."""
        if self._last_api_call is None:
            return True

        elapsed = (datetime.now() - self._last_api_call).total_seconds()
        return elapsed >= MIN_API_INTERVAL_SECONDS

    def _get_seconds_until_next_call_unlocked(self) -> int:
        """Internal method - must be called while holding _lock."""
        if self._last_api_call is None:
            return 0

        elapsed = (datetime.now() - self._last_api_call).total_seconds()
        remaining = max(0, MIN_API_INTERVAL_SECONDS - elapsed)
        return int(remaining)

    def get_current_reading(self) -> Tuple[Optional[GlucoseData], int]:
        """
        Get current glucose reading with rate limiting.

        Returns:
            Tuple of (GlucoseData, progress_percentage)
            - progress_percentage: 0-100, where 100 = ready for next refresh

        Rate limiting: Will not call API more than once per 5 minutes.
        Returns cached data if called before 5 minutes have passed.
        """
        with self._lock:
            # Check if we need to wait
            if not self._can_call_api_unlocked():
                if self._cached_data is not None:
                    progress = self._get_refresh_progress_unlocked()
                    seconds_remaining = self._get_seconds_until_next_call_unlocked()
                    logger.debug(
                        f"Rate limited: returning cached data. "
                        f"Next refresh in {seconds_remaining}s ({progress}%)"
                    )
                    return self._cached_data, progress
                # No cached data but rate limited - allow the call anyway
                logger.warning("Rate limited but no cached data - allowing API call")

        # Fetch fresh data
        try:
            dexcom = self._get_dexcom_client()

            # Try to get last 2 readings to calculate delta
            readings = dexcom.get_glucose_readings(minutes=30, max_count=2)

            if not readings:
                # Fallback to get_latest_glucose_reading if get_glucose_readings returns empty
                logger.info("get_glucose_readings returned empty, trying get_latest_glucose_reading")
                latest = dexcom.get_latest_glucose_reading()
                if latest:
                    readings = [latest]
                else:
                    logger.warning("No glucose readings returned from Dexcom")
                    with self._lock:
                        # Still update the last call time to prevent hammering
                        self._last_api_call = datetime.now()
                    return None, 0

            current = readings[0]
            previous = readings[1] if len(readings) > 1 else None

            # Calculate delta
            delta = None
            previous_value = None
            if previous is not None:
                delta = current.value - previous.value
                previous_value = previous.value

            glucose_data = GlucoseData(
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

            # Update cache and last call time
            with self._lock:
                self._cached_data = glucose_data
                self._last_api_call = datetime.now()
                self._last_error = None
                self._last_error_time = None

            if delta is not None:
                logger.info(
                    f"Fetched glucose: {glucose_data.value} {glucose_data.trend_arrow} "
                    f"(delta: {delta:+d})"
                )
            else:
                logger.info(
                    f"Fetched glucose: {glucose_data.value} {glucose_data.trend_arrow}"
                )

            return glucose_data, 0  # 0% = just refreshed

        except Exception as e:
            logger.error(f"Error fetching from Dexcom: {e}")
            self._last_error = str(e)
            self._last_error_time = datetime.now()

            # Return cached data if available during error
            with self._lock:
                if self._cached_data is not None:
                    logger.warning("Returning cached value due to error")
                    return self._cached_data, self._get_refresh_progress_unlocked()

            raise


# Dependency injection for FastAPI
_client: Optional[DexcomClient] = None


def get_dexcom_client() -> DexcomClient:
    global _client
    if _client is None:
        from .config import get_settings

        _client = DexcomClient(get_settings())
    return _client
