#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Wireshark-backed packet capture window."""

from __future__ import annotations

import os
import re
import threading
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from utils.packet_capture import (
    PacketCaptureConfig,
    PacketCaptureError,
    PacketCaptureSession,
    capture_file_analysis,
    capture_file_summary,
    default_capture_directory,
    find_wireshark_tools,
    list_capture_interfaces,
    new_capture_path,
    open_capture_in_wireshark,
)


FILTER_PRESETS = (
    ("不过滤（捕获全部）", ""),
    ("ARP", "arp"),
    ("ICMP / Ping", "icmp or icmp6"),
    ("SSH（TCP 22）", "tcp port 22"),
    ("DNS（TCP/UDP 53）", "port 53"),
    ("DHCP（UDP 67/68）", "udp port 67 or udp port 68"),
)


class _CaptureBridge(QObject):
    message = pyqtSignal(str)
    finished = pyqtSignal(int)


class _CaptureSummaryWorker(QThread):
    completed = pyqtSignal(dict)

    def __init__(self, tools, capture_file, parent=None):
        super().__init__(parent)
        self.tools = tools
        self.capture_file = capture_file

    def run(self):
        try:
            summary = capture_file_analysis(self.tools, self.capture_file)
        except Exception as exc:
            try:
                summary = capture_file_summary(self.tools, self.capture_file)
            except Exception:
                summary = {"packets": 0, "bytes": 0, "duration": 0.0}
            summary["error"] = str(exc)
        self.completed.emit(summary)


class PacketCaptureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setWindowTitle("网络抓包")
        self.resize(1040, 760)
        self.setMinimumSize(820, 620)
        self.tools = find_wireshark_tools()
        self.session = None
        self._last_capture_file = ""
        self._summary_worker = None
        self._bridge = _CaptureBridge(self)
        self._bridge.message.connect(self._capture_message)
        self._bridge.finished.connect(self._capture_finished)
        self._build_ui()
        self.refresh_interfaces()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        capture_group = QGroupBox("抓包配置")
        form = QGridLayout(capture_group)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.interface_combo = QComboBox()
        self.interface_combo.setMinimumWidth(360)
        self.refresh_button = QPushButton("刷新网卡")
        self.refresh_button.clicked.connect(self.refresh_interfaces)

        self.preset_combo = QComboBox()
        for label, expression in FILTER_PRESETS:
            self.preset_combo.addItem(label, expression)
        self.preset_combo.currentIndexChanged.connect(self._apply_filter_preset)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(
            "可选，例如：host 192.168.10.10 and tcp port 22"
        )
        self.filter_input.setToolTip(
            "这里使用抓包过滤器（BPF）语法，过滤在采集阶段执行"
        )

        self.output_input = QLineEdit(default_capture_directory())
        browse_button = QPushButton("选择目录")
        browse_button.clicked.connect(self.choose_output_directory)
        open_folder_button = QPushButton("打开目录")
        open_folder_button.clicked.connect(self.open_output_directory)

        form.addWidget(QLabel("抓包网卡"), 0, 0)
        form.addWidget(self.interface_combo, 0, 1, 1, 3)
        form.addWidget(self.refresh_button, 0, 4)
        form.addWidget(QLabel("常用过滤"), 1, 0)
        form.addWidget(self.preset_combo, 1, 1)
        form.addWidget(self.filter_input, 1, 2, 1, 3)
        form.addWidget(QLabel("保存目录"), 2, 0)
        form.addWidget(self.output_input, 2, 1, 1, 2)
        form.addWidget(browse_button, 2, 3)
        form.addWidget(open_folder_button, 2, 4)
        form.setColumnStretch(2, 1)
        layout.addWidget(capture_group)

        limits_group = QGroupBox("自动停止条件")
        limits = QHBoxLayout(limits_group)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 86400)
        self.duration_spin.setValue(60)
        self.duration_spin.setSuffix(" 秒")
        self.packet_spin = QSpinBox()
        self.packet_spin.setRange(0, 10_000_000)
        self.packet_spin.setSpecialValueText("不限制")
        self.file_size_spin = QSpinBox()
        self.file_size_spin.setRange(0, 20480)
        self.file_size_spin.setValue(100)
        self.file_size_spin.setSuffix(" MB")
        self.file_size_spin.setSpecialValueText("不限制")
        self.promiscuous_check = QCheckBox("混杂模式")
        self.promiscuous_check.setChecked(True)
        self.promiscuous_check.setToolTip(
            "抓取网卡可见的所有报文；能否看到其他端口流量取决于交换机端口镜像"
        )
        limits.addWidget(QLabel("抓包时长"))
        limits.addWidget(self.duration_spin)
        limits.addWidget(QLabel("最多包数"))
        limits.addWidget(self.packet_spin)
        limits.addWidget(QLabel("最大文件"))
        limits.addWidget(self.file_size_spin)
        limits.addWidget(self.promiscuous_check)
        limits.addStretch(1)
        layout.addWidget(limits_group)

        action_row = QHBoxLayout()
        self.start_button = QPushButton("开始抓包")
        self.start_button.setObjectName("btn_success")
        self.start_button.clicked.connect(self.start_capture)
        self.stop_button = QPushButton("停止抓包")
        self.stop_button.setObjectName("btn_danger")
        self.stop_button.clicked.connect(self.stop_capture)
        self.stop_button.setEnabled(False)
        self.open_capture_button = QPushButton("使用 Wireshark 打开")
        self.open_capture_button.clicked.connect(self.open_last_capture)
        self.open_capture_button.setEnabled(False)
        self.status_label = QLabel("准备就绪" if self.tools else "未检测到 Wireshark")
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.stop_button)
        action_row.addWidget(self.open_capture_button)
        action_row.addWidget(self.status_label)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.file_label = QLabel("尚未生成抓包文件")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)

        self.result_tabs = QTabWidget()
        self.analysis_output = QTextEdit()
        self.analysis_output.setReadOnly(True)
        self.analysis_output.setPlaceholderText(
            "抓包完成后，这里将显示协议、通信对象和常见异常的中文摘要。"
        )
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        terminal_style = (
            "QTextEdit {"
            "background: #073D4A; color: #E6F5F7;"
            "font-family: Consolas, 'Microsoft YaHei'; font-size: 15px;"
            "}"
        )
        self.analysis_output.setStyleSheet(terminal_style)
        self.log_output.setStyleSheet(terminal_style)
        self.result_tabs.addTab(self.analysis_output, "自动分析")
        self.result_tabs.addTab(self.log_output, "运行日志")
        layout.addWidget(self.result_tabs, 1)

        notice = QLabel(
            "电脑默认只能捕获本机可见流量；抓取交换机其他端口流量时，"
            "请先配置端口镜像并将电脑连接到镜像目的端口。"
        )
        notice.setWordWrap(True)
        notice.setObjectName("subtle_label")
        layout.addWidget(notice)

        if not self.tools:
            self.start_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self._append_log("未检测到 Wireshark，请安装官方 Windows 版本后重试。")

    def refresh_interfaces(self):
        self.interface_combo.clear()
        if not self.tools:
            return
        self.refresh_button.setEnabled(False)
        try:
            interfaces = list_capture_interfaces(self.tools)
        except PacketCaptureError as exc:
            self.status_label.setText("网卡读取失败")
            self._append_log(str(exc))
            self.start_button.setEnabled(False)
        else:
            for interface in interfaces:
                self.interface_combo.addItem(interface.label, interface.identifier)
            self.start_button.setEnabled(bool(interfaces))
            self.status_label.setText(f"已识别 {len(interfaces)} 个抓包接口")
            self._append_log(f"已刷新抓包网卡，共 {len(interfaces)} 个接口。")
        finally:
            self.refresh_button.setEnabled(True)

    def _apply_filter_preset(self):
        self.filter_input.setText(self.preset_combo.currentData() or "")

    def choose_output_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择抓包文件保存目录",
            self.output_input.text().strip() or default_capture_directory(),
        )
        if directory:
            self.output_input.setText(directory)

    def open_output_directory(self):
        directory = Path(
            self.output_input.text().strip() or default_capture_directory()
        ).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        os.startfile(str(directory))

    def start_capture(self):
        if not self.tools:
            QMessageBox.warning(self, "无法抓包", "未检测到 Wireshark")
            return
        interface = self.interface_combo.currentData()
        output_directory = self.output_input.text().strip()
        if not output_directory:
            QMessageBox.warning(self, "参数不完整", "请选择抓包文件保存目录")
            return

        capture_file = new_capture_path(output_directory)
        config = PacketCaptureConfig(
            interface=interface or "",
            output_file=capture_file,
            capture_filter=self.filter_input.text().strip(),
            duration_seconds=self.duration_spin.value(),
            packet_limit=self.packet_spin.value(),
            file_size_kb=self.file_size_spin.value() * 1024,
            promiscuous=self.promiscuous_check.isChecked(),
        )
        try:
            config.validate()
            session = PacketCaptureSession(
                self.tools,
                config,
                on_message=self._bridge.message.emit,
                on_finished=self._bridge.finished.emit,
            )
            session.start()
        except (PacketCaptureError, OSError) as exc:
            QMessageBox.warning(self, "启动失败", str(exc))
            self._append_log(f"启动失败：{exc}")
            return

        self.session = session
        self._last_capture_file = capture_file
        self.analysis_output.clear()
        self.analysis_output.setPlaceholderText("正在抓包，结束后自动分析。")
        self.result_tabs.setCurrentWidget(self.log_output)
        self.file_label.setText(f"抓包文件：{capture_file}")
        self._set_capture_running(True)
        self.status_label.setText("正在抓包")
        self._append_log(
            f"开始抓包；网卡：{self.interface_combo.currentText()}；"
            f"过滤器：{config.capture_filter or '无'}"
        )

    def stop_capture(self):
        if not self.session or not self.session.is_running:
            return
        self.stop_button.setEnabled(False)
        self.status_label.setText("正在停止")
        self._append_log("正在停止抓包，请稍候。")
        threading.Thread(
            target=self.session.stop,
            name="AOMT-StopCapture",
            daemon=True,
        ).start()

    def _capture_message(self, message: str):
        packet_match = re.search(r"Packets captured:\s*(\d+)", message, re.IGNORECASE)
        if packet_match:
            self._append_log(f"已捕获 {packet_match.group(1)} 个数据包。")
            return
        lower = message.lower()
        if "permission" in lower or "access is denied" in lower:
            self._append_log(
                "抓包权限不足，请确认 Npcap 正常安装，必要时以管理员身份运行。"
            )
            return
        self._append_log(message)

    def _capture_finished(self, return_code: int):
        self._set_capture_running(False)
        capture_file = self._last_capture_file
        exists = bool(capture_file and Path(capture_file).is_file())
        if return_code == 0 and exists:
            self.status_label.setText("抓包完成，正在统计")
        elif exists:
            self.status_label.setText("抓包已停止，正在统计")
        else:
            self.status_label.setText("抓包失败")
            self._append_log(
                f"抓包进程已结束，退出码 {return_code}，未生成有效文件。"
            )
            return

        self.open_capture_button.setEnabled(True)
        self._summary_worker = _CaptureSummaryWorker(
            self.tools,
            capture_file,
            self,
        )
        self._summary_worker.completed.connect(self._summary_completed)
        self._summary_worker.start()

    def _summary_completed(self, summary: dict):
        packet_count = int(summary.get("packets", 0))
        byte_count = int(summary.get("bytes", 0))
        duration = float(summary.get("duration", 0.0))
        self.status_label.setText("抓包完成")
        self._append_log(
            f"抓包完成：{packet_count} 个数据包，"
            f"{self._format_bytes(byte_count)}，持续 {duration:.2f} 秒。"
        )
        lines = list(summary.get("lines") or ())
        if lines:
            self.analysis_output.setPlainText("\n\n".join(lines))
            self.result_tabs.setCurrentWidget(self.analysis_output)
        else:
            self.analysis_output.setPlainText(
                "自动分析未生成有效结论，请使用 Wireshark 打开抓包文件检查。"
            )
        if summary.get("error"):
            self._append_log(f"统计信息不完整：{summary['error']}")

    def open_last_capture(self):
        if not self.tools or not self._last_capture_file:
            return
        try:
            open_capture_in_wireshark(self.tools, self._last_capture_file)
        except PacketCaptureError as exc:
            QMessageBox.warning(self, "打开失败", str(exc))

    def _set_capture_running(self, running: bool):
        self.start_button.setEnabled(not running and bool(self.interface_combo.count()))
        self.stop_button.setEnabled(running)
        self.interface_combo.setEnabled(not running)
        self.refresh_button.setEnabled(not running)
        self.preset_combo.setEnabled(not running)
        self.filter_input.setEnabled(not running)
        self.output_input.setEnabled(not running)
        self.duration_spin.setEnabled(not running)
        self.packet_spin.setEnabled(not running)
        self.file_size_spin.setEnabled(not running)
        self.promiscuous_check.setEnabled(not running)

    def _append_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")

    @staticmethod
    def _format_bytes(value: int) -> str:
        size = float(max(0, value))
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} GB"

    def closeEvent(self, event):
        if self.session and self.session.is_running:
            answer = QMessageBox.question(
                self,
                "停止抓包",
                "抓包仍在进行，关闭窗口将停止抓包。是否继续？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.session.stop(timeout=2)
            self.session.wait(timeout=2)
        if self._summary_worker and self._summary_worker.isRunning():
            if not self._summary_worker.wait(3000):
                QMessageBox.information(
                    self,
                    "正在整理抓包文件",
                    "抓包文件仍在统计，请稍后再关闭窗口。",
                )
                event.ignore()
                return
        event.accept()
