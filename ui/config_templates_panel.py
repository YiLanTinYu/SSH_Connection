"""Common configuration template list panel."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)


class ConfigTemplatesPanel(QGroupBox):
    open_requested = pyqtSignal(object)
    use_requested = pyqtSignal()
    add_requested = pyqtSignal()
    remove_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("常用配置模板", parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.config_template_list = QListWidget()
        self.config_template_list.setMinimumHeight(118)
        self.config_template_list.setMaximumHeight(180)
        self.config_template_list.setAlternatingRowColors(True)
        layout.addWidget(self.config_template_list)

        self.use_template_btn = QPushButton("调用选中模板")
        self.use_template_btn.setObjectName("btn_primary")
        self.use_template_btn.setToolTip("将选中模板设为当前统一业务命令文件")
        layout.addWidget(self.use_template_btn)

        button_row = QHBoxLayout()
        self.add_template_btn = QPushButton("添加模板")
        self.add_template_btn.setObjectName("btn_outline")
        self.add_template_btn.setToolTip("批量添加自己的配置模板")
        self.remove_template_btn = QPushButton("移除选中")
        self.remove_template_btn.setObjectName("btn_neutral")
        self.remove_template_btn.setToolTip("仅自定义模板可以从列表中移除")
        button_row.addWidget(self.add_template_btn)
        button_row.addWidget(self.remove_template_btn)
        layout.addLayout(button_row)

        self.config_template_list.itemDoubleClicked.connect(
            self.open_requested.emit
        )
        self.use_template_btn.clicked.connect(self.use_requested.emit)
        self.add_template_btn.clicked.connect(self.add_requested.emit)
        self.remove_template_btn.clicked.connect(self.remove_requested.emit)
