import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QHeaderView

import ui.main_window as main_window


def _font_size(style, selector):
    match = re.search(
        re.escape(selector) + r"\s*\{[^}]*font-size:\s*(\d+)px",
        style,
    )
    assert match, selector
    return int(match.group(1))


def test_main_window_uses_a_clear_typography_hierarchy(monkeypatch):
    app = QApplication.instance() or QApplication([])
    previous_font = QFont(app.font())
    monkeypatch.setattr(main_window, "ConnectionLogger", lambda: object())

    window = main_window.MainWindow()
    try:
        window.resize(1962, 1248)
        window._apply_font_pt(window._calc_font_pt(window.width()))
        style = window.styleSheet()

        body = _font_size(style, "QMainWindow, QWidget")
        group_title = _font_size(style, "QGroupBox::title")
        table_body = _font_size(style, "QTableWidget")
        table_header = _font_size(style, "QHeaderView::section")
        field_label = _font_size(style, "QLabel#field_label")

        assert body == table_body == field_label
        assert group_title == table_header == body + 1
        assert "font-size: 29px" in window._title_lbl.styleSheet()
        assert "font-size: 22px" in window._left_panel._title.styleSheet()
        assert window._ops_tool_buttons[:4] == [
            window.serial_console_btn,
            window.ssh_console_btn,
            window.file_transfer_btn,
            window.packet_capture_btn,
        ]
        header = window.device_table.horizontalHeader()
        assert header.sectionResizeMode(0) == QHeaderView.Interactive
        assert header.sectionSize(0) >= 100

        badge = main_window.StatusBadge(
            "待连接",
            font_px=window._status_badge_font_px,
        )
        assert badge.minimumSizeHint().height() <= (
            window.device_table.verticalHeader().defaultSectionSize()
        )
    finally:
        window.close()
        app.setFont(previous_font)
