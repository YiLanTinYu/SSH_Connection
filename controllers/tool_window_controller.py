"""Open and reuse tool dialogs owned by the main window."""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from ui.config_diff_dialog import ConfigDiffDialog
from ui.file_transfer_dialog import FileTransferDialog
from ui.packet_capture_dialog import PacketCaptureDialog
from ui.result_dialog import ResultCenterDialog
from ui.serial_console import SerialConsoleDialog
from ui.ssh_console import SSHConsoleDialog
from ui.subnet_calculator_dialog import SubnetCalculatorDialog
from ui.task_history_dialog import TaskHistoryDialog
from utils.maintenance_tools import unified_config_diff


class ToolWindowController:
    def __init__(
        self,
        window,
        serial_dialog=SerialConsoleDialog,
        ssh_dialog=SSHConsoleDialog,
        transfer_dialog=FileTransferDialog,
        capture_dialog=PacketCaptureDialog,
    ):
        self.window = window
        self.serial_dialog = serial_dialog
        self.ssh_dialog = ssh_dialog
        self.transfer_dialog = transfer_dialog
        self.capture_dialog = capture_dialog

    def _show_singleton(self, attribute: str, factory, *args):
        dialog = getattr(self.window, attribute, None)
        if dialog is None:
            dialog = factory(*args, self.window)
            setattr(self.window, attribute, dialog)
            dialog.setAttribute(Qt.WA_DeleteOnClose)
            dialog.destroyed.connect(
                lambda: setattr(self.window, attribute, None)
            )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def show_serial_console(self):
        return self._show_singleton("_serial_console", self.serial_dialog)

    def show_ssh_console(self):
        devices = self.window._get_task_devices("ssh_console")
        dialog = getattr(self.window, "_ssh_console", None)
        if dialog is None:
            return self._show_singleton(
                "_ssh_console",
                self.ssh_dialog,
                devices,
            )
        dialog.set_devices(devices)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def show_file_transfer(self):
        return self._show_singleton(
            "_file_transfer_dialog",
            self.transfer_dialog,
        )

    def show_packet_capture(self):
        return self._show_singleton(
            "_packet_capture_dialog",
            self.capture_dialog,
        )

    def open_result_center(self):
        results = self.window.execution_results
        if not results and self.window.ssh_manager:
            results = self.window.ssh_manager.get_results()
        ResultCenterDialog(results, self.window).exec_()

    def show_task_history(self):
        try:
            dialog = TaskHistoryDialog(
                self.window._get_task_audit_store(),
                self.window,
            )
        except Exception as exc:
            QMessageBox.warning(
                self.window,
                "批量执行历史",
                f"无法打开任务审计数据库：\n{exc}",
            )
            return
        dialog.exec_()

    def show_config_diff(self):
        first_path, _ = QFileDialog.getOpenFileName(
            self.window,
            "选择第一份配置",
            "",
            "配置文件 (*.txt *.cfg *.conf *.log);;所有文件 (*.*)",
        )
        if not first_path:
            return
        second_path, _ = QFileDialog.getOpenFileName(
            self.window,
            "选择第二份配置",
            os.path.dirname(first_path),
            "配置文件 (*.txt *.cfg *.conf *.log);;所有文件 (*.*)",
        )
        if not second_path:
            return
        try:
            diff_text = unified_config_diff(first_path, second_path)
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self.window, "配置对比失败", str(exc))
            return

        dialog = ConfigDiffDialog(
            first_path,
            second_path,
            diff_text,
            self.window,
        )
        dialog.diff_saved.connect(
            lambda path: self.window._log_info(
                f"[配置对比] 差异文件已保存: {path}"
            )
        )
        self.window._log_info(
            f"[配置对比] 已比较 {os.path.basename(first_path)} 和 "
            f"{os.path.basename(second_path)}"
        )
        dialog.exec_()

    def show_subnet_calculator(self):
        SubnetCalculatorDialog(self.window).exec_()
