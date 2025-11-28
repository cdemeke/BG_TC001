from typing import List, Optional, Tuple

from .config import Settings
from .models import AwtrixResponse, GlucoseData


def get_color_for_glucose(value: int, settings: Settings) -> List[int]:
    """
    Returns RGB color based on glucose value using configurable colors.

    Color coding (configurable via env):
    - Red: <70 mg/dL (hypoglycemia)
    - Green: 70-180 mg/dL (normal range)
    - Yellow: 181-240 mg/dL (high)
    - Orange: >240 mg/dL (very high)
    """
    if value < settings.glucose_critical_low:
        return settings.parse_color(settings.color_critical_low)
    elif value < settings.glucose_low:
        return settings.parse_color(settings.color_low)
    elif value <= settings.glucose_high:
        return settings.parse_color(settings.color_normal)
    elif value <= settings.glucose_very_high:
        return settings.parse_color(settings.color_high)
    else:
        return settings.parse_color(settings.color_very_high)


def get_background_color(value: int, settings: Settings) -> Optional[List[int]]:
    """Returns optional background color for critical values."""
    if value < settings.glucose_critical_low:
        # Critical low - dim red background
        return [64, 0, 0]
    elif value > settings.glucose_very_high:
        # Critical high - dim orange background
        return [64, 32, 0]
    return None


def rgb_to_hex(rgb: List[int]) -> str:
    """Convert RGB array to hex color string for draw commands."""
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


def get_arrow_drawing(delta: Optional[int], settings: Settings, hex_color: str, x: int) -> Tuple[List[dict], int]:
    """
    Returns draw commands for arrow at specified x position.

    Arrow types based on delta:
    - Stable (→) for delta ±0 to ±stable_threshold
    - Diagonal (↗ ↘) for moderate changes
    - Vertical (↑ ↓) for rapid changes

    Returns: (draw_commands, arrow_width)
    """
    abs_delta = abs(delta) if delta is not None else 0

    # Stable: horizontal arrow (→)
    if delta is None or abs_delta <= settings.delta_stable_threshold:
        return [
            {"dl": [x, 3, x + 3, 3, hex_color]},      # Horizontal stem
            {"dp": [x + 4, 3, hex_color]},            # Tip
            {"dp": [x + 3, 2, hex_color]},            # Head top
            {"dp": [x + 3, 4, hex_color]},            # Head bottom
        ], 5

    # Rapid: vertical arrows (↑ ↓)
    elif abs_delta > settings.delta_rapid_threshold:
        if delta > 0:
            # Up arrow (↑)
            return [
                {"dl": [x + 2, 2, x + 2, 6, hex_color]},  # Stem
                {"dp": [x + 2, 1, hex_color]},            # Tip
                {"dp": [x + 1, 2, hex_color]},            # Head left inner
                {"dp": [x + 3, 2, hex_color]},            # Head right inner
                {"dp": [x, 3, hex_color]},                # Head left outer
                {"dp": [x + 4, 3, hex_color]},            # Head right outer
            ], 5
        else:
            # Down arrow (↓) - user's design
            return [
                {"dl": [x + 2, 0, x + 2, 5, hex_color]},  # Stem
                {"dp": [x + 2, 6, hex_color]},            # Tip
                {"dp": [x + 1, 5, hex_color]},            # Head left inner
                {"dp": [x + 3, 5, hex_color]},            # Head right inner
                {"dp": [x, 4, hex_color]},                # Head left outer
                {"dp": [x + 4, 4, hex_color]},            # Head right outer
            ], 5

    # Moderate: diagonal arrows (↗ ↘)
    else:
        if delta > 0:
            # Diagonal up-right (↗)
            return [
                {"dp": [x, 5, hex_color]},
                {"dp": [x + 1, 4, hex_color]},
                {"dp": [x + 2, 3, hex_color]},
                {"dp": [x + 3, 2, hex_color]},
                {"dp": [x + 4, 1, hex_color]},
                {"dp": [x + 4, 0, hex_color]},            # Tip top
                {"dp": [x + 3, 0, hex_color]},            # Head left
                {"dp": [x + 4, 2, hex_color]},            # Head down
            ], 5
        else:
            # Diagonal down-right (↘) - user's design
            return [
                {"dp": [x, 1, hex_color]},
                {"dp": [x + 1, 2, hex_color]},
                {"dp": [x + 2, 3, hex_color]},
                {"dp": [x + 3, 4, hex_color]},
                {"dp": [x + 4, 5, hex_color]},
                {"dp": [x + 4, 6, hex_color]},            # Tip bottom
                {"dp": [x + 3, 6, hex_color]},            # Head left
                {"dp": [x + 4, 4, hex_color]},            # Head up
            ], 5


def estimate_text_width(text: str) -> int:
    """Estimate pixel width of text in AWTRIX3 default font."""
    width = 0
    for char in text:
        if char in '1il:':
            width += 2
        elif char in ' ':
            width += 2
        elif char in '+-':
            width += 4
        else:
            width += 4
        width += 1
    return width - 1 if width > 0 else 0


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

    Display format: {value}{arrow}{delta} (e.g., "149↘-11")

    The arrow is pixel-drawn inline between the glucose value and delta.

    Args:
        glucose_data: Current glucose reading
        settings: Application settings
        refresh_progress: Progress towards next API refresh (0-100).
                         0 = just refreshed, 100 = ready to refresh again.
                         Displayed as a progress bar at bottom of screen.
    """
    value = glucose_data.value
    delta = glucose_data.delta

    # Get colors (configurable via env)
    glucose_color = get_color_for_glucose(value, settings)
    delta_color = settings.parse_color(settings.color_delta)
    progress_color = settings.parse_color(settings.color_progress_bar)
    progress_bg_color = settings.parse_color(settings.color_progress_bg)

    # Convert to hex for draw commands
    glucose_hex = rgb_to_hex(glucose_color)
    delta_hex = rgb_to_hex(delta_color)

    # Format strings
    value_str = str(value)
    delta_str = format_delta(delta)

    # Calculate positions: "149" + arrow + "-11"
    value_width = estimate_text_width(value_str)
    arrow_x = value_width + 1  # After value + gap

    # Get arrow drawing at calculated position
    arrow_draw, arrow_width = get_arrow_drawing(delta, settings, glucose_hex, arrow_x)

    # Delta position after arrow
    delta_x = arrow_x + arrow_width + 1

    # Build draw commands: value + arrow + delta
    draw_commands = [
        {"dt": [0, 0, value_str, glucose_hex]},  # Glucose value
    ]
    draw_commands.extend(arrow_draw)  # Arrow pixels
    if delta_str:
        draw_commands.append({"dt": [delta_x, 0, delta_str, delta_hex]})  # Delta

    # Build response
    response = AwtrixResponse(
        text="",  # Empty - using draw array
        color=glucose_color,
        icon=None,
        duration=settings.awtrix_duration,
        noScroll=True,
        center=False,
        lifetime=settings.awtrix_lifetime,
        draw=draw_commands,
    )

    # Add background for critical values
    background = get_background_color(value, settings)
    if background:
        response.background = background

    # Add blinking for critical lows
    if value < settings.glucose_critical_low:
        response.blinkText = 500  # Blink every 500ms

    # Add progress bar
    response.progress = refresh_progress
    response.progressC = progress_color
    response.progressBC = progress_bg_color

    return response
