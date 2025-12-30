"""
AWTRIX3 display formatter for glucose data.

This module converts glucose readings into AWTRIX3-compatible display
commands with pixel-level control for trend arrows and progress indicators.
"""

from typing import List, Optional, Tuple

from .config import Settings
from .constants import (
    ARROW_WIDTH,
    CHAR_SPACING,
    CHAR_WIDTH_DEFAULT,
    CHAR_WIDTH_MEDIUM,
    CHAR_WIDTH_NARROW,
    CHAR_WIDTH_SPACE,
    CRITICAL_BLINK_INTERVAL_MS,
    CRITICAL_HIGH_BACKGROUND,
    CRITICAL_LOW_BACKGROUND,
    DIAGONAL_DOWN_PATTERN,
    DIAGONAL_UP_PATTERN,
    DOWN_ARROW_PATTERN,
    INDICATOR_DOT_STEP_SIZE,
    MEDIUM_CHARS,
    NARROW_CHARS,
    SPACE_CHARS,
    STABLE_ARROW_PATTERN,
    UP_ARROW_PATTERN,
    ArrowPixel,
    ArrowType,
)
from .models import AwtrixResponse, GlucoseData


# =============================================================================
# Color Functions
# =============================================================================

def get_color_for_glucose(value: int, settings: Settings) -> List[int]:
    """
    Get RGB color based on glucose value using configurable thresholds.

    Color coding (configurable via environment):
    - Critical Low: <55 mg/dL (red)
    - Low: 55-69 mg/dL (red)
    - Normal: 70-180 mg/dL (green)
    - High: 181-240 mg/dL (yellow)
    - Very High: >240 mg/dL (orange)

    Args:
        value: Glucose value in mg/dL
        settings: Application settings with color configuration

    Returns:
        RGB color as [R, G, B] list
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
    """
    Get optional background color for critical glucose values.

    Args:
        value: Glucose value in mg/dL
        settings: Application settings

    Returns:
        RGB color as [R, G, B] list for critical values, None otherwise
    """
    if value < settings.glucose_critical_low:
        return CRITICAL_LOW_BACKGROUND.copy()
    elif value > settings.glucose_very_high:
        return CRITICAL_HIGH_BACKGROUND.copy()
    return None


def rgb_to_hex(rgb: List[int]) -> str:
    """
    Convert RGB color array to hex color string for AWTRIX draw commands.

    Args:
        rgb: Color as [R, G, B] list

    Returns:
        Hex color string (e.g., "#ff0000")
    """
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


# =============================================================================
# Arrow Drawing Functions
# =============================================================================

def get_arrow_type(delta: Optional[int], settings: Settings) -> ArrowType:
    """
    Determine arrow type based on glucose delta.

    Args:
        delta: Change from previous reading (can be None)
        settings: Application settings with threshold configuration

    Returns:
        ArrowType indicating which arrow style to use
    """
    if delta is None:
        return ArrowType.STABLE

    abs_delta = abs(delta)

    if abs_delta <= settings.delta_stable_threshold:
        return ArrowType.STABLE
    elif abs_delta > settings.delta_rapid_threshold:
        return ArrowType.RAPID
    else:
        return ArrowType.DIAGONAL


def get_arrow_pattern(
    arrow_type: ArrowType,
    delta: Optional[int],
) -> List[ArrowPixel]:
    """
    Get the pixel pattern for an arrow type and direction.

    Args:
        arrow_type: Type of arrow (stable, diagonal, or rapid)
        delta: Change value to determine direction (positive = up)

    Returns:
        List of ArrowPixel objects defining the arrow shape
    """
    if arrow_type == ArrowType.STABLE:
        return STABLE_ARROW_PATTERN

    is_rising = (delta or 0) > 0

    if arrow_type == ArrowType.RAPID:
        return UP_ARROW_PATTERN if is_rising else DOWN_ARROW_PATTERN
    else:  # DIAGONAL
        return DIAGONAL_UP_PATTERN if is_rising else DIAGONAL_DOWN_PATTERN


def render_arrow_pattern(
    pattern: List[ArrowPixel],
    base_x: int,
    hex_color: str,
) -> List[dict]:
    """
    Render an arrow pattern at a specific position with a given color.

    Args:
        pattern: List of ArrowPixel objects defining the shape
        base_x: X coordinate for the arrow's left edge
        hex_color: Hex color string for the arrow

    Returns:
        List of AWTRIX draw commands
    """
    draw_commands = []

    for pixel in pattern:
        if pixel.command == 'dp':
            # Draw pixel: [x, y, color]
            x = base_x + pixel.offsets[0]
            y = pixel.offsets[1]
            draw_commands.append({"dp": [x, y, hex_color]})
        elif pixel.command == 'dl':
            # Draw line: [x1, y1, x2, y2, color]
            x1 = base_x + pixel.offsets[0]
            y1 = pixel.offsets[1]
            x2 = base_x + pixel.offsets[2]
            y2 = pixel.offsets[3]
            draw_commands.append({"dl": [x1, y1, x2, y2, hex_color]})

    return draw_commands


def get_arrow_drawing(
    delta: Optional[int],
    settings: Settings,
    hex_color: str,
    x: int,
) -> Tuple[List[dict], int]:
    """
    Generate complete arrow drawing at specified position.

    Args:
        delta: Glucose change from previous reading
        settings: Application settings
        hex_color: Hex color string for the arrow
        x: X coordinate for the arrow's left edge

    Returns:
        Tuple of (draw_commands, arrow_width)
    """
    arrow_type = get_arrow_type(delta, settings)
    pattern = get_arrow_pattern(arrow_type, delta)
    draw_commands = render_arrow_pattern(pattern, x, hex_color)

    return draw_commands, ARROW_WIDTH


# =============================================================================
# Indicator Dot Functions
# =============================================================================

def calculate_growth_step(refresh_progress: int) -> int:
    """
    Calculate the growth step for the indicator dot based on refresh progress.

    Args:
        refresh_progress: Progress percentage (0-100)

    Returns:
        Growth step (0-10)
    """
    return refresh_progress // INDICATOR_DOT_STEP_SIZE


def get_indicator_dot_color(step: int, settings: Settings) -> str:
    """
    Get the indicator dot color, alternating between bright and dim for blink effect.

    Args:
        step: Current growth step
        settings: Application settings

    Returns:
        Hex color string
    """
    is_bright = (step % 2) == 0
    color_str = settings.indicator_dot_color if is_bright else settings.indicator_dot_color_dim
    return rgb_to_hex(settings.parse_color(color_str))


def get_indicator_dot_drawing(
    refresh_progress: int,
    settings: Settings,
) -> List[dict]:
    """
    Generate draw commands for a growing/blinking indicator dot.

    The dot grows in size approximately every 30 seconds during the 5-minute
    API polling interval, providing visual feedback that the system is
    preparing to fetch new data.

    Growth pattern:
    - Step 0 (0-9%): 1 pixel
    - Step 1-2 (10-29%): 2-3 pixels
    - Step 3-4 (30-49%): 4 pixels
    - Step 5-6 (50-69%): 5-6 pixels
    - Step 7-8 (70-89%): 7-9 pixels
    - Step 9-10 (90-100%): Full shape (12 pixels)

    Args:
        refresh_progress: Progress percentage (0-100) towards next API refresh
        settings: Application settings with dot configuration

    Returns:
        List of draw commands for the indicator dot
    """
    if not settings.indicator_dot_enabled:
        return []

    growth_step = calculate_growth_step(refresh_progress)
    color_hex = get_indicator_dot_color(growth_step, settings)

    base_x = settings.indicator_dot_x
    base_y = settings.indicator_dot_y

    # Define growth progression as list of (x_offset, y_offset) from base
    growth_offsets = [
        [(0, 0)],                                                          # Step 0: 1 pixel
        [(0, 0), (0, 1)],                                                  # Step 1: 2 pixels
        [(0, 0), (0, 1), (-1, 0)],                                         # Step 2: 3 pixels
        [(0, 0), (0, 1), (-1, 0), (-1, 1)],                                # Step 3: 4 pixels
        [(0, 0), (0, 1), (-1, 0), (-1, 1), (0, 2)],                        # Step 4: 5 pixels
        [(0, 0), (0, 1), (-1, 0), (-1, 1), (0, 2), (-1, 2)],               # Step 5: 6 pixels
        [(0, 0), (0, 1), (-1, 0), (-1, 1), (0, 2), (-1, 2), (-2, 0)],      # Step 6: 7 pixels
        [(0, 0), (0, 1), (-1, 0), (-1, 1), (0, 2), (-1, 2), (-2, 0), (-2, 1)],  # Step 7: 8 pixels
        [(0, 0), (0, 1), (-1, 0), (-1, 1), (0, 2), (-1, 2), (-2, 0), (-2, 1), (-2, 2)],  # Step 8: 9 pixels
        [(0, 0), (0, 1), (-1, 0), (-1, 1), (0, 2), (-1, 2), (-2, 0), (-2, 1), (-2, 2),
         (0, 3), (-1, 3), (-2, 3)],  # Step 9-10: 12 pixels
    ]

    # Clamp step to valid range
    step_index = min(growth_step, len(growth_offsets) - 1)
    offsets = growth_offsets[step_index]

    return [
        {"dp": [base_x + dx, base_y + dy, color_hex]}
        for dx, dy in offsets
    ]


# =============================================================================
# Text Formatting Functions
# =============================================================================

def estimate_text_width(text: str) -> int:
    """
    Estimate pixel width of text in AWTRIX3 default font.

    Uses proportional spacing based on character widths:
    - Narrow chars (1, i, l, :): 2 pixels
    - Space: 2 pixels
    - Medium chars (+, -): 4 pixels
    - Default: 4 pixels

    Args:
        text: Text string to measure

    Returns:
        Estimated width in pixels
    """
    if not text:
        return 0

    width = 0
    for char in text:
        if char in NARROW_CHARS:
            width += CHAR_WIDTH_NARROW
        elif char in SPACE_CHARS:
            width += CHAR_WIDTH_SPACE
        elif char in MEDIUM_CHARS:
            width += CHAR_WIDTH_MEDIUM
        else:
            width += CHAR_WIDTH_DEFAULT
        width += CHAR_SPACING

    # Remove trailing spacing
    return width - CHAR_SPACING if width > 0 else 0


def format_delta(delta: Optional[int]) -> str:
    """
    Format delta value with sign for display.

    Args:
        delta: Change from previous reading

    Returns:
        Formatted string (e.g., "+5", "-3", or "" if None)
    """
    if delta is None:
        return ""
    return f"+{delta}" if delta >= 0 else str(delta)


# =============================================================================
# Main Formatter
# =============================================================================

def format_for_awtrix(
    glucose_data: GlucoseData,
    settings: Settings,
    refresh_progress: int = 0,
) -> AwtrixResponse:
    """
    Format glucose data for AWTRIX3 custom app display.

    Display format: {value}{arrow}{delta} (e.g., "149↘-11")

    The display uses pixel-level drawing for:
    - Glucose value (colored by threshold)
    - Trend arrow (custom pixel art)
    - Delta change (white)
    - Progress bar (bottom of display)
    - Indicator dot (top-right, shows refresh progress)

    Args:
        glucose_data: Current glucose reading
        settings: Application settings
        refresh_progress: Progress towards next API refresh (0-100)
            0 = just refreshed, 100 = ready to refresh again

    Returns:
        AwtrixResponse configured for the display
    """
    value = glucose_data.value
    delta = glucose_data.delta

    # Get colors
    glucose_color = get_color_for_glucose(value, settings)
    delta_color = settings.parse_color(settings.color_delta)
    progress_color = settings.parse_color(settings.color_progress_bar)
    progress_bg_color = settings.parse_color(settings.color_progress_bg)

    # Convert to hex for draw commands
    glucose_hex = rgb_to_hex(glucose_color)
    delta_hex = rgb_to_hex(delta_color)

    # Format text strings
    value_str = str(value)
    delta_str = format_delta(delta)

    # Calculate positions
    value_width = estimate_text_width(value_str)
    arrow_x = value_width + 1  # Gap after value
    arrow_draw, arrow_width = get_arrow_drawing(delta, settings, glucose_hex, arrow_x)
    delta_x = arrow_x + arrow_width + 1  # Gap after arrow

    # Build draw commands
    draw_commands: List[dict] = [
        {"dt": [0, 0, value_str, glucose_hex]},  # Glucose value
    ]
    draw_commands.extend(arrow_draw)

    if delta_str:
        draw_commands.append({"dt": [delta_x, 0, delta_str, delta_hex]})

    # Add indicator dot for refresh progress
    draw_commands.extend(get_indicator_dot_drawing(refresh_progress, settings))

    # Build response
    response = AwtrixResponse(
        text="",  # Using draw array instead
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
        response.blinkText = CRITICAL_BLINK_INTERVAL_MS

    # Add progress bar
    response.progress = refresh_progress
    response.progressC = progress_color
    response.progressBC = progress_bg_color

    return response
