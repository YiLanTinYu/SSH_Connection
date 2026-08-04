"""Batch execution options and primary action panel."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QPushButton, QVBoxLayout

from ui.theme import Theme


class BatchExecutionPanel(QGroupBox):
    """Present batch execution options without owning execution logic."""

    start_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("批量执行", parent)
        self._build_ui()
        self.connect_btn.clicked.connect(self.start_requested.emit)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        save_row = QHBoxLayout()
        self.save_check = QCheckBox("执行后保存配置")
        self.save_check.setToolTip(
            "连接成功并执行命令后自动发送设备保存配置命令"
        )
        self.save_check.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: 12px;"
        )
        save_row.addWidget(self.save_check)
        save_row.addStretch()
        layout.addLayout(save_row)

        uplink_row = QHBoxLayout()
        self.l2_uplink_check = QCheckBox("探测二层上联口")
        self.l2_uplink_check.setToolTip(
            "通过 路由表→ARP→MAC表 三步查询探测上联端口"
            "（移植自 w-sw-ssh --l2_sw）"
        )
        self.l2_uplink_check.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: 12px;"
        )
        uplink_row.addWidget(self.l2_uplink_check)
        uplink_row.addStretch()
        layout.addLayout(uplink_row)

        self.connect_btn = QPushButton("开始执行")
        self.connect_btn.setObjectName("btn_success")
        layout.addWidget(self.connect_btn)
