#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtTest import QSignalSpy, QTest
from PyQt5.QtWidgets import QApplication

from ui.ssh_console import InteractiveSSHWorker, SSHConsoleDialog
from ui.terminal_widget import TerminalWidget


def test_terminal_widget_applies_cursor_positioning():
    app = QApplication.instance() or QApplication([])
    terminal = TerminalWidget(columns=20, lines=5)
    try:
        terminal.feed_text("abc\rXY")
        terminal.flush_pending_output()
        assert terminal.toPlainText() == "XYc"
    finally:
        terminal.close()


def test_terminal_widget_renders_ansi_foreground_color():
    app = QApplication.instance() or QApplication([])
    terminal = TerminalWidget(columns=20, lines=5)
    try:
        terminal.feed_text("\x1b[31mR\x1b[0m")
        terminal.flush_pending_output()
        cursor = QTextCursor(terminal.document())
        cursor.setPosition(0)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
        assert cursor.charFormat().foreground().color().name() == "#f06a6a"
        app.processEvents()
    finally:
        terminal.close()


def test_terminal_widget_batches_output_until_flush():
    app = QApplication.instance() or QApplication([])
    terminal = TerminalWidget(columns=20, lines=5)
    try:
        terminal.feed_text("display ")
        terminal.feed_text("version")
        assert terminal.toPlainText() == ""

        terminal.flush_pending_output()
        assert terminal.toPlainText().rstrip() == "display version"

        terminal.clear_terminal()
        terminal.feed_text("automatic refresh")
        QTest.qWait(100)
        assert terminal.toPlainText().rstrip() == "automatic refresh"
        app.processEvents()
    finally:
        terminal.close()


def test_terminal_widget_restores_device_cursor_after_document_click():
    app = QApplication.instance() or QApplication([])
    terminal = TerminalWidget(columns=20, lines=5)
    try:
        terminal.feed_text("line1\r\n<H3C>")
        terminal.flush_pending_output()
        expected_position = terminal.textCursor().position()

        clicked_cursor = terminal.textCursor()
        clicked_cursor.setPosition(0)
        terminal.setTextCursor(clicked_cursor)
        terminal.show()
        QTest.mouseClick(
            terminal.viewport(),
            Qt.LeftButton,
            pos=QPoint(2, 2),
        )

        assert terminal.textCursor().position() == expected_position
        assert terminal.textCursor().blockNumber() == 1
        assert terminal.textCursor().positionInBlock() == 5
        app.processEvents()
    finally:
        terminal.close()


def test_terminal_widget_preserves_text_when_resized_smaller_and_larger():
    app = QApplication.instance() or QApplication([])
    terminal = TerminalWidget(columns=80, lines=20, history=200)
    try:
        payload = "\r\n".join(
            f"line {index:03d} text" for index in range(80)
        ) + "\r\n<H3C>"
        terminal.feed_text(payload)
        terminal.flush_pending_output()

        terminal._resize_screen_preserving_content(34, 100)
        terminal._render_screen()
        terminal._resize_screen_preserving_content(12, 40)
        terminal._render_screen()
        terminal._resize_screen_preserving_content(34, 100)
        terminal._render_screen()

        rendered = terminal.toPlainText()
        assert "line 000 text" in rendered
        assert "line 079 text" in rendered
        assert "<H3C>" in rendered
        assert 0 <= terminal._screen.cursor.y < terminal._screen.lines
        app.processEvents()
    finally:
        terminal.close()


def test_terminal_widget_emits_terminal_key_sequences():
    app = QApplication.instance() or QApplication([])
    terminal = TerminalWidget(columns=20, lines=5)
    sent = QSignalSpy(terminal.data_ready)
    try:
        terminal.setReadOnly(False)
        terminal.show()
        terminal.setFocus()
        QTest.keyClicks(terminal, "display version")
        QTest.keyClick(terminal, Qt.Key_Return)
        QTest.keyClick(terminal, Qt.Key_Up)
        QTest.keyClick(terminal, Qt.Key_C, Qt.ControlModifier)
        app.processEvents()
        assert b"".join(bytes(item[0]) for item in sent) == (
            b"display version\r\x1b[A\x03"
        )
    finally:
        terminal.close()


def test_terminal_widget_copy_paste_and_selection_survive_refresh():
    app = QApplication.instance() or QApplication([])
    terminal = TerminalWidget(columns=40, lines=8)
    sent = QSignalSpy(terminal.data_ready)
    try:
        terminal.setReadOnly(False)
        terminal.feed_text("display version")
        terminal.flush_pending_output()
        terminal.show()
        terminal.setFocus()

        selection = terminal.textCursor()
        selection.setPosition(0)
        selection.setPosition(7, QTextCursor.KeepAnchor)
        terminal.setTextCursor(selection)
        QTest.keyClick(terminal, Qt.Key_C, Qt.ControlModifier)
        assert QApplication.clipboard().text() == "display"
        assert len(sent) == 0

        terminal.feed_text("\r\n<H3C>")
        terminal.flush_pending_output()
        assert terminal.selected_text() == "display"

        cursor = terminal.textCursor()
        cursor.clearSelection()
        terminal.setTextCursor(cursor)
        QApplication.clipboard().setText("system-view")
        QTest.keyClick(terminal, Qt.Key_V, Qt.ControlModifier)
        QTest.keyClick(terminal, Qt.Key_C, Qt.ControlModifier)

        assert b"".join(bytes(item[0]) for item in sent) == (
            b"system-view\x03"
        )
        app.processEvents()
    finally:
        terminal.close()


