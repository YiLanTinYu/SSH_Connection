#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""FTP/TFTP file transfer window for switch maintenance."""

from __future__ import annotations

import os
import secrets
import shutil
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, Qt, pyqtSignal
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
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.file_transfer_service import (
    FTPServiceConfig,
    FTPTransferService,
    TFTPServiceConfig,
    TFTPTransferService,
    TransferServiceError,
    available_transfer_backends,
    discover_local_addresses,
    normalize_shared_directory,
)


class _TransferEventBridge(QObject):
    message = pyqtSignal(str)


class FileTransferDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setWindowTitle("交换机文件传输")
        self.resize(1080, 760)
        self.setMinimumSize(880, 620)
        self.service = None
        self._local_addresses = discover_local_addresses()
        self._bridge = _TransferEventBridge(self)
        self._bridge.message.connect(self._append_log)
        self._build_ui()
        self._populate_bind_addresses()
        self._protocol_changed()
        self.refresh_files()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        settings_group = QGroupBox("服务配置")
        settings = QGridLayout(settings_group)
        settings.setHorizontalSpacing(10)
        settings.setVerticalSpacing(8)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItem("TFTP", "tftp")
        self.protocol_combo.addItem("FTP", "ftp")
        self.protocol_combo.currentIndexChanged.connect(self._protocol_changed)

        self.bind_combo = QComboBox()
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.valueChanged.connect(self._update_command_preview)

        self.root_input = QLineEdit(
            os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "AOMT_File_Transfer",
            )
        )
        self.root_input.textChanged.connect(self._update_command_preview)
        browse_button = QPushButton("选择目录")
        browse_button.clicked.connect(self.choose_shared_directory)
        open_folder_button = QPushButton("打开目录")
        open_folder_button.clicked.connect(self.open_shared_directory)

        self.allow_upload_check = QCheckBox("允许交换机上传文件")
        self.allow_upload_check.setToolTip(
            "关闭时服务为只读下载；开启后交换机可以向共享目录写入文件，"
            "同名文件可能被覆盖"
        )

        settings.addWidget(QLabel("协议"), 0, 0)
        settings.addWidget(self.protocol_combo, 0, 1)
        settings.addWidget(QLabel("监听地址"), 0, 2)
        settings.addWidget(self.bind_combo, 0, 3)
        settings.addWidget(QLabel("端口"), 0, 4)
        settings.addWidget(self.port_spin, 0, 5)
        settings.addWidget(QLabel("共享目录"), 1, 0)
        settings.addWidget(self.root_input, 1, 1, 1, 3)
        settings.addWidget(browse_button, 1, 4)
        settings.addWidget(open_folder_button, 1, 5)
        settings.addWidget(self.allow_upload_check, 2, 0, 1, 3)
        settings.setColumnStretch(1, 1)
        settings.setColumnStretch(3, 1)

        self.ftp_options = QWidget()
        ftp_layout = QGridLayout(self.ftp_options)
        ftp_layout.setContentsMargins(0, 0, 0, 0)
        self.username_input = QLineEdit("aomt")
        self.password_input = QLineEdit(secrets.token_urlsafe(9))
        self.password_input.setEchoMode(QLineEdit.Normal)
        self.username_input.textChanged.connect(self._update_command_preview)
        self.passive_start_spin = QSpinBox()
        self.passive_start_spin.setRange(1024, 65535)
        self.passive_start_spin.setValue(50000)
        self.passive_end_spin = QSpinBox()
        self.passive_end_spin.setRange(1024, 65535)
        self.passive_end_spin.setValue(50020)
        ftp_layout.addWidget(QLabel("FTP 用户名"), 0, 0)
        ftp_layout.addWidget(self.username_input, 0, 1)
        ftp_layout.addWidget(QLabel("FTP 密码"), 0, 2)
        ftp_layout.addWidget(self.password_input, 0, 3)
        ftp_layout.addWidget(QLabel("被动端口"), 0, 4)
        ftp_layout.addWidget(self.passive_start_spin, 0, 5)
        ftp_layout.addWidget(QLabel("至"), 0, 6)
        ftp_layout.addWidget(self.passive_end_spin, 0, 7)
        ftp_layout.setColumnStretch(1, 1)
        ftp_layout.setColumnStretch(3, 1)
        settings.addWidget(self.ftp_options, 3, 0, 1, 6)
        layout.addWidget(settings_group)

        action_row = QHBoxLayout()
        self.start_button = QPushButton("启动服务")
        self.start_button.setObjectName("btn_success")
        self.start_button.clicked.connect(self.start_service)
        self.stop_button = QPushButton("停止服务")
        self.stop_button.setObjectName("btn_danger")
        self.stop_button.clicked.connect(self.stop_service)
        self.stop_button.setEnabled(False)
        self.status_label = QLabel("服务未启动")
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.stop_button)
        action_row.addWidget(self.status_label)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(108)
        self.command_preview.setToolTip(
            "命令仅供当前 H3C 模拟环境参考，程序不会自动发送"
        )
        layout.addWidget(self.command_preview)

        splitter = QSplitter(Qt.Horizontal)
        file_panel = QWidget()
        file_layout = QVBoxLayout(file_panel)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.addWidget(QLabel("共享文件"))
        self.file_list = QListWidget()
        file_layout.addWidget(self.file_list, 1)
        file_actions = QHBoxLayout()
        add_files = QPushButton("添加文件")
        remove_file = QPushButton("移除选中")
        refresh_files = QPushButton("刷新")
        add_files.clicked.connect(self.add_shared_files)
        remove_file.clicked.connect(self.remove_selected_file)
        refresh_files.clicked.connect(self.refresh_files)
        file_actions.addWidget(add_files)
        file_actions.addWidget(remove_file)
        file_actions.addWidget(refresh_files)
        file_layout.addLayout(file_actions)

        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("传输日志"))
        log_header.addStretch(1)
        clear_log = QPushButton("清空")
        clear_log.clicked.connect(self.log_output_clear)
        log_header.addWidget(clear_log)
        log_layout.addLayout(log_header)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(
            "QTextEdit {"
            "background: #073D4A; color: #E6F5F7;"
            "font-family: Consolas, 'Microsoft YaHei';"
            "}"
        )
        log_layout.addWidget(self.log_output, 1)

        splitter.addWidget(file_panel)
        splitter.addWidget(log_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        notice = QLabel(
            "TFTP 和 FTP 均为明文协议，请只在可信的隔离运维网络中临时启用。"
        )
        notice.setObjectName("subtle_label")
        layout.addWidget(notice)

    def _populate_bind_addresses(self):
        self.bind_combo.clear()
        self.bind_combo.addItem("0.0.0.0（所有 IPv4 网卡）", "0.0.0.0")
        for address in self._local_addresses:
            self.bind_combo.addItem(address, address)
        self.bind_combo.currentIndexChanged.connect(self._update_command_preview)

    def _protocol_changed(self):
        protocol = self.protocol_combo.currentData()
        self.ftp_options.setVisible(protocol == "ftp")
        self.port_spin.setValue(21 if protocol == "ftp" else 69)
        self._update_command_preview()

    def _effective_client_address(self):
        bind_host = self.bind_combo.currentData() or "0.0.0.0"
        if bind_host not in ("0.0.0.0", "::"):
            return bind_host
        for address in self._local_addresses:
            if ":" not in address:
                return address
        return "<本机运维网卡IP>"

    def _update_command_preview(self):
        if not hasattr(self, "command_preview"):
            return
        address = self._effective_client_address()
        protocol = self.protocol_combo.currentData()
        ipv6_keyword = " ipv6" if ":" in address else ""
        if protocol == "ftp":
            text = (
                "H3C 参考命令（程序不会自动发送）：\n"
                f"<H3C> ftp{ipv6_keyword} {address}\n"
                f"用户名：{self.username_input.text() if hasattr(self, 'username_input') else 'aomt'}"
                "  登录后可使用 binary、dir、get <文件名>、put <设备文件>。"
            )
        else:
            text = (
                "H3C 参考命令（程序不会自动发送）：\n"
                f"下载到交换机：tftp{ipv6_keyword} {address} get <共享文件名>\n"
                f"上传到电脑：tftp{ipv6_keyword} {address} "
                "put <设备文件> <保存文件名>"
            )
        self.command_preview.setPlainText(text)

    def choose_shared_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择文件传输共享目录",
            self.root_input.text().strip(),
        )
        if directory:
            self.root_input.setText(directory)
            self.refresh_files()

    def _shared_root(self):
        try:
            root = normalize_shared_directory(self.root_input.text().strip())
        except (OSError, TransferServiceError) as exc:
            QMessageBox.warning(self, "共享目录", str(exc))
            return ""
        self.root_input.setText(root)
        return root

    def open_shared_directory(self):
        root = self._shared_root()
        if root:
            os.startfile(root)

    def add_shared_files(self):
        root = self._shared_root()
        if not root:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "添加到共享目录",
            "",
            "所有文件 (*.*)",
        )
        for source in paths:
            destination = os.path.join(root, os.path.basename(source))
            if os.path.exists(destination):
                answer = QMessageBox.question(
                    self,
                    "文件已存在",
                    f"{os.path.basename(source)} 已存在，是否覆盖？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    continue
            try:
                shutil.copy2(source, destination)
                self._append_log(f"已添加共享文件：{os.path.basename(source)}")
            except OSError as exc:
                QMessageBox.warning(self, "添加失败", str(exc))
        self.refresh_files()

    def remove_selected_file(self):
        item = self.file_list.currentItem()
        root = self._shared_root()
        if item is None or not root:
            return
        name = item.data(Qt.UserRole)
        path = Path(root, name).resolve()
        try:
            path.relative_to(Path(root).resolve())
        except ValueError:
            return
        answer = QMessageBox.question(
            self,
            "移除共享文件",
            f"确定永久删除共享目录中的“{name}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            path.unlink()
        except OSError as exc:
            QMessageBox.warning(self, "删除失败", str(exc))
            return
        self._append_log(f"已删除共享文件：{name}")
        self.refresh_files()

    def refresh_files(self):
        self.file_list.clear()
        root_text = self.root_input.text().strip()
        if not root_text:
            return
        root = Path(root_text).expanduser()
        if not root.is_dir():
            return
        for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
            if not path.is_file():
                continue
            size = path.stat().st_size
            item_text = f"{path.name}    {self._format_size(size)}"
            self.file_list.addItem(item_text)
            item = self.file_list.item(self.file_list.count() - 1)
            item.setData(Qt.UserRole, path.name)

    @staticmethod
    def _format_size(size):
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    def _build_service(self):
        root = self._shared_root()
        if not root:
            return None
        protocol = self.protocol_combo.currentData()
        bind_host = self.bind_combo.currentData() or "0.0.0.0"
        if protocol == "ftp":
            config = FTPServiceConfig(
                root=root,
                bind_host=bind_host,
                port=self.port_spin.value(),
                username=self.username_input.text(),
                password=self.password_input.text(),
                allow_upload=self.allow_upload_check.isChecked(),
                passive_port_start=self.passive_start_spin.value(),
                passive_port_end=self.passive_end_spin.value(),
            )
            return FTPTransferService(config, self._bridge.message.emit)
        config = TFTPServiceConfig(
            root=root,
            bind_host=bind_host,
            port=self.port_spin.value(),
            allow_upload=self.allow_upload_check.isChecked(),
        )
        return TFTPTransferService(config, self._bridge.message.emit)

    def start_service(self):
        if self.service is not None:
            return
        protocol = self.protocol_combo.currentData()
        backends = available_transfer_backends()
        if not backends.get(protocol):
            package = "pyftpdlib" if protocol == "ftp" else "partftpy"
            QMessageBox.critical(
                self,
                "缺少文件传输组件",
                f"当前环境未安装 {package}，请重新运行 build.bat 或安装项目依赖。",
            )
            return
        try:
            service = self._build_service()
            if service is None:
                return
            service.start()
        except (OSError, ValueError, TransferServiceError) as exc:
            QMessageBox.critical(self, "服务启动失败", str(exc))
            return
        self.service = service
        self.status_label.setText(
            f"{protocol.upper()} 服务运行中："
            f"{service.bound_host}:{service.bound_port}"
        )
        self._set_running(True)
        self.refresh_files()

    def stop_service(self):
        service = self.service
        self.service = None
        if service is not None:
            service.stop()
        self.status_label.setText("服务未启动")
        self._set_running(False)
        self.refresh_files()

    def _set_running(self, running):
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        for widget in (
            self.protocol_combo,
            self.bind_combo,
            self.port_spin,
            self.root_input,
            self.allow_upload_check,
            self.username_input,
            self.password_input,
            self.passive_start_spin,
            self.passive_end_spin,
        ):
            widget.setEnabled(not running)

    def _append_log(self, message):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{stamp}] {message}")
        self.refresh_files()

    def log_output_clear(self):
        self.log_output.clear()

    def closeEvent(self, event):
        self.stop_service()
        event.accept()
