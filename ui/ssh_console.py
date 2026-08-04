#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Interactive SSH terminal for a single device."""

import os
import queue
import socket
import threading
import time
from copy import copy
from datetime import datetime
from types import SimpleNamespace

import paramiko
from PyQt5.QtCore import QEvent, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
)

from config.ssh_security import (
    build_connect_kwargs,
    configure_host_key_policy,
    persist_host_keys,
)
from ui.terminal_widget import TerminalWidget


class InteractiveSSHWorker(QThread):
    opened_signal = pyqtSignal(str)
    data_signal = pyqtSignal(bytes)
    error_signal = pyqtSignal(str)
    closed_signal = pyqtSignal()

    def __init__(self, device, columns=120, lines=32):
        super().__init__()
        self.device = device
        self.columns = max(20, int(columns))
        self.lines = max(5, int(lines))
        self.client = None
        self.channel = None
        self._stop_event = threading.Event()
        self._outgoing = queue.Queue()

    def run(self):
        try:
            self.client = paramiko.SSHClient()
            policy = getattr(self.device, "host_key_policy", "tofu")
            known_hosts_path = configure_host_key_policy(self.client, policy)
            kwargs = build_connect_kwargs(self.device, self.device.ip)
            self.client.connect(**kwargs)
            persist_host_keys(self.client, policy, known_hosts_path)
            self.channel = self.client.invoke_shell(
                term="xterm",
                width=self.columns,
                height=self.lines,
            )
            self.channel.settimeout(0.2)
            self.opened_signal.emit(self._device_label())

            while not self._stop_event.is_set():
                self._flush_outgoing()
                channel = self.channel
                if channel is None:
                    break
                if channel.recv_ready():
                    data = channel.recv(32768)
                    if not data:
                        break
                    self.data_signal.emit(bytes(data))
                    continue
                if channel.closed:
                    break
                time.sleep(0.02)
        except paramiko.BadHostKeyException:
            self._emit_error("SSH Host Key 与已保存记录不一致，连接已拒绝")
        except paramiko.AuthenticationException:
            self._emit_error("SSH 用户名、密码或私钥认证失败")
        except (paramiko.SSHException, OSError, ValueError, socket.error) as exc:
            self._emit_error(str(exc))
        finally:
            self._close_connections()
            self.closed_signal.emit()

    def write_bytes(self, payload):
        if payload and not self._stop_event.is_set():
            self._outgoing.put(("data", bytes(payload)))

    def resize_terminal(self, columns, lines):
        self.columns = max(20, int(columns))
        self.lines = max(5, int(lines))
        if not self._stop_event.is_set():
            self._outgoing.put(("resize", (self.columns, self.lines)))

    def stop(self):
        self._stop_event.set()
        self._close_connections()

    def _flush_outgoing(self):
        while True:
            try:
                action, payload = self._outgoing.get_nowait()
            except queue.Empty:
                return
            channel = self.channel
            if channel is None or channel.closed:
                continue
            if action == "data":
                channel.sendall(payload)
            elif action == "resize":
                columns, lines = payload
                channel.resize_pty(width=columns, height=lines)

    def _emit_error(self, message):
        if not self._stop_event.is_set():
            self.error_signal.emit(message or "未知 SSH 错误")

    def _close_connections(self):
        channel, self.channel = self.channel, None
        client, self.client = self.client, None
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

    def _device_label(self):
        name = getattr(self.device, "name", "") or getattr(self.device, "ip", "")
        return f"{name} ({self.device.ip})"


