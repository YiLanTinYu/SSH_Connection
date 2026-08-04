"""Pure responsive-layout calculations shared by the main window."""


def calculate_font_size(width: int, anchors) -> int:
    if width <= anchors[0][0]:
        return anchors[0][1]
    if width >= anchors[-1][0]:
        return anchors[-1][1]
    for index in range(len(anchors) - 1):
        width_start, size_start = anchors[index]
        width_end, size_end = anchors[index + 1]
        if width_start <= width <= width_end:
            ratio = (width - width_start) / (width_end - width_start)
            return round(size_start + ratio * (size_end - size_start))
    return anchors[0][1]


def maximum_sidebar_width(window_width: int, minimum_width: int) -> int:
    return max(minimum_width, window_width // 2)


def expanded_sidebar_width(total_width: int, maximum_width: int, minimum_width: int) -> int:
    return min(max(minimum_width, int(total_width * 0.30)), maximum_width)


def operations_tool_columns(sidebar_expanded: bool, sidebar_width: int) -> int:
    return 2 if sidebar_expanded and sidebar_width >= 660 else 1
