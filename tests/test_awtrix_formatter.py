"""Tests for app/awtrix_formatter.py module."""

import pytest

from app.awtrix_formatter import (
    calculate_growth_step,
    estimate_text_width,
    format_delta,
    format_for_awtrix,
    get_arrow_drawing,
    get_arrow_pattern,
    get_arrow_type,
    get_background_color,
    get_color_for_glucose,
    get_indicator_dot_color,
    get_indicator_dot_drawing,
    render_arrow_pattern,
    rgb_to_hex,
)
from app.constants import ARROW_WIDTH, ArrowType
from app.models import GlucoseData


class TestRgbToHex:
    """Tests for rgb_to_hex function."""

    def test_black(self):
        """Test black color conversion."""
        assert rgb_to_hex([0, 0, 0]) == "#000000"

    def test_white(self):
        """Test white color conversion."""
        assert rgb_to_hex([255, 255, 255]) == "#ffffff"

    def test_red(self):
        """Test red color conversion."""
        assert rgb_to_hex([255, 0, 0]) == "#ff0000"

    def test_green(self):
        """Test green color conversion."""
        assert rgb_to_hex([0, 255, 0]) == "#00ff00"

    def test_blue(self):
        """Test blue color conversion."""
        assert rgb_to_hex([0, 0, 255]) == "#0000ff"

    def test_mixed_color(self):
        """Test mixed color conversion."""
        assert rgb_to_hex([128, 64, 32]) == "#804020"


class TestGetColorForGlucose:
    """Tests for get_color_for_glucose function."""

    def test_critical_low(self, mock_settings):
        """Test critical low color."""
        color = get_color_for_glucose(50, mock_settings)
        assert color == [255, 0, 0]  # Red

    def test_low(self, mock_settings):
        """Test low color."""
        color = get_color_for_glucose(65, mock_settings)
        assert color == [255, 0, 0]  # Red

    def test_normal(self, mock_settings):
        """Test normal color."""
        color = get_color_for_glucose(120, mock_settings)
        assert color == [0, 255, 0]  # Green

    def test_high(self, mock_settings):
        """Test high color."""
        color = get_color_for_glucose(200, mock_settings)
        assert color == [255, 255, 0]  # Yellow

    def test_very_high(self, mock_settings):
        """Test very high color."""
        color = get_color_for_glucose(280, mock_settings)
        assert color == [255, 128, 0]  # Orange


class TestGetBackgroundColor:
    """Tests for get_background_color function."""

    def test_critical_low_has_background(self, mock_settings):
        """Test critical low has red background."""
        bg = get_background_color(50, mock_settings)
        assert bg is not None
        assert bg[0] > 0  # Red component

    def test_very_high_has_background(self, mock_settings):
        """Test very high has orange background."""
        bg = get_background_color(280, mock_settings)
        assert bg is not None

    def test_normal_no_background(self, mock_settings):
        """Test normal range has no background."""
        bg = get_background_color(120, mock_settings)
        assert bg is None


class TestGetArrowType:
    """Tests for get_arrow_type function."""

    def test_none_delta_is_stable(self, mock_settings):
        """Test None delta returns stable arrow."""
        assert get_arrow_type(None, mock_settings) == ArrowType.STABLE

    def test_zero_delta_is_stable(self, mock_settings):
        """Test zero delta returns stable arrow."""
        assert get_arrow_type(0, mock_settings) == ArrowType.STABLE

    def test_small_positive_is_stable(self, mock_settings):
        """Test small positive delta returns stable arrow."""
        assert get_arrow_type(3, mock_settings) == ArrowType.STABLE

    def test_small_negative_is_stable(self, mock_settings):
        """Test small negative delta returns stable arrow."""
        assert get_arrow_type(-3, mock_settings) == ArrowType.STABLE

    def test_moderate_positive_is_diagonal(self, mock_settings):
        """Test moderate positive delta returns diagonal arrow."""
        assert get_arrow_type(10, mock_settings) == ArrowType.DIAGONAL

    def test_moderate_negative_is_diagonal(self, mock_settings):
        """Test moderate negative delta returns diagonal arrow."""
        assert get_arrow_type(-10, mock_settings) == ArrowType.DIAGONAL

    def test_large_positive_is_rapid(self, mock_settings):
        """Test large positive delta returns rapid arrow."""
        assert get_arrow_type(20, mock_settings) == ArrowType.RAPID

    def test_large_negative_is_rapid(self, mock_settings):
        """Test large negative delta returns rapid arrow."""
        assert get_arrow_type(-20, mock_settings) == ArrowType.RAPID


