import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QSignalSpy, QTest
from PyQt5.QtWidgets import QApplication, QPushButton

from ui.serial_console import SerialConsoleDialog, SerialWorker
from utils.serial_tools import (
    SerialConfig,
    SerialProfileStore,
    friendly_serial_error,
    open_serial_connection,
)


def test_loopback_serial_connection_round_trip():
    config = SerialConfig(port="loop://", baudrate=9600, timeout=0.5)
    connection = open_serial_connection(config)
    try:
        payload = b"display version\r"
        connection.write(payload)
        assert connection.read(len(payload)) == payload
    finally:
        connection.close()


def test_serial_permission_error_has_actionable_chinese_message():
    message = friendly_serial_error(
        "could not open port 'COM3': PermissionError(13, '拒绝访问。')",
        "COM3",
    )
    assert "无法打开 COM3" in message
    assert "其他程序占用" in message
    assert "SecureCRT" in message


def test_serial_profile_store_round_trip(tmp_path):
    store = SerialProfileStore(str(tmp_path / "profiles.json"))
    config = SerialConfig(
        port="COM9", baudrate=115200, parity="E",
        flow_control="rtscts", encoding="gbk", line_ending="cr",
    )
    store.save_profile("H3C Console", config)
    loaded = store.load()
    assert loaded["H3C Console"]["port"] == "COM9"
    assert loaded["H3C Console"]["baudrate"] == 115200
    assert loaded["H3C Console"]["parity"] == "E"

    store.delete_profile("H3C Console")
    assert store.load() == {}


def test_legacy_serial_profile_migrates_crlf_default_to_cr(tmp_path):
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        '{"legacy": {"port": "COM3", "line_ending": "crlf"}}',
        encoding="utf-8",
    )

    loaded = SerialProfileStore(str(profile_path)).load()

    assert loaded["legacy"]["line_ending"] == "cr"
    assert loaded["legacy"]["profile_version"] == 2


def test_serial_worker_reads_without_blocking_ui_thread():
    app = QApplication.instance() or QApplication([])
    worker = SerialWorker(SerialConfig(port="loop://", timeout=0.05))
    opened = QSignalSpy(worker.opened_signal)
    received = QSignalSpy(worker.data_signal)
    worker.start()
    try:
        assert opened.wait(2000)
        worker.write_bytes(b"hello-console")
        assert received.wait(2000)
        deadline = time.monotonic() + 2
        received_data = b""
        while time.monotonic() < deadline:
            app.processEvents()
            received_data = b"".join(bytes(item[0]) for item in received)
            if b"hello-console" in received_data:
                break
            QTest.qWait(10)
        assert b"hello-console" in received_data
    finally:
        worker.stop()
        assert worker.wait(3000)


