"""
Dexcom AWTRIX Bridge - A medical glucose data visualization service.

This package provides a bridge between Dexcom G7 continuous glucose monitoring
and AWTRIX3 LED matrix displays for real-time glucose monitoring.
"""

__version__ = "2.0.0"
__author__ = "Dexcom AWTRIX Bridge Contributors"

from .config import Settings, get_settings
from .models import AwtrixResponse, GlucoseData, HealthResponse

__all__ = [
    "Settings",
    "get_settings",
    "AwtrixResponse",
    "GlucoseData",
    "HealthResponse",
]
