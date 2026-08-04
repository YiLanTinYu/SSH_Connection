from ui.responsive_layout import (
    calculate_font_size,
    expanded_sidebar_width,
    maximum_sidebar_width,
    operations_tool_columns,
)


def test_responsive_layout_calculations_preserve_main_window_rules():
    anchors = ((1280, 15), (1920, 17), (2560, 17))
    assert calculate_font_size(1000, anchors) == 15
    assert calculate_font_size(1600, anchors) == 16
    assert calculate_font_size(3000, anchors) == 17
    assert maximum_sidebar_width(1920, 420) == 960
    assert expanded_sidebar_width(1920, 960, 420) == 576


def test_operations_tools_use_two_columns_only_when_space_allows():
    assert operations_tool_columns(True, 660) == 2
    assert operations_tool_columns(True, 659) == 1
    assert operations_tool_columns(False, 900) == 1