def test_interactive_ssh_worker_opens_pty_and_receives_data(monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = {}

    class FakeChannel:
        def __init__(self):
            self.closed = False
            self._has_data = True

        @staticmethod
        def settimeout(_timeout):
            pass

        def recv_ready(self):
            return self._has_data

        def recv(self, _size):
            self._has_data = False
            self.closed = True
            return b"<H3C>"

        @staticmethod
        def close():
            pass

    class FakeClient:
        def __init__(self):
            self.channel = FakeChannel()

        def connect(self, **kwargs):
            calls["connect"] = kwargs

        def invoke_shell(self, **kwargs):
            calls["shell"] = kwargs
            return self.channel

        @staticmethod
        def close():
            pass

    monkeypatch.setattr("ui.ssh_console.paramiko.SSHClient", FakeClient)
    monkeypatch.setattr(
        "ui.ssh_console.configure_host_key_policy",
        lambda _client, _policy: "known_hosts",
    )
    monkeypatch.setattr(
        "ui.ssh_console.persist_host_keys",
        lambda _client, _policy, _path: None,
    )
    monkeypatch.setattr(
        "ui.ssh_console.build_connect_kwargs",
        lambda device, hostname: {
            "hostname": hostname,
            "port": device.port,
            "username": device.username,
        },
    )

    device = SimpleNamespace(
        brand="H3C",
        ip="192.0.2.10",
        port=22,
        username="admin",
        password="secret",
        name="SW1",
    )
    worker = InteractiveSSHWorker(device, columns=132, lines=40)
    opened = QSignalSpy(worker.opened_signal)
    received = QSignalSpy(worker.data_signal)
    worker.start()
    try:
        assert worker.wait(2000)
        app.processEvents()
        assert opened[0][0] == "SW1 (192.0.2.10)"
        assert bytes(received[0][0]) == b"<H3C>"
        assert calls["shell"] == {
            "term": "xterm",
            "width": 132,
            "height": 40,
        }
    finally:
        worker.stop()
        worker.wait(1000)


def test_interactive_ssh_worker_sends_data_and_resizes_pty():
    device = SimpleNamespace(name="SW1", ip="192.0.2.10")
    worker = InteractiveSSHWorker(device)

    class FakeChannel:
        closed = False

        def __init__(self):
            self.sent = []
            self.sizes = []

        def sendall(self, payload):
            self.sent.append(payload)

        def resize_pty(self, **kwargs):
            self.sizes.append(kwargs)

    channel = FakeChannel()
    worker.channel = channel
    worker.write_bytes(b"display version\r")
    worker.resize_terminal(160, 48)
    worker._flush_outgoing()

    assert channel.sent == [b"display version\r"]
    assert channel.sizes == [{"width": 160, "height": 48}]


def test_ssh_console_disables_connect_without_devices():
    app = QApplication.instance() or QApplication([])
    dialog = SSHConsoleDialog([])
    try:
        assert dialog.windowTitle() == "SSH 交互终端"
        assert dialog.windowFlags() & Qt.WindowMaximizeButtonHint
        assert dialog.device_combo.isEditable() is True
        assert dialog.device_combo.count() == 0
        assert dialog.device_menu_button.isEnabled() is False
        assert dialog.connect_button.isEnabled() is False
        assert dialog.terminal.isReadOnly() is True

        dialog.device_combo.setEditText("[2026:1000:120::23]:2222")
        dialog.username_input.setText("admin")
        dialog.password_input.setText("secret")
        device = dialog._connection_device()
        assert dialog.connect_button.isEnabled() is True
        assert device.ip == "2026:1000:120::23"
        assert device.port == 2222
        assert device.username == "admin"
        app.processEvents()
    finally:
        dialog.close()


def test_ssh_console_keeps_imported_device_list_editable():
    app = QApplication.instance() or QApplication([])
    imported = SimpleNamespace(
        name="SW10",
        brand="H3C",
        ip="192.168.10.10",
        port=22,
        username="admin",
        password="imported-secret",
        auth_method="password",
        host_key_policy="tofu",
    )
    dialog = SSHConsoleDialog([imported])
    try:
        assert dialog.device_combo.isEditable() is True
        assert dialog.device_combo.count() == 1
        assert dialog.device_combo.currentData() is imported
        assert dialog.device_menu_button.isEnabled() is True
        assert dialog.username_input.text() == "admin"

        dialog.device_combo.setEditText("192.168.10.99")
        dialog.username_input.setText("manual-admin")
        dialog.password_input.setText("manual-secret")
        device = dialog._connection_device()
        assert device.ip == "192.168.10.99"
        assert device.username == "manual-admin"
        assert device.password == "manual-secret"
        app.processEvents()
    finally:
        dialog.close()
