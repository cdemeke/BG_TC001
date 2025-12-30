"""
Application configuration with Pydantic validation.

All settings are loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List, Optional, Tuple

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

from .constants import (
    DEFAULT_LOG_LEVEL,
    DeltaThreshold,
    GlucoseThreshold,
)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All color values should be comma-separated RGB strings (e.g., "255,0,0").
    Thresholds are validated to ensure logical ordering.
    """

    # =========================================================================
    # Dexcom Credentials
    # =========================================================================
    dexcom_username: Optional[str] = None
    dexcom_password: str
    dexcom_account_id: Optional[str] = None
    dexcom_region: str = "us"  # us, ous, or jp

    # =========================================================================
    # Cache Settings
    # =========================================================================
    cache_ttl_seconds: int = 90

    # =========================================================================
    # AWTRIX Display Settings
    # =========================================================================
    awtrix_icon: Optional[str] = None
    awtrix_duration: int = 10
    awtrix_lifetime: int = 120

    # =========================================================================
    # Server Settings
    # =========================================================================
    port: int = 8080
    debug: bool = False
    log_level: str = DEFAULT_LOG_LEVEL

    # =========================================================================
    # Glucose Thresholds (mg/dL)
    # =========================================================================
    glucose_critical_low: int = GlucoseThreshold.CRITICAL_LOW
    glucose_low: int = GlucoseThreshold.LOW
    glucose_high: int = GlucoseThreshold.HIGH
    glucose_very_high: int = GlucoseThreshold.VERY_HIGH

    # =========================================================================
    # Delta Thresholds for Arrow Types
    # =========================================================================
    # ±0 to stable_threshold: stable arrow (→)
    # ±stable_threshold to rapid_threshold: diagonal arrow (↗ ↘)
    # Beyond rapid_threshold: vertical arrow (↑ ↓)
    delta_stable_threshold: int = DeltaThreshold.STABLE
    delta_rapid_threshold: int = DeltaThreshold.RAPID

    # =========================================================================
    # Arrow Icons
    # =========================================================================
    icon_stable: str = "arrow_right"
    icon_up: str = "arrow_up"
    icon_down: str = "arrow_down"
    icon_diagonal_up: str = "arrow_up_right"
    icon_diagonal_down: str = "arrow_down_right"

    # =========================================================================
    # Display Colors (RGB comma-separated strings)
    # =========================================================================
    color_critical_low: str = "255,0,0"      # Red
    color_low: str = "255,0,0"               # Red
    color_normal: str = "0,255,0"            # Green
    color_high: str = "255,255,0"            # Yellow
    color_very_high: str = "255,128,0"       # Orange
    color_delta: str = "255,255,255"         # White
    color_progress_bar: str = "0,255,255"    # Cyan
    color_progress_bg: str = "32,32,32"      # Dark gray

    # =========================================================================
    # Indicator Dot Settings
    # =========================================================================
    indicator_dot_enabled: bool = True
    indicator_dot_color: str = "0,255,255"       # Cyan
    indicator_dot_color_dim: str = "0,128,128"   # Dim cyan
    indicator_dot_x: int = 31                    # Right edge
    indicator_dot_y: int = 0                     # Top
    indicator_dot_blink_interval: int = 30       # Seconds

    # =========================================================================
    # MQTT Settings (Optional - for push-based updates without local bridge)
    # =========================================================================
    mqtt_enabled: bool = False
    mqtt_broker_host: Optional[str] = None
    mqtt_broker_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_use_tls: bool = False
    mqtt_client_id: str = "dexcom-awtrix-bridge"
    mqtt_awtrix_prefix: str = "awtrix"           # Topic prefix for AWTRIX
    mqtt_app_name: str = "glucose"               # Custom app name

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator('dexcom_region')
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate Dexcom region is supported."""
        valid_regions = {'us', 'ous', 'jp'}
        v_lower = v.lower()
        if v_lower not in valid_regions:
            raise ValueError(f"Invalid region '{v}'. Must be one of: {', '.join(valid_regions)}")
        return v_lower

    @field_validator(
        'color_critical_low', 'color_low', 'color_normal', 'color_high',
        'color_very_high', 'color_delta', 'color_progress_bar', 'color_progress_bg',
        'indicator_dot_color', 'indicator_dot_color_dim'
    )
    @classmethod
    def validate_color_format(cls, v: str) -> str:
        """Validate color string is in 'R,G,B' format with valid values."""
        try:
            parts = [p.strip() for p in v.split(',')]
            if len(parts) != 3:
                raise ValueError("Color must have exactly 3 components")

            for i, part in enumerate(parts):
                value = int(part)
                if not 0 <= value <= 255:
                    raise ValueError(f"Color component {i+1} must be 0-255, got {value}")

            return v
        except ValueError as e:
            raise ValueError(f"Invalid color format '{v}': {e}. Expected 'R,G,B' with values 0-255")

    @field_validator('indicator_dot_x')
    @classmethod
    def validate_dot_x(cls, v: int) -> int:
        """Validate indicator dot X position is within display width."""
        if not 0 <= v <= 31:
            raise ValueError(f"indicator_dot_x must be 0-31, got {v}")
        return v

    @field_validator('indicator_dot_y')
    @classmethod
    def validate_dot_y(cls, v: int) -> int:
        """Validate indicator dot Y position is within display height."""
        if not 0 <= v <= 7:
            raise ValueError(f"indicator_dot_y must be 0-7, got {v}")
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level '{v}'. Must be one of: {', '.join(valid_levels)}")
        return v_upper

    @model_validator(mode='after')
    def validate_thresholds(self) -> 'Settings':
        """Validate that threshold values are in logical order."""
        # Glucose thresholds
        if not (self.glucose_critical_low < self.glucose_low):
            raise ValueError(
                f"glucose_critical_low ({self.glucose_critical_low}) must be less than "
                f"glucose_low ({self.glucose_low})"
            )
        if not (self.glucose_low < self.glucose_high):
            raise ValueError(
                f"glucose_low ({self.glucose_low}) must be less than "
                f"glucose_high ({self.glucose_high})"
            )
        if not (self.glucose_high < self.glucose_very_high):
            raise ValueError(
                f"glucose_high ({self.glucose_high}) must be less than "
                f"glucose_very_high ({self.glucose_very_high})"
            )

        # Delta thresholds
        if not (0 < self.delta_stable_threshold < self.delta_rapid_threshold):
            raise ValueError(
                f"delta_stable_threshold ({self.delta_stable_threshold}) must be positive and "
                f"less than delta_rapid_threshold ({self.delta_rapid_threshold})"
            )

        return self

    @model_validator(mode='after')
    def validate_authentication(self) -> 'Settings':
        """Validate that authentication credentials are provided."""
        if not self.dexcom_username and not self.dexcom_account_id:
            raise ValueError(
                "Either dexcom_username or dexcom_account_id must be provided"
            )
        return self

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def parse_color(self, color_str: str) -> List[int]:
        """Parse a comma-separated RGB color string to a list of ints."""
        return [int(c.strip()) for c in color_str.split(",")]

    def get_color_tuple(self, color_str: str) -> Tuple[int, int, int]:
        """Parse a color string and return as a tuple."""
        parts = self.parse_color(color_str)
        return (parts[0], parts[1], parts[2])

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
