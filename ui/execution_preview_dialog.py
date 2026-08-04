#!/usr/bin/env python3
"""Unified preflight preview for batch command execution."""

from __future__ import annotations

import os
import re
from typing import Iterable, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)


RISK_RULES = (
    ("高", "重启设备", re.compile(r"^\s*(reboot|reload)\b", re.I)),
    (
        "高",
        "清除或恢复配置",
        re.compile(
            r"^\s*(reset\s+saved-configuration|erase\s+startup-config|"
            r"restore\s+factory-default|factory-default|format\b|"
            r"delete\s+/unreserved\b)",
            re.I,
        ),
    ),
    (
        "高",
        "修改认证信息",
        re.compile(
            r"\b(local-user\b.*\bpassword|password\s+(cipher|simple)|"
            r"set\s+authentication\s+password)\b",
            re.I,
        ),
    ),
    (
        "注意",
        "关闭接口或服务",
        re.compile(r"^\s*(shutdown|undo\s+(ssh|stelnet)\s+server)\b", re.I),
    ),
    (
        "注意",
        "保存持久化配置",
        re.compile(
            r"^\s*(save\b|write\b|copy\s+running-config\s+startup-config)",
            re.I,
        ),
    ),
)

SECRET_PATTERNS = (
    re.compile(r"(?i)(\bpassword\s+(?:cipher\s+|simple\s+)?)(\S+)"),
    re.compile(r"(?i)(\bcommunity\s+(?:read\s+|write\s+)?)(\S+)"),
    re.compile(r"(?i)(\bshared-key\s+(?:cipher\s+|simple\s+)?)(\S+)"),
)


def redact_command(command: str, sensitive_values: Iterable[str] = ()) -> str:
    text = str(command or "")
    for value in sensitive_values or ():
        secret = str(value or "")
        if secret:
            text = text.replace(secret, "********")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(r"\1********", text)
    return text


def command_risks(commands: Iterable[str]) -> List[dict]:
    risks = []
    for index, command in enumerate(commands, start=1):
        for level, label, pattern in RISK_RULES:
            if pattern.search(str(command or "")):
                risks.append({
                    "level": level,
                    "label": label,
                    "line": index,
                })
    return risks


def build_execution_preview(devices, manager) -> List[dict]:
    entries = []
    sensitive_values = list(getattr(manager, "sensitive_values", []) or [])
    for device in devices:
        commands, source = manager._load_commands_for_device(device)
        redacted = [
            redact_command(command, sensitive_values)
            for command in commands
        ]
        entries.append({
            "name": str(getattr(device, "name", "") or ""),
            "ip": str(getattr(device, "ip", "") or ""),
            "brand": str(getattr(device, "brand", "") or ""),
            "source": os.path.basename(source) if source else "未匹配脚本",
            "commands": redacted,
            "command_count": len(redacted),
            "risks": command_risks(commands),
            "missing": not bool(commands),
        })
    return entries


class ExecutionPreviewDialog(QDialog):
    def __init__(
        self,
        entries,
        save_after_exec=False,
        detect_l2_uplink=False,
        parent=None,
    ):
        super().__init__(parent)
        self.entries = list(entries or [])
        flags = self.windowFlags()
        flags &= ~Qt.WindowContextHelpButtonHint
        flags |= Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        self.setWindowTitle("执行前预览")
        self.resize(1180, 760)
        self.setMinimumSize(880, 580)
        self._build_ui(save_after_exec, detect_l2_uplink)
        self._populate()

    def _build_ui(self, save_after_exec, detect_l2_uplink):
        layout = QVBoxLayout(self)
        executable = sum(not item["missing"] for item in self.entries)
        high_risk = sum(
            any(risk["level"] == "高" for risk in item["risks"])
            for item in self.entries
        )
        missing = sum(item["missing"] for item in self.entries)
        options = []
        if save_after_exec:
            options.append("执行后保存配置")
        if detect_l2_uplink:
            options.append("探测二层上联口")
        option_text = "、".join(options) if options else "无附加操作"
        self.summary_label = QLabel(
            f"目标 {len(self.entries)} 台，可执行 {executable} 台，"
            f"未匹配 {missing} 台，高风险设备 {high_risk} 台；{option_text}"
        )
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "设备名称", "IP 地址", "品牌", "脚本来源", "命令数", "风险",
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
        self.detail.setFont(QFont("Consolas", 12))
        splitter.addWidget(self.detail)
        splitter.setSizes([260, 390])
        layout.addWidget(splitter, 1)

        self.confirm_check = QCheckBox(
            "我已核对目标设备、脚本来源和实际命令"
        )
        self.confirm_check.toggled.connect(self._update_accept_state)
        layout.addWidget(self.confirm_check)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.button(QDialogButtonBox.Ok).setText("确认执行")
        self.buttons.button(QDialogButtonBox.Cancel).setText("取消")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._update_accept_state()

    def _populate(self):
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            if entry["missing"]:
                risk_text = "未匹配，将跳过"
            elif entry["risks"]:
                levels = {risk["level"] for risk in entry["risks"]}
                risk_text = "高风险" if "高" in levels else "需注意"
            else:
                risk_text = "未发现"
            values = [
                entry["name"],
                entry["ip"],
                entry["brand"],
                entry["source"],
                str(entry["command_count"]),
                risk_text,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (4, 5):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)
        if self.entries:
            self.table.selectRow(0)

    def _show_detail(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.entries):
            return
        entry = self.entries[row]
        lines = [
            f"设备：{entry['name'] or entry['ip']}",
            f"地址：{entry['ip']}",
            f"品牌：{entry['brand'] or '未指定'}",
            f"脚本：{entry['source']}",
            "",
        ]
        if entry["missing"]:
            lines.append("没有可执行命令，本设备将在任务中跳过。")
        else:
            if entry["risks"]:
                lines.append("风险提示：")
                for risk in entry["risks"]:
                    lines.append(
                        f"- [{risk['level']}] 第 {risk['line']} 行：{risk['label']}"
                    )
                lines.append("")
            lines.append("实际命令（敏感值已隐藏）：")
            for index, command in enumerate(entry["commands"], start=1):
                lines.append(f"{index:>3}. {command}")
        self.detail.setPlainText("\n".join(lines))

    def _update_accept_state(self):
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(
            bool(self.entries) and self.confirm_check.isChecked()
        )
