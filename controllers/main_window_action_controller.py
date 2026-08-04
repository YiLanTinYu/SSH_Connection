"""Handle common user actions initiated from the main window."""

from __future__ import annotations

import os

from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QFileDialog, QMessageBox

class MainWindowActionController:
    def __init__(
        self,
        window,
        app_name="AOMT",
        version="",
        author="",
        desktop_services=QDesktopServices,
        url_class=QUrl,
    ):
        self.window = window
        self.app_name = app_name
        self.version = version
        self.author = author
        self.desktop_services = desktop_services
        self.url_class = url_class

    def open_user_guide(self):
        guide_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "USER_GUIDE.md",
        )
        if not os.path.isfile(guide_path):
            QMessageBox.warning(
                self.window,
                "使用说明",
                f"未找到使用说明文件：\n{guide_path}",
            )
            return
        if not self.desktop_services.openUrl(
            self.url_class.fromLocalFile(guide_path)
        ):
            QMessageBox.warning(
                self.window,
                "使用说明",
                "无法调用系统默认程序打开 USER_GUIDE.md。",
            )

    def show_about_dialog(self):
        QMessageBox.about(
            self.window,
            "关于 AOMT",
            f"{self.app_name}\n\n版本：v{self.version}\n作者：{self.author}",
        )

    def close_application(self):
        self.window.close()

    def delete_selected_device(self):
        rows = sorted(
            {index.row() for index in self.window.device_table.selectedIndexes()},
            reverse=True,
        )
        if not rows:
            self.window._warn("请先在设备列表中选中要移除的设备")
            return
        if not self.window._confirm_action(
            "确认移除",
            f"确定要移除选中的 {len(rows)} 台设备吗？",
        ):
            return
        removed = self.window._device_inventory_controller.remove_rows(rows)
        self.window.update_device_table()
        self.window._log_info(f"[移除]  已移除 {removed} 台设备")
        self.window._set_status(f"已移除 {removed} 台设备")
        self.window._update_device_count()

    def clear_devices(self):
        if not self.window._confirm_action(
            "确认清空",
            "确定要清空所有设备吗？\n\n此操作会移除当前设备列表中的全部设备。",
        ):
            return
        self.window._device_inventory_controller.clear()
        self.window.update_device_table()
        self.window.log_text.clear()
        self.window._log_info("[清空]  设备列表已清空")
        self.window.logger.log_operation("清空设备列表")
        self.window._set_status("设备列表已清空")
        self.window._update_device_count()

    def view_logs(self):
        files = self.window.logger.get_log_files()
        log_dir = os.path.abspath(self.window.logger.log_dir)
        message = (
            "日志文件位置\n\n"
            f"  ✅  成功日志: {len(files['success'])} 个文件\n"
            f"  ❌  失败日志: {len(files['failure'])} 个文件\n"
            f"  📋  操作日志: {len(files['operation'])} 个文件\n\n"
            f"  📁  日志目录:\n  {log_dir}"
        )
        QMessageBox.information(self.window, "日志信息", message)

    def clear_connection_log(self):
        self.window.log_text.clear()
        self.window._set_status("连接日志已清空")
        QTimer.singleShot(3000, self.window._update_device_count)

    def browse_command_file(self):
        if self.window.cmd_mode_combo.currentData() == "per_device":
            directory = QFileDialog.getExistingDirectory(
                self.window,
                "选择设备脚本目录",
                "",
            )
            if not directory:
                return
            self.window._command_directory = directory
            self.window._clear_parameterized_template()
            display = os.path.basename(os.path.normpath(directory)) or directory
            self.window.cmd_file_label.setText(display)
            self.window.cmd_file_label.setToolTip(directory)
            self.window._log_info(
                f"[命令]  已选择设备脚本目录: {directory}"
            )
            self.window._set_status(f"设备脚本目录: {display}")
            QTimer.singleShot(3000, self.window._update_device_count)
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self.window,
            "选择命令文件",
            "",
            "文本文件 (*.txt);;所有文件 (*.*)",
        )
        if not file_path:
            return
        self.window._command_file = file_path
        self.window._clear_parameterized_template()
        display = os.path.basename(file_path)
        self.window.cmd_file_label.setText(display)
        self.window.cmd_file_label.setToolTip(file_path)
        self.window._log_info(f"[命令]  已选择命令文件: {file_path}")
        self.window._set_status(f"命令文件: {display}")
        QTimer.singleShot(3000, self.window._update_device_count)

    def reset_command_file(self):
        self.window._command_file = None
        self.window._command_directory = None
        self.window._clear_parameterized_template()
        if self.window.cmd_mode_combo.currentData() == "per_device":
            self.window.cmd_file_label.setText("请选择设备脚本目录")
        else:
            self.window.cmd_file_label.setText("SSH_command.txt  (默认)")
        self.window.cmd_file_label.setToolTip("")
        self.window._log_info(
            "[命令]  已恢复使用默认命令文件 SSH_command.txt"
        )
        self.window._set_status("命令文件已恢复为默认")
        QTimer.singleShot(3000, self.window._update_device_count)

    def on_command_mode_changed(self):
        if self.window._command_lines is not None:
            self.window._clear_parameterized_template()
        per_device = self.window.cmd_mode_combo.currentData() == "per_device"
        if per_device:
            self.window._command_file = None
            self.window.cmd_browse_btn.setText("选择脚本目录")
            self.window.cmd_file_label.setText(
                os.path.basename(os.path.normpath(self.window._command_directory))
                if self.window._command_directory
                else "请选择设备脚本目录"
            )
            self.window._cmd_tip_label.setText(
                "仅按设备名称匹配：设备名 SW1 → SW1.txt"
            )
        else:
            self.window._command_directory = None
            self.window.cmd_browse_btn.setText("选择文件")
            self.window.cmd_file_label.setText(
                os.path.basename(self.window._command_file)
                if self.window._command_file
                else "SSH_command.txt  (默认)"
            )
            self.window._cmd_tip_label.setText(
                "命令原样发送；每行一条，# 开头为注释"
            )
        self.window.cmd_file_label.setToolTip("")
