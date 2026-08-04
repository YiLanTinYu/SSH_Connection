"""Excel device import actions."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QGroupBox, QPushButton, QVBoxLayout


class ExcelImportPanel(QGroupBox):
    import_requested = pyqtSignal()
    encrypt_requested = pyqtSignal()
    template_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("批量导入", parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.import_btn = self._add_button(layout, "导入 Excel 文件")
        self.encrypt_excel_btn = self._add_button(layout, "加密 Excel 认证信息")
        self.template_btn = self._add_button(layout, "下载 Excel 模板")

        self.import_btn.clicked.connect(self.import_requested.emit)
        self.encrypt_excel_btn.clicked.connect(self.encrypt_requested.emit)
        self.template_btn.clicked.connect(self.template_requested.emit)

    @staticmethod
    def _add_button(layout: QVBoxLayout, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("btn_outline")
        layout.addWidget(button)
        return button
