"""Device list destructive action controls."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QGroupBox, QHBoxLayout, QPushButton


class DeviceListActionsPanel(QGroupBox):
    remove_selected_requested = pyqtSignal()
    clear_all_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("列表管理", parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(8)

        self.delete_btn = QPushButton("移除选中")
        self.delete_btn.setObjectName("btn_neutral")
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.setObjectName("btn_danger")
        layout.addWidget(self.delete_btn)
        layout.addWidget(self.clear_btn)

        self.delete_btn.clicked.connect(self.remove_selected_requested.emit)
        self.clear_btn.clicked.connect(self.clear_all_requested.emit)
