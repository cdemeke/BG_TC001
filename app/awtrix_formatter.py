from typing import List, Optional

from .config import Settings
from .models import AwtrixResponse, GlucoseData


def get_color_for_glucose(value: int, settings: Settings) -> List[int]:
    """
    Returns RGB color based on glucose value.

    Color coding:
    - Red: <70 mg/dL (hypoglycemia)
    - Green: 70-180 mg/dL (normal range)
    - Yellow: 181-240 mg/dL (high)
    - Orange: >240 mg/dL (very high)
    """
    if value < settings.glucose_low:
        # Red for low blood sugar
        return [255, 0, 0]
    elif value <= settings.glucose_high:
        # Green for normal range
        return [0, 255, 0]
    elif value <= settings.glucose_very_high:
        # Yellow for high
        return [255, 255, 0]
    else:
        # Orange for very high
        return [255, 128, 0]


def get_background_color(value: int, settings: Settings) -> Optional[List[int]]:
    """Returns optional background color for critical values."""
    if value < settings.glucose_critical_low:
        # Critical low - dim red background
        return [64, 0, 0]
    elif value > settings.glucose_very_high:
        # Critical high - dim orange background
        return [64, 32, 0]
    return None


def get_arrow_for_delta(delta: Optional[int], settings: Settings) -> str:
    """
    Returns arrow based on delta magnitude.

    - Single arrow (→↑↓) for delta < 20
    - Double arrow (↑↑↓↓) for delta >= 20
    """
    if delta is None:
        return "→"

    abs_delta = abs(delta)

    if abs_delta >= settings.delta_fast_threshold:
        # Fast change - double arrows
        if delta > 0:
            return "↑↑"
        else:
            return "↓↓"
    elif delta > 0:
        return "↑"
    elif delta < 0:
        return "↓"
    else:
        return "→"


def format_delta(delta: Optional[int]) -> str:
    """Format delta with sign."""
    if delta is None:
        return ""
    if delta >= 0:
        return f"+{delta}"
    else:
        return str(delta)


def format_for_awtrix(
    glucose_data: GlucoseData, settings: Settings, refresh_progress: int = 0
) -> AwtrixResponse:
    """
    Format glucose data for AWTRIX3 custom app.

    Display format: "{value}{arrow} {delta}" (e.g., "120→ +3" or "120↑↑ +30")

    Args:
        glucose_data: Current glucose reading
        settings: Application settings
        refresh_progress: Progress towards next API refresh (0-100).
                         0 = just refreshed, 100 = ready to refresh again.
                         Displayed as a progress bar at bottom of screen.
    """
    value = glucose_data.value
    delta = glucose_data.delta

    # Get arrow based on delta
    arrow = get_arrow_for_delta(delta, settings)

    # Format delta with sign
    delta_str = format_delta(delta)

    # Build display text: "120→ +3"
    if delta_str:
        text = f"{value}{arrow} {delta_str}"
    else:
        text = f"{value}{arrow}"

    # Get color based on glucose value
    color = get_color_for_glucose(value, settings)

    # Build response
    response = AwtrixResponse(
        text=text,
        color=color,
        icon=settings.awtrix_icon,
        duration=settings.awtrix_duration,
        noScroll=True,
        center=True,
        lifetime=settings.awtrix_lifetime,
    )

    # Add background for critical values
    background = get_background_color(value, settings)
    if background:
        response.background = background

    # Add blinking for critical lows
    if value < settings.glucose_critical_low:
        response.blinkText = 500  # Blink every 500ms

    # Add progress bar showing countdown to next API refresh
    # Progress bar fills up as we get closer to the next refresh
    response.progress = refresh_progress
    response.progressC = [0, 255, 255]  # Cyan progress bar
    response.progressBC = [32, 32, 32]  # Dark gray background

    return response
