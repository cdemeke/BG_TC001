"""Tests for app/constants.py module."""

import pytest

from app.constants import (
    ARROW_WIDTH,
    CHAR_WIDTH_DEFAULT,
    CHAR_WIDTH_NARROW,
    CRITICAL_BLINK_INTERVAL_MS,
    CRITICAL_HIGH_BACKGROUND,
    CRITICAL_LOW_BACKGROUND,
    DEFAULT_LOG_FORMAT,
    DIAGONAL_DOWN_PATTERN,
    DIAGONAL_UP_PATTERN,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    DOWN_ARROW_PATTERN,
    DeltaThreshold,
    GlucoseThreshold,
    INDICATOR_DOT_GROWTH_STEPS,
    MIN_API_INTERVAL_SECONDS,
    STABLE_ARROW_PATTERN,
    UP_ARROW_PATTERN,
    ArrowPixel,
    ArrowType,
)


class TestArrowType:
    """Tests for ArrowType enum."""

    def test_arrow_type_values(self):
        """Test that arrow types have correct values."""
        assert ArrowType.STABLE == 0
        assert ArrowType.DIAGONAL == 1
        assert ArrowType.RAPID == 2


class TestArrowPatterns:
    """Tests for arrow pixel patterns."""

    def test_stable_arrow_pattern_not_empty(self):
        """Test stable arrow pattern has pixels."""
        assert len(STABLE_ARROW_PATTERN) > 0

    def test_up_arrow_pattern_not_empty(self):
        """Test up arrow pattern has pixels."""
        assert len(UP_ARROW_PATTERN) > 0

    def test_down_arrow_pattern_not_empty(self):
        """Test down arrow pattern has pixels."""
        assert len(DOWN_ARROW_PATTERN) > 0

    def test_diagonal_up_pattern_not_empty(self):
        """Test diagonal up pattern has pixels."""
        assert len(DIAGONAL_UP_PATTERN) > 0

    def test_diagonal_down_pattern_not_empty(self):
        """Test diagonal down pattern has pixels."""
        assert len(DIAGONAL_DOWN_PATTERN) > 0

    def test_arrow_pixel_structure(self):
        """Test ArrowPixel dataclass structure."""
        pixel = ArrowPixel('dp', (1, 2))
        assert pixel.command == 'dp'
        assert pixel.offsets == (1, 2)

    def test_all_patterns_have_valid_commands(self):
        """Test all patterns use valid draw commands."""
        all_patterns = [
            STABLE_ARROW_PATTERN,
            UP_ARROW_PATTERN,
            DOWN_ARROW_PATTERN,
            DIAGONAL_UP_PATTERN,
            DIAGONAL_DOWN_PATTERN,
        ]
        valid_commands = {'dp', 'dl'}

        for pattern in all_patterns:
            for pixel in pattern:
                assert pixel.command in valid_commands


class TestDisplayConstants:
    """Tests for display-related constants."""

    def test_display_dimensions(self):
        """Test AWTRIX display dimensions."""
        assert DISPLAY_WIDTH == 32
        assert DISPLAY_HEIGHT == 8

    def test_arrow_width(self):
        """Test arrow width constant."""
        assert ARROW_WIDTH == 5

    def test_char_widths_positive(self):
        """Test character widths are positive."""
        assert CHAR_WIDTH_NARROW > 0
        assert CHAR_WIDTH_DEFAULT > 0


class TestThresholds:
    """Tests for threshold constants."""

    def test_glucose_thresholds_ordered(self):
        """Test glucose thresholds are in ascending order."""
        assert GlucoseThreshold.CRITICAL_LOW < GlucoseThreshold.LOW
        assert GlucoseThreshold.LOW < GlucoseThreshold.HIGH
        assert GlucoseThreshold.HIGH < GlucoseThreshold.VERY_HIGH

    def test_delta_thresholds_ordered(self):
        """Test delta thresholds are in ascending order."""
        assert 0 < DeltaThreshold.STABLE < DeltaThreshold.RAPID


class TestApiConstants:
    """Tests for API-related constants."""

    def test_min_api_interval(self):
        """Test API interval is 5 minutes."""
        assert MIN_API_INTERVAL_SECONDS == 300

    def test_indicator_dot_growth_steps(self):
        """Test indicator dot has 10 growth steps."""
        assert INDICATOR_DOT_GROWTH_STEPS == 10


class TestCriticalAlertConstants:
    """Tests for critical alert constants."""

    def test_critical_backgrounds_are_rgb(self):
        """Test critical backgrounds are valid RGB arrays."""
        assert len(CRITICAL_LOW_BACKGROUND) == 3
        assert len(CRITICAL_HIGH_BACKGROUND) == 3

        for color in [CRITICAL_LOW_BACKGROUND, CRITICAL_HIGH_BACKGROUND]:
            for component in color:
                assert 0 <= component <= 255

    def test_blink_interval_positive(self):
        """Test blink interval is positive."""
        assert CRITICAL_BLINK_INTERVAL_MS > 0


class TestLoggingConstants:
    """Tests for logging constants."""

    def test_log_format_has_required_fields(self):
        """Test log format includes essential fields."""
        assert "%(asctime)s" in DEFAULT_LOG_FORMAT
        assert "%(levelname)s" in DEFAULT_LOG_FORMAT
        assert "%(message)s" in DEFAULT_LOG_FORMAT