class SSHConsoleDialog(QDialog):
    def __init__(self, devices=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setWindowTitle("SSH 交互终端")
        self.resize(1180, 780)
        self.setMinimumSize(900, 620)
        self.worker = None
        self._devices = []
        self._build_ui()
        self.set_devices(devices or [])
        self._set_connected(False)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and hasattr(
            self, "terminal"
        ):
            if self.isMinimized():
                self.terminal.suspend_for_window_minimize()
            else:
                self.terminal.restore_after_window_minimize()
        super().changeEvent(event)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        connection_row = QHBoxLayout()
        connection_row.addWidget(QLabel("设备"))
        self.device_combo = QComboBox()
        self.device_combo.setEditable(True)
        self.device_combo.setInsertPolicy(QComboBox.NoInsert)
        self.device_combo.lineEdit().setPlaceholderText("选择设备或输入 IP/主机名")
        self.device_combo.setMinimumWidth(320)
        self.device_combo.currentIndexChanged.connect(self._load_selected_device)
        self.device_combo.editTextChanged.connect(self._update_connect_button)
        connection_row.addWidget(self.device_combo, 1)
        self.device_menu_button = QToolButton()
        self.device_menu_button.setText("▼")
        self.device_menu_button.setToolTip("展开已添加或导入的设备列表")
        self.device_menu_button.setAccessibleName("展开设备列表")
        self.device_menu_button.setFixedWidth(34)
        self.device_menu_button.clicked.connect(self.device_combo.showPopup)
        connection_row.addWidget(self.device_menu_button)
        connection_row.addWidget(QLabel("编码"))
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "GBK", "GB18030", "BIG5"])
        connection_row.addWidget(self.encoding_combo)

        self.connect_button = QPushButton("连接")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_row.addWidget(self.connect_button)
        self.status_label = QLabel("未连接")
        connection_row.addWidget(self.status_label)
        connection_row.addStretch(1)

        clear_button = QPushButton("清屏")
        clear_button.clicked.connect(self.clear_terminal)
        save_button = QPushButton("保存会话")
        save_button.clicked.connect(self.save_session_log)
        connection_row.addWidget(clear_button)
        connection_row.addWidget(save_button)
        layout.addLayout(connection_row)

        credential_row = QHBoxLayout()
        credential_row.addWidget(QLabel("端口"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        credential_row.addWidget(self.port_spin)
        credential_row.addWidget(QLabel("用户名"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("SSH 用户名")
        credential_row.addWidget(self.username_input, 1)
        credential_row.addWidget(QLabel("密码"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("密码认证时填写")
        credential_row.addWidget(self.password_input, 1)
        layout.addLayout(credential_row)

        self.terminal = TerminalWidget()
        self.terminal.setToolTip("连接后可直接在此区域输入 SSH 命令")
        self.terminal.data_ready.connect(self.send_raw)
        self.terminal.terminal_resized.connect(self.resize_remote_terminal)
        layout.addWidget(self.terminal, 1)

        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)

    def set_devices(self, devices):
        selected = self.device_combo.currentData()
        selected_key = id(selected) if selected is not None else None
        self._devices = list(devices or [])
        self.device_combo.clear()
        for device in self._devices:
            name = getattr(device, "name", "") or getattr(device, "ip", "")
            self.device_combo.addItem(
                f"{name}  |  {device.ip}:{device.port}",
                device,
            )
        if selected_key is not None:
            for index in range(self.device_combo.count()):
                if id(self.device_combo.itemData(index)) == selected_key:
                    self.device_combo.setCurrentIndex(index)
                    break
        if self.device_combo.count():
            self._load_selected_device(self.device_combo.currentIndex())
        self.device_menu_button.setEnabled(bool(self._devices))
        self._update_connect_button()

    def toggle_connection(self):
        if self.worker is None:
            self.open_ssh()
        else:
            self.close_ssh()

    def open_ssh(self):
        try:
            device = self._connection_device()
        except ValueError as exc:
            QMessageBox.warning(self, "SSH 连接参数", str(exc))
            return
        self.terminal.reset_terminal()
        self.terminal.set_encoding(self._active_encoding())
        self.worker = InteractiveSSHWorker(
            device,
            self.terminal.columns,
            self.terminal.lines,
        )
        self.worker.opened_signal.connect(self.on_opened)
        self.worker.data_signal.connect(self.on_data)
        self.worker.error_signal.connect(self.on_error)
        self.worker.closed_signal.connect(self.on_closed)
        self.device_combo.setEnabled(False)
        self.encoding_combo.setEnabled(False)
        self.port_spin.setEnabled(False)
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)
        self.connect_button.setText("取消")
        self.connect_button.setEnabled(True)
        self.status_label.setText("正在连接...")
        self.worker.start()

    def close_ssh(self):
        if self.worker is None:
            return
        self.status_label.setText("正在断开...")
        self.worker.stop()
        if not self.worker.wait(3000):
            self.status_label.setText("SSH 断开超时")

    def on_opened(self, label):
        self._set_connected(True)
        self.status_label.setText(f"已连接：{label}")
        self._append_event(f"已连接 {label}")
        self.terminal.setFocus()

    def on_data(self, data):
        self.terminal.feed_bytes(data, self._active_encoding())

    def on_error(self, message):
        self.status_label.setText(f"错误：{message}")
        self._append_event(f"SSH 错误：{message}")

    def on_closed(self):
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.deleteLater()
        self._set_connected(False)
        self._append_event("SSH 会话已断开")

    def send_raw(self, payload):
        if self.worker is not None:
            self.worker.write_bytes(payload)

    def resize_remote_terminal(self, columns, lines):
        if self.worker is not None:
            self.worker.resize_terminal(columns, lines)

    def clear_terminal(self):
        self.terminal.clear_terminal()

    def save_session_log(self):
        self.terminal.flush_pending_output()
        default = f"ssh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存 SSH 会话",
            default,
            "日志文件 (*.log *.txt)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as stream:
                stream.write(self.terminal.toPlainText())
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        QMessageBox.information(
            self,
            "保存完成",
            f"SSH 会话已保存到：\n{os.path.abspath(file_path)}",
        )

    def _set_connected(self, connected):
        self.connect_button.setText("断开" if connected else "连接")
        if connected:
            self.connect_button.setEnabled(True)
        else:
            self._update_connect_button()
        self.device_combo.setEnabled(not connected)
        self.encoding_combo.setEnabled(not connected)
        self.port_spin.setEnabled(not connected)
        self.username_input.setEnabled(not connected)
        self.password_input.setEnabled(not connected)
        self.terminal.setReadOnly(not connected)
        if not connected and not self.status_label.text().startswith("错误"):
            self.status_label.setText("未连接")

    def _append_event(self, message):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.feed_text(f"\r\n[{stamp}] {message}\r\n")

    def _active_encoding(self):
        return self.encoding_combo.currentText().lower() or "utf-8"

    def _load_selected_device(self, index):
        device = self.device_combo.itemData(index) if index >= 0 else None
        if device is None:
            self._update_connect_button()
            return
        self.port_spin.setValue(int(getattr(device, "port", 22) or 22))
        self.username_input.setText(str(getattr(device, "username", "") or ""))
        auth_method = str(
            getattr(device, "auth_method", "password") or "password"
        ).lower()
        if auth_method == "key":
            self.password_input.clear()
            self.password_input.setPlaceholderText("使用设备中配置的 SSH 私钥")
        else:
            self.password_input.setPlaceholderText("密码认证时填写")
            self.password_input.setText(
                str(getattr(device, "password", "") or "")
            )
        self._update_connect_button()

    def _connection_device(self):
        host_text = self.device_combo.currentText().strip()
        if not host_text:
            raise ValueError("请输入设备 IP、主机名，或从列表中选择设备")

        index = self.device_combo.currentIndex()
        selected = self.device_combo.itemData(index) if index >= 0 else None
        if (
            selected is not None
            and host_text == self.device_combo.itemText(index)
        ):
            device = copy(selected)
            device.port = self.port_spin.value()
            device.username = self.username_input.text().strip()
            if getattr(device, "auth_method", "password") != "key":
                device.password = self.password_input.text()
            if not device.username:
                raise ValueError("请输入 SSH 用户名")
            return device

        host, parsed_port = self._parse_host_and_port(host_text)
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not host:
            raise ValueError("请输入有效的设备 IP 或主机名")
        if not username:
            raise ValueError("请输入 SSH 用户名")
        if not password:
            raise ValueError("手动连接使用密码认证，请输入 SSH 密码")
        return SimpleNamespace(
            name=host,
            brand="",
            ip=host,
            port=parsed_port or self.port_spin.value(),
            username=username,
            password=password,
            auth_method="password",
            private_key_path="",
            private_key_passphrase="",
            host_key_policy="tofu",
        )

    @staticmethod
    def _parse_host_and_port(value):
        text = str(value or "").strip()
        if text.startswith("[") and "]" in text:
            closing = text.index("]")
            host = text[1:closing].strip()
            suffix = text[closing + 1:].strip()
            if suffix.startswith(":") and suffix[1:].isdigit():
                return host, int(suffix[1:])
            return host, None
        if text.count(":") == 1:
            host, port = text.rsplit(":", 1)
            if host.strip() and port.isdigit():
                return host.strip(), int(port)
        return text, None

    def _update_connect_button(self, *_args):
        self.connect_button.setEnabled(
            self.worker is not None
            or bool(self.device_combo.currentText().strip())
        )

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(3000)
        event.accept()