class TestGetArrowPattern:
    """Tests for get_arrow_pattern function."""

    def test_stable_pattern(self):
        """Test stable arrow pattern is returned."""
        pattern = get_arrow_pattern(ArrowType.STABLE, 0)
        assert len(pattern) > 0

    def test_rapid_up_pattern(self):
        """Test rapid up arrow pattern is returned."""
        pattern = get_arrow_pattern(ArrowType.RAPID, 20)
        assert len(pattern) > 0

    def test_rapid_down_pattern(self):
        """Test rapid down arrow pattern is returned."""
        pattern = get_arrow_pattern(ArrowType.RAPID, -20)
        assert len(pattern) > 0

    def test_diagonal_up_pattern(self):
        """Test diagonal up arrow pattern is returned."""
        pattern = get_arrow_pattern(ArrowType.DIAGONAL, 10)
        assert len(pattern) > 0

    def test_diagonal_down_pattern(self):
        """Test diagonal down arrow pattern is returned."""
        pattern = get_arrow_pattern(ArrowType.DIAGONAL, -10)
        assert len(pattern) > 0


class TestRenderArrowPattern:
    """Tests for render_arrow_pattern function."""

    def test_render_produces_commands(self):
        """Test rendering produces draw commands."""
        from app.constants import STABLE_ARROW_PATTERN

        commands = render_arrow_pattern(STABLE_ARROW_PATTERN, 10, "#ff0000")
        assert len(commands) > 0

    def test_render_includes_color(self):
        """Test rendered commands include color."""
        from app.constants import STABLE_ARROW_PATTERN

        commands = render_arrow_pattern(STABLE_ARROW_PATTERN, 0, "#00ff00")
        for cmd in commands:
            if 'dp' in cmd:
                assert "#00ff00" in cmd['dp']
            elif 'dl' in cmd:
                assert "#00ff00" in cmd['dl']


class TestGetArrowDrawing:
    """Tests for get_arrow_drawing function."""

    def test_returns_commands_and_width(self, mock_settings):
        """Test function returns draw commands and width."""
        commands, width = get_arrow_drawing(5, mock_settings, "#ffffff", 0)
        assert isinstance(commands, list)
        assert width == ARROW_WIDTH

    def test_commands_are_dicts(self, mock_settings):
        """Test draw commands are dictionaries."""
        commands, _ = get_arrow_drawing(5, mock_settings, "#ffffff", 0)
        for cmd in commands:
            assert isinstance(cmd, dict)


class TestCalculateGrowthStep:
    """Tests for calculate_growth_step function."""

    def test_zero_progress(self):
        """Test zero progress returns step 0."""
        assert calculate_growth_step(0) == 0

    def test_fifty_percent(self):
        """Test 50% progress returns step 5."""
        assert calculate_growth_step(50) == 5

    def test_hundred_percent(self):
        """Test 100% progress returns step 10."""
        assert calculate_growth_step(100) == 10


class TestGetIndicatorDotColor:
    """Tests for get_indicator_dot_color function."""

    def test_even_step_is_bright(self, mock_settings):
        """Test even steps use bright color."""
        color0 = get_indicator_dot_color(0, mock_settings)
        color2 = get_indicator_dot_color(2, mock_settings)
        assert color0 == color2

    def test_odd_step_is_dim(self, mock_settings):
        """Test odd steps use dim color."""
        color1 = get_indicator_dot_color(1, mock_settings)
        color3 = get_indicator_dot_color(3, mock_settings)
        assert color1 == color3

    def test_alternating_colors(self, mock_settings):
        """Test colors alternate between steps."""
        color0 = get_indicator_dot_color(0, mock_settings)
        color1 = get_indicator_dot_color(1, mock_settings)
        assert color0 != color1


