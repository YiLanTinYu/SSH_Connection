#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Parameter editor and command preview for built-in configuration templates."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from config.template_renderer import TemplateValidationError, render_template


class ConfigTemplateDialog(QDialog):
    def __init__(self, template: dict, parent=None):
        super().__init__(parent)
        self.template = template
        self.rendered_template = None
        self.inputs = {}
        self.setWindowTitle(f"配置模板 · {template.get('name', '')}")
        self.resize(920, 760)
        self.setMinimumSize(760, 620)
        self._build_ui()
        self._refresh_preview()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        heading = QLabel(self.template.get("name", "配置模板"))
        heading.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(heading)

        brand = str(self.template.get("brand", "")).upper()
        description = self.template.get("description", "")
        info = QLabel(f"目标品牌：{brand}　　{description}")
        info.setWordWrap(True)
        layout.addWidget(info)

        warning = QLabel(
            "模板命令不会跨品牌转换。密码只保存在当前内存中，不写入模板文件；"
            "执行前请核对设备型号和软件版本。"
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background:#FFF4E8; color:#8A4B16; padding:8px; border:1px solid #F2C48D;"
        )
        layout.addWidget(warning)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(8)
        for field in self.template.get("parameters", ()):
            editor = QLineEdit(str(field.get("default", "")))
            if field.get("sensitive"):
                editor.setEchoMode(QLineEdit.Password)
                editor.setPlaceholderText("不会保存到磁盘")
            editor.textChanged.connect(self._refresh_preview)
            self.inputs[field["name"]] = editor
            form.addRow(field.get("label", field["name"]) + "：", editor)
        layout.addLayout(form)

        manual_steps = self._manual_steps_from_defaults()
        self.manual_label = QLabel()
        self.manual_label.setWordWrap(True)
        if manual_steps:
            self.manual_label.setText(
                "必须先手动完成：\n" + "\n".join(f"• {step}" for step in manual_steps)
            )
            self.manual_label.setStyleSheet(
                "background:#FDECEC; color:#9C2F2F; padding:8px; border:1px solid #E8A3A3;"
            )
            layout.addWidget(self.manual_label)

        preview_title = QLabel("最终命令预览（密码已隐藏）")
        preview_title.setStyleSheet("font-weight:700;")
        layout.addWidget(preview_title)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setStyleSheet(
            "QTextEdit { background:#073D4A; color:#E6F5F7;"
            "font-family:Consolas, 'Microsoft YaHei'; font-size:15px; }"
        )
        layout.addWidget(self.preview, 1)

        self.validation_label = QLabel()
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        button_row = QHBoxLayout()
        self.copy_button = QPushButton("复制可执行命令")
        self.copy_button.clicked.connect(self._copy_commands)
        button_row.addWidget(self.copy_button)
        button_row.addStretch(1)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.button(QDialogButtonBox.Ok).setText("调用为批量命令")
        self.buttons.button(QDialogButtonBox.Cancel).setText("取消")
        self.buttons.accepted.connect(self._accept_template)
        self.buttons.rejected.connect(self.reject)
        button_row.addWidget(self.buttons)
        layout.addLayout(button_row)

    def values(self) -> dict:
        return {name: editor.text() for name, editor in self.inputs.items()}

    def _refresh_preview(self):
        try:
            rendered = render_template(self.template, self.values())
        except TemplateValidationError as exc:
            self.rendered_template = None
            self.preview.clear()
            self.validation_label.setText(str(exc))
            self.validation_label.setStyleSheet("color:#C43D32;")
            self.copy_button.setEnabled(False)
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return
        self.rendered_template = rendered
        self.preview.setPlainText(rendered.preview)
        self.validation_label.setText(
            f"参数校验通过，共 {len(rendered.commands)} 条可执行命令。"
        )
        self.validation_label.setStyleSheet("color:#087F5B;")
        self.copy_button.setEnabled(True)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def _manual_steps_from_defaults(self):
        try:
            rendered = render_template(self.template, self.values())
        except TemplateValidationError:
            path = self.template.get("path", "")
            try:
                lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
            except OSError:
                return ()
            return tuple(
                line.partition(":")[2].strip()
                for line in lines
                if line.strip().startswith("# MANUAL:")
            )
        return rendered.manual_steps

    def _copy_commands(self):
        if not self.rendered_template:
            return
        text = "\n".join(self.rendered_template.commands)
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        if self.rendered_template.contains_secrets:
            self.validation_label.setText(
                "命令已复制；其中包含密码，60 秒后将自动清理本程序写入的剪贴板内容。"
            )

            def clear_secret():
                if clipboard.text() == text:
                    clipboard.clear()

            QTimer.singleShot(60_000, clear_secret)
        else:
            self.validation_label.setText("命令已复制到剪贴板。")

    def _accept_template(self):
        self._refresh_preview()
        if not self.rendered_template:
            return
        if self.rendered_template.manual_steps:
            detail = "\n".join(
                f"• {step}" for step in self.rendered_template.manual_steps
            )
            answer = QMessageBox.question(
                self,
                "确认手动前置步骤",
                "该模板存在不能安全自动执行的前置步骤：\n\n"
                f"{detail}\n\n确认已经完成，再调用批量命令？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self.accept()
