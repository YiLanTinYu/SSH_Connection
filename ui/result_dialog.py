#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Per-device execution result center."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from utils.result_export import (
    export_results_csv,
    export_results_json,
    export_results_xlsx,
)


class ResultCenterDialog(QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.results = list(results or [])
        flags = self.windowFlags()
        flags &= ~Qt.WindowContextHelpButtonHint
        flags |= Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        self.setWindowTitle("执行结果中心")
        self.resize(1320, 820)
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        success = sum(bool(item.get("task_success")) for item in self.results)
        self.summary_label = QLabel(
            f"设备 {len(self.results)} 台　成功 {success} 台　"
            f"失败 {len(self.results) - success} 台"
        )
        layout.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "设备名称", "分组", "IP 地址", "品牌", "型号",
            "状态", "总耗时", "连接准备", "任务执行", "命令数", "错误",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        splitter.addWidget(self.table)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("Consolas", 11))
        splitter.addWidget(self.detail)
        splitter.setSizes([300, 450])
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        export_xlsx = QPushButton("导出 Excel")
        export_csv = QPushButton("导出 CSV")
        export_json = QPushButton("导出 JSON")
        close = QPushButton("关闭")
        export_xlsx.clicked.connect(lambda: self._export("xlsx"))
        export_csv.clicked.connect(lambda: self._export("csv"))
        export_json.clicked.connect(lambda: self._export("json"))
        close.clicked.connect(self.accept)
        for button in (export_xlsx, export_csv, export_json, close):
            buttons.addWidget(button)
        layout.addLayout(buttons)

    def _populate(self):
        self.table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            device = result.get("device_info", {}) or {}
            values = [
                device.get("name", ""),
                device.get("group", ""),
                device.get("ip", ""),
                result.get("brand_detected") or device.get("brand", ""),
                result.get("model_detected", ""),
                "成功" if result.get("task_success") else "失败",
                f"{float(result.get('duration_seconds') or 0):.2f} 秒",
                self._format_optional_duration(
                    result.get("connection_duration_seconds")
                ),
                self._format_optional_duration(
                    result.get("operation_duration_seconds")
                ),
                str(len(result.get("command_results", []) or [])),
                result.get("error_message", "") or "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in (5, 6, 7, 8, 9):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)
        if self.results:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("当前还没有执行结果。")

    def _show_selected_detail(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.results):
            return
        result = self.results[row]
        device = result.get("device_info", {}) or {}
        lines = [
            f"设备名称：{device.get('name', '')}",
            f"IP 地址：{device.get('ip', '')}",
            f"分组：{device.get('group', '') or '未分组'}",
            f"标签：{device.get('tags', '') or '无'}",
            f"状态：{'成功' if result.get('task_success') else '失败'}",
            f"开始时间：{result.get('started_at', '')}",
            f"结束时间：{result.get('finished_at', '')}",
            f"总耗时：{float(result.get('duration_seconds') or 0):.2f} 秒",
            f"连接准备：{self._format_optional_duration(result.get('connection_duration_seconds'))}",
            f"任务执行：{self._format_optional_duration(result.get('operation_duration_seconds'))}",
        ]
        if result.get("error_message"):
            lines.append(f"错误：{result['error_message']}")
        lines.append("\n" + "=" * 72)
        commands = result.get("command_results", []) or []
        if not commands:
            lines.append("没有命令执行记录。")
        for index, item in enumerate(commands, start=1):
            lines.extend([
                f"\n[{index}] {item.get('command', '')}",
                f"时间：{item.get('timestamp', '')}　"
                f"耗时：{float(item.get('duration_seconds') or 0):.2f} 秒",
                "-" * 72,
                item.get("output", "") or "(无输出)",
            ])
        self.detail.setPlainText("\n".join(lines))

    @staticmethod
    def _format_optional_duration(value):
        if value is None:
            return "-"
        return f"{float(value or 0):.2f} 秒"

    def _export(self, file_type):
        if not self.results:
            QMessageBox.warning(self, "导出结果", "当前没有可导出的执行结果")
            return
        filters = {
            "xlsx": ("Excel 工作簿 (*.xlsx)", ".xlsx", export_results_xlsx),
            "csv": ("CSV 文件 (*.csv)", ".csv", export_results_csv),
            "json": ("JSON 文件 (*.json)", ".json", export_results_json),
        }
        file_filter, suffix, exporter = filters[file_type]
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出执行结果", f"AOMT_执行结果{suffix}", file_filter
        )
        if not file_path:
            return
        if not file_path.lower().endswith(suffix):
            file_path += suffix
        try:
            exporter(self.results, file_path)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        QMessageBox.information(
            self, "导出完成", f"执行结果已保存到：\n{os.path.abspath(file_path)}"
        )