class TestGetIndicatorDotDrawing:
    """Tests for get_indicator_dot_drawing function."""

    def test_disabled_returns_empty(self, mock_settings):
        """Test disabled dot returns empty list."""
        mock_settings.indicator_dot_enabled = False
        commands = get_indicator_dot_drawing(50, mock_settings)
        assert commands == []

    def test_enabled_returns_commands(self, mock_settings):
        """Test enabled dot returns draw commands."""
        mock_settings.indicator_dot_enabled = True
        commands = get_indicator_dot_drawing(50, mock_settings)
        assert len(commands) > 0

    def test_grows_with_progress(self, mock_settings):
        """Test dot grows with progress."""
        mock_settings.indicator_dot_enabled = True
        commands_10 = get_indicator_dot_drawing(10, mock_settings)
        commands_90 = get_indicator_dot_drawing(90, mock_settings)
        assert len(commands_90) > len(commands_10)


class TestEstimateTextWidth:
    """Tests for estimate_text_width function."""

    def test_empty_string(self):
        """Test empty string has zero width."""
        assert estimate_text_width("") == 0

    def test_narrow_chars(self):
        """Test narrow characters have less width."""
        narrow = estimate_text_width("111")
        wide = estimate_text_width("888")
        assert narrow < wide

    def test_space_width(self):
        """Test space has width."""
        assert estimate_text_width(" ") > 0

    def test_reasonable_width(self):
        """Test typical glucose value has reasonable width."""
        width = estimate_text_width("120")
        assert 8 < width < 20


class TestFormatDelta:
    """Tests for format_delta function."""

    def test_none_returns_empty(self):
        """Test None returns empty string."""
        assert format_delta(None) == ""

    def test_positive_has_plus(self):
        """Test positive values have plus sign."""
        assert format_delta(5) == "+5"

    def test_negative_has_minus(self):
        """Test negative values have minus sign."""
        assert format_delta(-5) == "-5"

    def test_zero_has_plus(self):
        """Test zero has plus sign."""
        assert format_delta(0) == "+0"


class TestFormatForAwtrix:
    """Tests for format_for_awtrix function."""

    def test_returns_awtrix_response(self, sample_glucose_data, mock_settings):
        """Test returns AwtrixResponse model."""
        from app.models import AwtrixResponse

        response = format_for_awtrix(sample_glucose_data, mock_settings, 50)
        assert isinstance(response, AwtrixResponse)

    def test_has_draw_commands(self, sample_glucose_data, mock_settings):
        """Test response has draw commands."""
        response = format_for_awtrix(sample_glucose_data, mock_settings, 50)
        assert response.draw is not None
        assert len(response.draw) > 0

    def test_has_progress_bar(self, sample_glucose_data, mock_settings):
        """Test response has progress bar."""
        response = format_for_awtrix(sample_glucose_data, mock_settings, 50)
        assert response.progress == 50
        assert response.progressC is not None
        assert response.progressBC is not None

    def test_critical_low_has_blink(self, mock_settings):
        """Test critical low values have blink effect."""
        glucose = GlucoseData(value=50, delta=0)
        response = format_for_awtrix(glucose, mock_settings, 0)
        assert response.blinkText is not None
        assert response.background is not None

    def test_normal_no_blink(self, sample_glucose_data, mock_settings):
        """Test normal values have no blink effect."""
        response = format_for_awtrix(sample_glucose_data, mock_settings, 0)
        assert response.blinkText is None

    def test_no_scroll(self, sample_glucose_data, mock_settings):
        """Test scrolling is disabled."""
        response = format_for_awtrix(sample_glucose_data, mock_settings, 0)
        assert response.noScroll is True
