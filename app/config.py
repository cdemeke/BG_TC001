from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


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

    # Glucose thresholds
    glucose_critical_low: int = 55
    glucose_low: int = 70
    glucose_high: int = 180
    glucose_very_high: int = 240

    # Delta threshold for double arrows
    delta_fast_threshold: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
