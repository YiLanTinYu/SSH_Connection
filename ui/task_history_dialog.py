#!/usr/bin/env python3
"""Read-only task audit history viewer."""

from __future__ import annotations

import json

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)


STATUS_LABELS = {
    "running": "运行中",
    "completed": "已完成",
    "cancelled": "已取消",
    "interrupted": "异常中断",
}


class TaskHistoryDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.tasks = []
        flags = self.windowFlags()
        flags &= ~Qt.WindowContextHelpButtonHint
        flags |= Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        self.setWindowTitle("批量执行历史")
        self.resize(1250, 780)
        self.setMinimumSize(900, 600)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "编号", "开始时间", "操作用户", "任务类型", "脚本来源",
            "目标", "成功", "失败", "状态",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._show_detail)
        splitter.addWidget(self.table)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("Consolas", 11))
        splitter.addWidget(self.detail)
        splitter.setSizes([300, 390])
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        refresh = QPushButton("刷新")
        export = QPushButton("导出 JSON")
        close = QPushButton("关闭")
        refresh.clicked.connect(self.refresh)
        export.clicked.connect(self._export_json)
        close.clicked.connect(self.accept)
        for button in (refresh, export, close):
            buttons.addWidget(button)
        layout.addLayout(buttons)

    def refresh(self):
        self.tasks = self.store.list_tasks()
        self.table.setRowCount(len(self.tasks))
        for row, task in enumerate(self.tasks):
            values = [
                str(task["id"]),
                task["started_at"],
                task["operator_name"],
                task["task_type"],
                task["source_label"],
                str(task["target_count"]),
                str(task["success_count"]),
                str(task["failure_count"]),
                STATUS_LABELS.get(task["status"], task["status"]),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 5, 6, 7, 8):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)
        if self.tasks:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("暂无批量执行历史。")

    def _selected_detail(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.tasks):
            return {}
        return self.store.task_detail(self.tasks[row]["id"])

    def _show_detail(self):
        detail = self._selected_detail()
        task = detail.get("task", {})
        if not task:
            return
        try:
            options = json.loads(task.get("options_json") or "{}")
        except json.JSONDecodeError:
            options = {}
        lines = [
            f"任务编号：{task['id']}",
            f"开始时间：{task['started_at']}",
            f"结束时间：{task.get('finished_at') or '尚未结束'}",
            f"操作用户：{task.get('operator_name', '')}",
            f"任务类型：{task.get('task_type', '')}",
            f"脚本来源：{task.get('source_label', '')}",
            f"脚本指纹：{task.get('source_hash', '')}",
            f"执行选项：{json.dumps(options, ensure_ascii=False)}",
            f"状态：{STATUS_LABELS.get(task.get('status'), task.get('status', ''))}",
            "",
            "设备结果：",
        ]
        for device in detail.get("devices", []):
            label = device.get("device_name") or device.get("ip")
            line = (
                f"- {label} [{device.get('ip')}:{device.get('port')}] "
                f"{device.get('status')}  {device.get('duration_seconds', 0):.2f} 秒"
            )
            if device.get("error_message"):
                line += f"  错误：{device['error_message']}"
            lines.append(line)
        self.detail.setPlainText("\n".join(lines))

    def _export_json(self):
        detail = self._selected_detail()
        if not detail:
            QMessageBox.information(self, "导出历史", "请先选择一条任务记录")
            return
        task_id = detail["task"]["id"]
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出任务审计记录",
            f"task_audit_{task_id}.json",
            "JSON 文件 (*.json)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(detail, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", f"无法保存审计记录：\n{exc}")
            return
        QMessageBox.information(self, "导出完成", f"已保存：\n{path}")
