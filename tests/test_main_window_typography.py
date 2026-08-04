import os
import re
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QHeaderView, QLineEdit

import ui.main_window as main_window
from ui.dialog_helpers import create_secret_input_dialog
from ui.ssh_console import SSHConsoleDialog


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
        assert window._local_tool_buttons == [
            window.serial_console_btn,
            window.file_transfer_btn,
            window.packet_capture_btn,
            window.subnet_calc_btn,
            window.config_diff_btn,
        ]
        assert window._device_tool_buttons[:4] == [
            window.ssh_console_btn,
            window.ping_excel_btn,
            window.port_check_btn,
            window.ssh_test_btn,
        ]
        assert all(
            not button.icon().isNull()
            for button in (
                window.add_btn,
                window.import_btn,
                window.connect_btn,
                window.delete_btn,
                window.clear_btn,
                *window._device_tool_buttons,
                *window._local_tool_buttons,
            )
        )
        assert all(
            button.objectName() == "tool_button"
            for button in window._device_tool_buttons + window._local_tool_buttons
        )
        assert all(
            button.objectName() == "toolbar_button"
            for button in (
                window.log_btn,
                window.clear_log_btn,
                window.result_center_btn,
            )
        )
        assert 42 <= window.statusBar().minimumHeight() <= 48
        first_password_dialog = create_secret_input_dialog(
            window,
            "设置主密码",
            "请输入主密码（至少 8 个字符）：",
        )
        second_password_dialog = create_secret_input_dialog(
            window,
            "确认主密码",
            "请再次输入主密码：",
        )
        assert first_password_dialog.size() == second_password_dialog.size()
        assert first_password_dialog.size().width() == 520
        assert first_password_dialog.size().height() == 210
        assert first_password_dialog.textEchoMode() == QLineEdit.Password
        assert second_password_dialog.textEchoMode() == QLineEdit.Password
        first_password_dialog.close()
        second_password_dialog.close()
        assert window._left_panel.button("devices").toolTip() == "设备库"
        assert window._left_panel.button("tasks").toolTip() == "设备作业"
        assert window._left_panel.button("tools").toolTip() == "本机工具"
        assert window._left_panel.button("templates").toolTip() == "模板中心"
        assert [
            window.brand_combo.itemText(index)
            for index in range(window.brand_combo.count())
        ] == ["H3C", "Huawei"]
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


def test_ssh_terminal_font_overrides_main_window_global_style(monkeypatch):
    app = QApplication.instance() or QApplication([])
    previous_font = QFont(app.font())
    monkeypatch.setattr(main_window, "ConnectionLogger", lambda: object())
    window = main_window.MainWindow()
    dialog = SSHConsoleDialog([], window)
    try:
        window.show()
        dialog.show()
        app.processEvents()

        assert dialog.terminal.font().pixelSize() == 18
        assert "font-size: 18px" in dialog.terminal.styleSheet()
    finally:
        dialog.close()
        window.close()
        app.setFont(previous_font)


def test_shared_task_targets_filter_ping_only_addresses(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(main_window, "ConnectionLogger", lambda: object())
    window = main_window.MainWindow()
    try:
        ssh_target = SimpleNamespace(
            name="SW10",
            ip="192.0.2.10",
            username="operator",
            _aomt_temporary=True,
        )
        ping_target = SimpleNamespace(
            name="192.0.2.11",
            ip="192.0.2.11",
            username="",
            _aomt_temporary=True,
            _aomt_ping_only=True,
        )
        window.device_manager.devices.append(ssh_target)
        window._custom_task_targets = [ssh_target, ping_target]
        window.task_scope_combo.addItem("自定义目标", "custom")
        window._set_combo_data(window.task_scope_combo, "custom")

        assert window._get_task_devices("ping") == [ssh_target, ping_target]
        assert window._get_task_devices("health_check") == [ssh_target]

        window._show_sidebar_page("tasks")
        assert window._left_panel.current_page_key() == "tasks"
        assert window._left_panel.is_expanded()
        window._show_sidebar_page("tasks")
        assert window._left_panel.is_expanded()
    finally:
        window.close()
