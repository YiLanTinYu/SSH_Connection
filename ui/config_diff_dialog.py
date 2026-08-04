"""Configuration diff viewer and exporter."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from utils.maintenance_tools import write_lines


class ConfigDiffDialog(QDialog):
    diff_saved = pyqtSignal(str)

    def __init__(self, first_path: str, second_path: str, diff_text: str, parent=None):
        super().__init__(parent)
        self.first_path = first_path
        self.second_path = second_path
        self.diff_text = diff_text
        self.setWindowTitle("配置文件对比")
        self.resize(1100, 760)

        layout = QVBoxLayout(self)
        self.title_label = QLabel(
            f"第一份：{first_path}\n第二份：{second_path}\n"
            "“-”表示第一份独有，“+”表示第二份新增。"
        )
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setFont(QFont("Consolas", 13))
        self.viewer.setPlainText(diff_text)
        layout.addWidget(self.viewer)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.save_button = QPushButton("保存差异")
        self.save_button.setObjectName("btn_outline")
        self.close_button = QPushButton("关闭")
        self.close_button.setObjectName("btn_neutral")
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self.save_button.clicked.connect(self.save_diff)
        self.close_button.clicked.connect(self.accept)

    def save_diff(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存配置差异",
            "config_diff.txt",
            "文本文件 (*.txt)",
        )
        if not path:
            return
        try:
            write_lines(path, self.diff_text.splitlines())
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.diff_saved.emit(path)
