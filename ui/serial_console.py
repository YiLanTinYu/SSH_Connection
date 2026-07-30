#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Serial console dialog for switch Console access."""

import codecs
import os
import threading
from datetime import datetime

import serial
from PyQt5.QtCore import QEvent, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ui.terminal_widget import TerminalWidget
from utils.serial_tools import (
    LINE_ENDINGS,
    SerialConfig,
    SerialProfileStore,
    discover_serial_ports,
    friendly_serial_error,
    open_serial_connection,
)


class SerialWorker(QThread):
    opened_signal = pyqtSignal(str)
    data_signal = pyqtSignal(bytes)
    error_signal = pyqtSignal(str)
    closed_signal = pyqtSignal()

    def __init__(self, config: SerialConfig):
        super().__init__()
        self.config = config
        self.connection = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()

    def run(self):
        try:
            self.connection = open_serial_connection(self.config)
            self.opened_signal.emit(self.config.port)
            while not self._stop_event.is_set():
                waiting = int(getattr(self.connection, "in_waiting", 0) or 0)
                data = self.connection.read(waiting or 1)
                if data:
                    self.data_signal.emit(bytes(data))
        except (serial.SerialException, OSError, ValueError) as exc:
            if not self._stop_event.is_set():
                self.error_signal.emit(str(exc))
        finally:
            if self.connection is not None:
                try:
                    self.connection.close()
                except Exception:
                    pass
                self.connection = None
            self.closed_signal.emit()

    def write_bytes(self, data: bytes):
        if not data:
            return
        try:
            with self._write_lock:
                if self.connection is None or not self.connection.is_open:
                    raise serial.SerialException("串口尚未打开")
                self.connection.write(data)
                self.connection.flush()
        except (serial.SerialException, OSError) as exc:
            self.error_signal.emit(str(exc))

    def send_break(self):
        try:
            if self.connection is not None and self.connection.is_open:
                self.connection.send_break(0.25)
        except (serial.SerialException, OSError) as exc:
            self.error_signal.emit(str(exc))

    def stop(self):
        self._stop_event.set()
        connection = self.connection
        if connection is not None:
            try:
                connection.cancel_read()
            except (AttributeError, OSError, serial.SerialException):
                try:
                    connection.close()
                except Exception:
                    pass


class SerialConsoleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setWindowTitle("串口控制台")
        self.resize(1180, 780)
        self.setMinimumSize(900, 620)
        self.worker = None
        self._last_serial_error = ""
        self._last_serial_error_kind = ""
        self._monitored_port = ""
        self._input_mode = None
        self.profile_store = SerialProfileStore()
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.serial_status_timer = QTimer(self)
        self.serial_status_timer.setInterval(2000)
        self.serial_status_timer.timeout.connect(self._monitor_serial_status)
        self._build_ui()
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)
        self._load_profiles()
        self.refresh_ports()
        self._set_connected(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("连接配置"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(220)
        self.profile_combo.currentIndexChanged.connect(self.load_selected_profile)
        save_profile = QPushButton("保存配置")
        delete_profile = QPushButton("删除配置")
        save_profile.clicked.connect(self.save_profile)
        delete_profile.clicked.connect(self.delete_profile)
        profile_row.addWidget(self.profile_combo, 1)
        profile_row.addWidget(save_profile)
        profile_row.addWidget(delete_profile)
        layout.addLayout(profile_row)

        settings = QGridLayout()
        settings.setHorizontalSpacing(8)
        settings.setVerticalSpacing(8)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(210)
        refresh = QPushButton("刷新")
        refresh.clicked.connect(self.refresh_ports)
        self.baud_combo = QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems([
            "1200", "2400", "4800", "9600", "19200", "38400",
            "57600", "115200", "230400", "460800", "921600",
        ])
        self.baud_combo.setCurrentText("9600")
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["8", "7", "6", "5"])
        self.parity_combo = QComboBox()
        for text, value in [
            ("无", "N"), ("偶校验", "E"), ("奇校验", "O"),
            ("Mark", "M"), ("Space", "S"),
        ]:
            self.parity_combo.addItem(text, value)
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "1.5", "2"])
        self.flow_combo = QComboBox()
        for text, value in [
            ("无", "none"), ("RTS/CTS", "rtscts"),
            ("XON/XOFF", "xonxoff"), ("DSR/DTR", "dsrdtr"),
        ]:
            self.flow_combo.addItem(text, value)
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "GBK", "GB18030", "BIG5"])
        self.line_ending_combo = QComboBox()
        for text, value in [
            ("CR", "cr"), ("CRLF", "crlf"), ("LF", "lf"), ("无", "none"),
        ]:
            self.line_ending_combo.addItem(text, value)
        self.dtr_check = QCheckBox("DTR")
        self.dtr_check.setChecked(True)
        self.rts_check = QCheckBox("RTS")
        self.rts_check.setChecked(True)

        settings.addWidget(QLabel("串口"), 0, 0)
        settings.addWidget(self.port_combo, 0, 1)
        settings.addWidget(refresh, 0, 2)
        settings.addWidget(QLabel("波特率"), 0, 3)
        settings.addWidget(self.baud_combo, 0, 4)
        settings.addWidget(QLabel("数据位"), 0, 5)
        settings.addWidget(self.data_bits_combo, 0, 6)
        settings.addWidget(QLabel("校验"), 1, 0)
        settings.addWidget(self.parity_combo, 1, 1)
        settings.addWidget(QLabel("停止位"), 1, 2)
        settings.addWidget(self.stop_bits_combo, 1, 3)
        settings.addWidget(QLabel("流控"), 1, 4)
        settings.addWidget(self.flow_combo, 1, 5)
        signal_row = QHBoxLayout()
        signal_row.addWidget(self.dtr_check)
        signal_row.addWidget(self.rts_check)
        settings.addLayout(signal_row, 1, 6)
        settings.addWidget(QLabel("编码"), 2, 0)
        settings.addWidget(self.encoding_combo, 2, 1)
        settings.addWidget(QLabel("行结束"), 2, 2)
        settings.addWidget(self.line_ending_combo, 2, 3)
        settings.setColumnStretch(1, 1)
        settings.setColumnStretch(4, 1)
        layout.addLayout(settings)

        connection_row = QHBoxLayout()
        self.open_button = QPushButton("打开串口")
        self.open_button.clicked.connect(self.toggle_connection)
        self.status_label = QLabel("串口未打开")
        self.status_label.setToolTip(
            "串口状态只表示电脑是否成功打开 COM 端口，"
            "不能判断交换机是否已通电或在线"
        )
        connection_row.addWidget(self.open_button)
        connection_row.addWidget(self.status_label)
        connection_row.addStretch(1)
        clear = QPushButton("清屏")
        save_log = QPushButton("保存会话")
        clear.clicked.connect(self.clear_terminal)
        save_log.clicked.connect(self.save_session_log)
        connection_row.addWidget(clear)
        connection_row.addWidget(save_log)
        layout.addLayout(connection_row)

        self.terminal = TerminalWidget()
        self.terminal.setReadOnly(True)
        self.terminal.setToolTip("点击此区域后可直接向串口输入")
        self.terminal.data_ready.connect(self.send_raw)
        self.terminal.input_focused.connect(
            lambda: self._set_input_mode("terminal")
        )
        layout.addWidget(self.terminal, 1)

        send_row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("输入 Console 命令，按 Enter 发送")
        self.command_input.installEventFilter(self)
        self.command_input.returnPressed.connect(self.send_command)
        self.hidden_input_check = QCheckBox("隐藏输入")
        self.hidden_input_check.toggled.connect(
            lambda checked: self.command_input.setEchoMode(
                QLineEdit.Password if checked else QLineEdit.Normal
            )
        )
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self.send_command)
        send_row.addWidget(self.command_input, 1)
        send_row.addWidget(self.hidden_input_check)
        send_row.addWidget(self.send_button)
        layout.addLayout(send_row)

    def current_config(self) -> SerialConfig:
        port = self.port_combo.currentData() or self.port_combo.currentText().strip()
        return SerialConfig(
            port=port,
            baudrate=int(self.baud_combo.currentText()),
            bytesize=int(self.data_bits_combo.currentText()),
            parity=self.parity_combo.currentData(),
            stopbits=float(self.stop_bits_combo.currentText()),
            flow_control=self.flow_combo.currentData(),
            encoding=self.encoding_combo.currentText().lower(),
            line_ending=self.line_ending_combo.currentData(),
            dtr=self.dtr_check.isChecked(),
            rts=self.rts_check.isChecked(),
        ).validate()

    def refresh_ports(self):
        current = self.port_combo.currentData() or self.port_combo.currentText()
        self.port_combo.clear()
        ports = discover_serial_ports()
        for item in ports:
            text = item["device"]
            if item["description"]:
                text += f"  ({item['description']})"
            self.port_combo.addItem(text, item["device"])
        if current:
            index = self.port_combo.findData(current)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
        if not ports:
            self.port_combo.addItem("未发现可用串口", "")
        self.open_button.setEnabled(bool(ports) and self.worker is None)

    def toggle_connection(self):
        if self.worker is not None:
            self.close_serial()
        else:
            self.open_serial()

    def open_serial(self):
        try:
            config = self.current_config()
        except (TypeError, ValueError, LookupError) as exc:
            QMessageBox.warning(self, "串口参数", str(exc))
            return
        self.decoder = codecs.getincrementaldecoder(config.encoding)(errors="replace")
        self.terminal.set_encoding(config.encoding)
        self.worker = SerialWorker(config)
        self.worker.opened_signal.connect(self.on_opened)
        self.worker.data_signal.connect(self.on_data)
        self.worker.error_signal.connect(self.on_error)
        self.worker.closed_signal.connect(self.on_closed)
        self._last_serial_error = ""
        self._last_serial_error_kind = ""
        self._monitored_port = config.port
        self._set_controls_enabled(False)
        self.open_button.setEnabled(False)
        self.status_label.setText("正在打开串口...")
        self.worker.start()

    def close_serial(self):
        if self.worker is None:
            return
        self.serial_status_timer.stop()
        self.status_label.setText("正在关闭...")
        self.worker.stop()
        if not self.worker.wait(3000):
            self.status_label.setText("串口关闭超时")

    def on_opened(self, port):
        self._set_connected(True)
        self._last_serial_error = ""
        self._last_serial_error_kind = ""
        self._monitored_port = port
        self.serial_status_timer.setInterval(2000)
        self.serial_status_timer.start()
        self.status_label.setText(
            f"串口已打开：{port}（设备状态未知）"
        )
        self._update_status_tooltip()
        self._append_event(f"已打开 {port}")
        self._set_input_mode("terminal")
        self.terminal.setFocus()

    def on_data(self, data):
        text = self.decoder.decode(data)
        self._append_terminal_text(text)

    def on_error(self, message):
        port = self.port_combo.currentData() or self.port_combo.currentText()
        friendly_message = friendly_serial_error(message, port)
        self._last_serial_error = friendly_message
        if self._last_serial_error_kind != "adapter_missing":
            self._last_serial_error_kind = "io_error"
        self._append_event(f"串口错误：{friendly_message}")
        self.status_label.setText(f"错误：{friendly_message}")
        self.status_label.setToolTip(friendly_message)

    def on_closed(self):
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.deleteLater()
        self._set_connected(False)
        if self._last_serial_error_kind == "adapter_missing":
            self.status_label.setText(
                f"串口适配器已拔出：{self._monitored_port}"
            )
            self.status_label.setToolTip(
                "程序正在每 1 秒检查一次该串口是否恢复。"
                "交换机是否通电无法仅凭串口状态判断。"
            )
            self.serial_status_timer.setInterval(1000)
            self.serial_status_timer.start()
        elif self._last_serial_error:
            self.serial_status_timer.stop()
            self.status_label.setText("串口异常关闭，请查看终端日志")
            self.status_label.setToolTip(self._last_serial_error)
        else:
            self.serial_status_timer.stop()
            self._update_status_tooltip()
        self._append_event("串口已关闭")

    def send_command(self):
        if self.worker is None:
            QMessageBox.warning(self, "串口控制台", "请先打开串口")
            return
        if self._input_mode != "command":
            return
        text = self.command_input.text()
        config = self.current_config()
        payload = text.encode(config.encoding, errors="replace")
        payload += LINE_ENDINGS[config.line_ending]
        self.worker.write_bytes(payload)
        self.command_input.clear()

    def send_raw(self, payload):
        if self.worker is not None:
            self.worker.write_bytes(payload)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.FocusIn and self.worker is not None:
            if watched is self.command_input:
                self._set_input_mode("command")
        return super().eventFilter(watched, event)

    def _set_input_mode(self, mode):
        if mode not in ("terminal", "command") or self.worker is None:
            return
        self._input_mode = mode
        terminal_active = mode == "terminal"
        self.terminal.setReadOnly(not terminal_active)
        self.command_input.setReadOnly(terminal_active)
        self.hidden_input_check.setEnabled(not terminal_active)
        self.send_button.setEnabled(not terminal_active)

    def _active_encoding(self):
        return (
            getattr(getattr(self.worker, "config", None), "encoding", "")
            or self.encoding_combo.currentText().lower()
            or "utf-8"
        )

    def _append_terminal_text(self, text):
        self.terminal.feed_text(text)

    def clear_terminal(self):
        self.terminal.clear_terminal()

    def _append_event(self, message):
        stamp = datetime.now().strftime("%H:%M:%S")
        self._append_terminal_text(f"\n[{stamp}] {message}\n")

    @staticmethod
    def _is_enumerated_port(port):
        return bool(port) and "://" not in port

    def _available_serial_devices(self):
        return {
            str(item.get("device", "")).strip().casefold()
            for item in discover_serial_ports()
            if item.get("device")
        }

    def _monitor_serial_status(self):
        port = self._monitored_port
        if not self._is_enumerated_port(port):
            return

        available = self._available_serial_devices()
        port_present = port.casefold() in available

        if self.worker is None:
            if (
                self._last_serial_error_kind == "adapter_missing"
                and port_present
            ):
                self.serial_status_timer.stop()
                self._last_serial_error = ""
                self._last_serial_error_kind = ""
                self.refresh_ports()
                self.status_label.setText(
                    f"串口适配器已恢复：{port}，请重新打开"
                )
                self._update_status_tooltip()
            return

        connection = getattr(self.worker, "connection", None)
        if not port_present:
            if self._last_serial_error_kind != "adapter_missing":
                self._last_serial_error_kind = "adapter_missing"
                self._last_serial_error = f"串口适配器已拔出：{port}"
                self.status_label.setText(self._last_serial_error)
                self.status_label.setToolTip(
                    "已停止当前串口会话，程序将每 1 秒检查一次端口是否恢复。"
                )
                self._append_event(self._last_serial_error)
            self.serial_status_timer.setInterval(1000)
            self.worker.stop()
            return

        if connection is not None and not bool(
            getattr(connection, "is_open", False)
        ):
            if not self._last_serial_error:
                self._last_serial_error_kind = "io_error"
                self._last_serial_error = f"串口句柄已关闭：{port}"
                self.status_label.setText(self._last_serial_error)
                self.status_label.setToolTip(
                    "串口句柄已意外关闭，请查看终端日志后重新打开。"
                )
                self._append_event(self._last_serial_error)
            self.worker.stop()
            return

        self.serial_status_timer.setInterval(2000)
        self.status_label.setText(
            f"串口已打开：{port}（设备状态未知）"
        )
        self._update_status_tooltip(connection)

    def _update_status_tooltip(self, connection=None):
        lines = [
            "串口状态只表示电脑是否成功打开 COM 端口，"
            "不能单独判断交换机是否已通电或在线。"
        ]
        if connection is not None:
            active_signals = []
            for label, attribute in (
                ("CTS", "cts"),
                ("DSR", "dsr"),
                ("CD", "cd"),
                ("RI", "ri"),
            ):
                try:
                    if bool(getattr(connection, attribute)):
                        active_signals.append(label)
                except (AttributeError, OSError, serial.SerialException):
                    pass
            if active_signals:
                lines.append(
                    "检测到线路信号："
                    + "、".join(active_signals)
                    + "；该信号仅供参考。"
                )
            else:
                lines.append("未检测到可用线路信号，或当前适配器不支持。")
        self.status_label.setToolTip("".join(lines))

    def _set_connected(self, connected):
        self.open_button.setText("关闭串口" if connected else "打开串口")
        if not connected:
            self.status_label.setText("串口未打开")
        self.command_input.setEnabled(connected)
        if not connected:
            self._input_mode = None
            self.terminal.setReadOnly(True)
            self.command_input.setReadOnly(True)
            self.hidden_input_check.setEnabled(False)
            self.send_button.setEnabled(False)
        self._set_controls_enabled(not connected)
        has_port = bool(self.port_combo.currentData())
        self.open_button.setEnabled(connected or has_port)

    def _set_controls_enabled(self, enabled):
        for widget in (
            self.port_combo, self.baud_combo, self.data_bits_combo,
            self.parity_combo, self.stop_bits_combo, self.flow_combo,
            self.encoding_combo, self.line_ending_combo,
            self.dtr_check, self.rts_check,
        ):
            widget.setEnabled(enabled)

    def _load_profiles(self, selected=""):
        profiles = self.profile_store.load()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("选择已保存配置", "")
        for name in sorted(profiles):
            self.profile_combo.addItem(name, name)
        index = self.profile_combo.findData(selected)
        self.profile_combo.setCurrentIndex(max(0, index))
        self.profile_combo.blockSignals(False)

    def save_profile(self):
        try:
            config = self.current_config()
        except (TypeError, ValueError, LookupError) as exc:
            QMessageBox.warning(self, "保存配置", str(exc))
            return
        name, accepted = QInputDialog.getText(self, "保存串口配置", "配置名称：")
        if not accepted or not name.strip():
            return
        self.profile_store.save_profile(name, config)
        self._load_profiles(name.strip())

    def delete_profile(self):
        name = self.profile_combo.currentData()
        if not name:
            return
        answer = QMessageBox.question(
            self, "删除配置", f"确定删除串口配置“{name}”吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.profile_store.delete_profile(name)
            self._load_profiles()

    def load_selected_profile(self):
        name = self.profile_combo.currentData()
        data = self.profile_store.load().get(name)
        if not data:
            return
        config = SerialConfig.from_dict(data)
        index = self.port_combo.findData(config.port)
        if index < 0:
            self.port_combo.addItem(config.port, config.port)
            index = self.port_combo.count() - 1
        self.port_combo.setCurrentIndex(index)
        self.baud_combo.setCurrentText(str(config.baudrate))
        self.data_bits_combo.setCurrentText(str(config.bytesize))
        self._set_combo_data(self.parity_combo, config.parity)
        self.stop_bits_combo.setCurrentText(str(config.stopbits).rstrip("0").rstrip("."))
        self._set_combo_data(self.flow_combo, config.flow_control)
        self.encoding_combo.setCurrentText(config.encoding.upper())
        self._set_combo_data(self.line_ending_combo, config.line_ending)
        self.dtr_check.setChecked(config.dtr)
        self.rts_check.setChecked(config.rts)
        self.open_button.setEnabled(self.worker is None)

    @staticmethod
    def _set_combo_data(combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def save_session_log(self):
        self.terminal.flush_pending_output()
        default = f"serial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存串口会话", default, "日志文件 (*.log *.txt)"
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
            self, "保存完成", f"串口会话已保存到：\n{os.path.abspath(file_path)}"
        )

    def closeEvent(self, event):
        self.serial_status_timer.stop()
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(3000)
        event.accept()
