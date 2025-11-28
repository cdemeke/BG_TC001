from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Dexcom credentials
    dexcom_username: Optional[str] = None
    dexcom_password: str
    dexcom_account_id: Optional[str] = None
    dexcom_region: str = "us"  # us, ous, or jp

    # Cache settings
    cache_ttl_seconds: int = 90

    # AWTRIX display settings
    awtrix_icon: Optional[str] = None
    awtrix_duration: int = 10
    awtrix_lifetime: int = 120

    # Server settings
    port: int = 8080
    debug: bool = False
    log_level: str = "INFO"

    # Glucose thresholds (mg/dL)
    glucose_critical_low: int = 55
    glucose_low: int = 70
    glucose_high: int = 180
    glucose_very_high: int = 240

    # Delta thresholds for arrow types
    # ±0 to stable_threshold: stable arrow (→)
    # ±stable_threshold to rapid_threshold: diagonal arrow (↗ ↘)
    # Beyond rapid_threshold: vertical arrow (↑ ↓)
    delta_stable_threshold: int = 5
    delta_rapid_threshold: int = 15

    # Arrow icons (filename without extension, or LaMetric icon ID)
    # Download these to your AWTRIX3 via the web interface Icons tab
    icon_stable: str = "arrow_right"        # → stable
    icon_up: str = "arrow_up"               # ↑ rapid rise
    icon_down: str = "arrow_down"           # ↓ rapid fall
    icon_diagonal_up: str = "arrow_up_right"    # ↗ moderate rise
    icon_diagonal_down: str = "arrow_down_right"  # ↘ moderate fall

    # Display colors (RGB format as comma-separated string, e.g., "255,0,0")
    # Glucose value colors based on range
    color_critical_low: str = "255,0,0"      # Red - critical low (<55)
    color_low: str = "255,0,0"               # Red - low (<70)
    color_normal: str = "0,255,0"            # Green - normal (70-180)
    color_high: str = "255,255,0"            # Yellow - high (181-240)
    color_very_high: str = "255,128,0"       # Orange - very high (>240)

    # Delta text color (separate from glucose value color)
    color_delta: str = "255,255,255"         # White - delta change text

    # Progress bar colors
    color_progress_bar: str = "0,255,255"    # Cyan - progress bar fill
    color_progress_bg: str = "32,32,32"      # Dark gray - progress bar background

    def parse_color(self, color_str: str) -> List[int]:
        """Parse a comma-separated RGB color string to a list of ints."""
        return [int(c.strip()) for c in color_str.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