def test_serial_console_dialog_starts_without_physical_port(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()
    try:
        assert dialog.windowTitle() == "串口控制台"
        assert dialog.windowFlags() & Qt.WindowMaximizeButtonHint
        assert dialog.port_combo.currentData() in (None, "")
        assert dialog.open_button.isEnabled() is False
        assert dialog.command_input.isEnabled() is False
        button_labels = {
            button.text() for button in dialog.findChildren(QPushButton)
        }
        assert not {
            "Enter", "Ctrl+C", "Ctrl+Z", "Esc", "Tab", "Break",
        } & button_labels
        app.processEvents()
    finally:
        dialog.close()


def test_serial_console_connected_status_is_updated(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()
    try:
        dialog.on_opened("COM3")
        assert dialog.status_label.text() == (
            "串口已打开：COM3（设备状态未知）"
        )
        assert dialog.open_button.text() == "关闭串口"
        app.processEvents()
    finally:
        dialog.close()


def test_serial_error_status_survives_closed_signal(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()
    try:
        class FakeWorker:
            @staticmethod
            def deleteLater():
                pass

        dialog.worker = FakeWorker()
        dialog.on_error(
            "could not open port 'COM3': PermissionError(13, '拒绝访问。')"
        )
        dialog.on_closed()

        assert dialog.status_label.text() == "串口异常关闭，请查看终端日志"
        assert "无法打开" in dialog.status_label.toolTip()
        app.processEvents()
    finally:
        dialog.close()


def test_serial_monitor_stops_worker_when_adapter_disappears(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()

    class FakeConnection:
        is_open = True

    class FakeWorker:
        connection = FakeConnection()

        def __init__(self):
            self.stop_calls = 0

        def stop(self):
            self.stop_calls += 1

    try:
        dialog.worker = FakeWorker()
        dialog._monitored_port = "COM3"
        dialog._monitor_serial_status()

        assert dialog.worker.stop_calls == 1
        assert dialog.status_label.text() == "串口适配器已拔出：COM3"
        assert dialog.serial_status_timer.interval() == 1000
        assert dialog._last_serial_error_kind == "adapter_missing"
        app.processEvents()
    finally:
        dialog.serial_status_timer.stop()
        dialog.worker = None
        dialog.close()


def test_serial_monitor_detects_adapter_recovery(monkeypatch):
    app = QApplication.instance() or QApplication([])
    ports = []
    monkeypatch.setattr(
        "ui.serial_console.discover_serial_ports", lambda: list(ports)
    )
    dialog = SerialConsoleDialog()
    try:
        dialog._monitored_port = "COM3"
        dialog._last_serial_error = "串口适配器已拔出：COM3"
        dialog._last_serial_error_kind = "adapter_missing"
        dialog.serial_status_timer.setInterval(1000)
        dialog.serial_status_timer.start()
        ports.append({"device": "COM3", "description": "USB Serial Port"})

        dialog._monitor_serial_status()

        assert dialog.serial_status_timer.isActive() is False
        assert dialog.status_label.text() == (
            "串口适配器已恢复：COM3，请重新打开"
        )
        assert dialog.port_combo.findData("COM3") >= 0
        assert dialog.open_button.isEnabled() is True
        app.processEvents()
    finally:
        dialog.serial_status_timer.stop()
        dialog.close()


def test_serial_monitor_reports_line_signals_without_claiming_online(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        "ui.serial_console.discover_serial_ports",
        lambda: [{"device": "COM3", "description": ""}],
    )
    dialog = SerialConsoleDialog()

    class FakeConnection:
        is_open = True
        cts = True
        dsr = False
        cd = False
        ri = False

    class FakeWorker:
        connection = FakeConnection()

        @staticmethod
        def stop():
            pass

    try:
        dialog.worker = FakeWorker()
        dialog._monitored_port = "COM3"
        dialog._monitor_serial_status()

        assert dialog.serial_status_timer.interval() == 2000
        assert dialog.status_label.text() == (
            "串口已打开：COM3（设备状态未知）"
        )
        assert "CTS" in dialog.status_label.toolTip()
        assert "仅供参考" in dialog.status_label.toolTip()
        app.processEvents()
    finally:
        dialog.serial_status_timer.stop()
        dialog.worker = None
        dialog.close()


def test_enter_sends_command_without_triggering_save_profile(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()

    class FakeWorker:
        def __init__(self):
            self.sent = []

        def write_bytes(self, payload):
            self.sent.append(payload)

        @staticmethod
        def stop():
            pass

        @staticmethod
        def wait(_timeout):
            return True

    try:
        dialog.port_combo.clear()
        dialog.port_combo.addItem("COM3", "COM3")
        dialog.worker = FakeWorker()
        dialog.command_input.setEnabled(True)
        dialog._set_input_mode("command")
        save_button = next(
            button for button in dialog.findChildren(QPushButton)
            if button.text() == "保存配置"
        )
        save_clicks = QSignalSpy(save_button.clicked)
        assert all(
            not button.autoDefault()
            for button in dialog.findChildren(QPushButton)
        )

        dialog.command_input.setText("display version")
        dialog.command_input.setFocus()
        QTest.keyClick(dialog.command_input, Qt.Key_Return)
        app.processEvents()

        assert dialog.worker.sent == [b"display version\r"]
        assert len(save_clicks) == 0
    finally:
        dialog.worker = None
        dialog.close()


def test_terminal_area_accepts_direct_keyboard_input(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()

    class FakeWorker:
        config = SerialConfig(
            port="COM3", encoding="utf-8", line_ending="crlf"
        )

        def __init__(self):
            self.sent = []

        def write_bytes(self, payload):
            self.sent.append(payload)

    try:
        dialog.worker = FakeWorker()
        dialog._set_input_mode("terminal")
        dialog.terminal.setFocus()
        QTest.keyClicks(dialog.terminal, "display version")
        QTest.keyClick(dialog.terminal, Qt.Key_Return)
        QTest.keyClick(dialog.terminal, Qt.Key_Up)
        QTest.keyClick(dialog.terminal, Qt.Key_C, Qt.ControlModifier)
        app.processEvents()

        assert b"".join(dialog.worker.sent) == (
            b"display version\r\x1b[A\x03"
        )
    finally:
        dialog.worker = None
        dialog.close()


def test_only_focused_serial_input_area_is_writable(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()

    class FakeWorker:
        config = SerialConfig(port="COM3")

        @staticmethod
        def write_bytes(_payload):
            pass

    try:
        dialog.worker = FakeWorker()
        dialog.command_input.setEnabled(True)

        dialog._set_input_mode("terminal")
        assert dialog.terminal.isReadOnly() is False
        assert dialog.command_input.isReadOnly() is True
        assert dialog.send_button.isEnabled() is False

        dialog._set_input_mode("command")
        assert dialog.terminal.isReadOnly() is True
        assert dialog.command_input.isReadOnly() is False
        assert dialog.send_button.isEnabled() is True
        app.processEvents()
    finally:
        dialog.worker = None
        dialog.close()


def test_mouse_focus_switches_between_terminal_and_command_input(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()

    class FakeWorker:
        config = SerialConfig(port="COM3")

        @staticmethod
        def write_bytes(_payload):
            pass

    try:
        dialog.worker = FakeWorker()
        dialog._set_connected(True)
        dialog.show()
        app.processEvents()

        QTest.mouseClick(dialog.terminal.viewport(), Qt.LeftButton)
        app.processEvents()
        assert dialog.terminal.hasFocus()
        assert dialog.terminal.isReadOnly() is False
        assert dialog.command_input.isReadOnly() is True

        QTest.mouseClick(dialog.command_input, Qt.LeftButton)
        app.processEvents()
        assert dialog.command_input.hasFocus()
        assert dialog.command_input.isReadOnly() is False
        assert dialog.terminal.isReadOnly() is True
    finally:
        dialog.worker = None
        dialog.close()


def test_serial_crlf_is_rendered_as_one_line_break(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()
    try:
        dialog.on_data(b"line1\r\nline2\r")
        dialog.on_data(b"\nline3\r\n")
        dialog.terminal.flush_pending_output()
        assert dialog.terminal.toPlainText() == "line1\nline2\nline3"
    finally:
        dialog.close()


def test_terminal_uses_explicit_output_pixel_size(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("ui.serial_console.discover_serial_ports", lambda: [])
    dialog = SerialConsoleDialog()
    try:
        dialog.show()
        app.processEvents()
        assert dialog.terminal.font().pixelSize() == 18
        assert "font-size: 18px" in dialog.terminal.styleSheet()
    finally:
        dialog.close()
