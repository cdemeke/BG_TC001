"""
Application constants and magic number definitions.

This module centralizes all hardcoded values for better maintainability.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Tuple


# =============================================================================
# API Rate Limiting
# =============================================================================

# Minimum interval between Dexcom API calls (5 minutes)
MIN_API_INTERVAL_SECONDS = 300

# Number of glucose readings to request for delta calculation
GLUCOSE_READINGS_COUNT = 2

# Time window for glucose readings (minutes)
GLUCOSE_READINGS_MINUTES = 30


# =============================================================================
# AWTRIX Display Constants
# =============================================================================

# Display dimensions (AWTRIX3 standard)
DISPLAY_WIDTH = 32
DISPLAY_HEIGHT = 8

# Default character widths for font estimation
CHAR_WIDTH_NARROW = 2  # Characters: 1, i, l, :
CHAR_WIDTH_SPACE = 2
CHAR_WIDTH_MEDIUM = 4  # Characters: +, -
CHAR_WIDTH_DEFAULT = 4
CHAR_SPACING = 1

# Narrow characters for text width calculation
NARROW_CHARS = frozenset('1il:')
SPACE_CHARS = frozenset(' ')
MEDIUM_CHARS = frozenset('+-')


# =============================================================================
# Arrow Drawing Constants
# =============================================================================

class ArrowType(IntEnum):
    """Arrow type enumeration based on glucose delta."""
    STABLE = 0      # Horizontal arrow (→)
    DIAGONAL = 1    # Diagonal arrows (↗ ↘)
    RAPID = 2       # Vertical arrows (↑ ↓)


# Arrow dimensions
ARROW_WIDTH = 5
ARROW_HEIGHT = 7


@dataclass(frozen=True)
class ArrowPixel:
    """Represents a single pixel or line in arrow drawing."""
    command: str  # 'dp' for pixel, 'dl' for line
    offsets: Tuple[int, ...]  # x, y for pixel; x1, y1, x2, y2 for line


# Stable arrow pattern (→) - relative coordinates
STABLE_ARROW_PATTERN: List[ArrowPixel] = [
    ArrowPixel('dl', (0, 3, 3, 3)),  # Horizontal stem
    ArrowPixel('dp', (4, 3)),        # Tip
    ArrowPixel('dp', (3, 2)),        # Head top
    ArrowPixel('dp', (3, 4)),        # Head bottom
]

# Up arrow pattern (↑) - relative coordinates
UP_ARROW_PATTERN: List[ArrowPixel] = [
    ArrowPixel('dl', (2, 2, 2, 6)),  # Stem
    ArrowPixel('dp', (2, 1)),        # Tip
    ArrowPixel('dp', (1, 2)),        # Head left inner
    ArrowPixel('dp', (3, 2)),        # Head right inner
    ArrowPixel('dp', (0, 3)),        # Head left outer
    ArrowPixel('dp', (4, 3)),        # Head right outer
]

# Down arrow pattern (↓) - relative coordinates
DOWN_ARROW_PATTERN: List[ArrowPixel] = [
    ArrowPixel('dl', (2, 0, 2, 5)),  # Stem
    ArrowPixel('dp', (2, 6)),        # Tip
    ArrowPixel('dp', (1, 5)),        # Head left inner
    ArrowPixel('dp', (3, 5)),        # Head right inner
    ArrowPixel('dp', (0, 4)),        # Head left outer
    ArrowPixel('dp', (4, 4)),        # Head right outer
]

# Diagonal up-right arrow pattern (↗) - relative coordinates
DIAGONAL_UP_PATTERN: List[ArrowPixel] = [
    ArrowPixel('dp', (0, 5)),
    ArrowPixel('dp', (1, 4)),
    ArrowPixel('dp', (2, 3)),
    ArrowPixel('dp', (3, 2)),
    ArrowPixel('dp', (4, 1)),
    ArrowPixel('dp', (4, 0)),        # Tip top
    ArrowPixel('dp', (3, 0)),        # Head left
    ArrowPixel('dp', (4, 2)),        # Head down
]

# Diagonal down-right arrow pattern (↘) - relative coordinates
DIAGONAL_DOWN_PATTERN: List[ArrowPixel] = [
    ArrowPixel('dp', (0, 1)),
    ArrowPixel('dp', (1, 2)),
    ArrowPixel('dp', (2, 3)),
    ArrowPixel('dp', (3, 4)),
    ArrowPixel('dp', (4, 5)),
    ArrowPixel('dp', (4, 6)),        # Tip bottom
    ArrowPixel('dp', (3, 6)),        # Head left
    ArrowPixel('dp', (4, 4)),        # Head up
]


# =============================================================================
# Indicator Dot Constants
# =============================================================================

# Number of growth steps over the 5-minute interval
INDICATOR_DOT_GROWTH_STEPS = 10

# Percentage threshold for each growth step (100 / 10 = 10% per step)
INDICATOR_DOT_STEP_SIZE = 10

# Default indicator dot position (top-right corner)
DEFAULT_INDICATOR_DOT_X = 31
DEFAULT_INDICATOR_DOT_Y = 0


# =============================================================================
# Critical Alert Constants
# =============================================================================

# Background colors for critical alerts (RGB)
CRITICAL_LOW_BACKGROUND = [64, 0, 0]     # Dim red
CRITICAL_HIGH_BACKGROUND = [64, 32, 0]   # Dim orange

# Blink interval for critical values (milliseconds)
CRITICAL_BLINK_INTERVAL_MS = 500


# =============================================================================
# Default Glucose Thresholds (mg/dL)
# =============================================================================

class GlucoseThreshold:
    """Default glucose threshold values in mg/dL."""
    CRITICAL_LOW = 55
    LOW = 70
    HIGH = 180
    VERY_HIGH = 240


# =============================================================================
# Default Delta Thresholds
# =============================================================================

class DeltaThreshold:
    """Default delta threshold values for arrow type selection."""
    STABLE = 5   # ±0 to ±5: stable arrow
    RAPID = 15   # Beyond ±15: vertical arrows


# =============================================================================
# Logging Constants
# =============================================================================

DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_LEVEL = "INFO"


# =============================================================================
# Bridge Constants
# =============================================================================

# Default polling interval in seconds
DEFAULT_POLL_INTERVAL = 60

# Default HTTP timeout in seconds
DEFAULT_HTTP_TIMEOUT = 10

# Maximum consecutive failures before logging warning
MAX_CONSECUTIVE_FAILURES = 5

# Default custom app name for AWTRIX
DEFAULT_AWTRIX_APP_NAME = "glucose"

# Error display text
ERROR_DISPLAY_TEXT = "---"
ERROR_DISPLAY_COLOR = [128, 128, 128]  # Gray
