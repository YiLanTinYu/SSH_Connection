"""Command source selection panel for batch execution."""

from typing import Callable, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from ui.theme import Theme


class CommandFilePanel(QGroupBox):
    """Present command mode, source path, and source actions."""

    mode_changed = pyqtSignal()
    browse_requested = pyqtSignal()
    reset_requested = pyqtSignal()

    def __init__(
        self,
        form_label_factory: Optional[Callable[[str], QLabel]] = None,
        parent=None,
    ):
        super().__init__("业务命令文件", parent)
        self._form_label_factory = form_label_factory or self._default_form_label
        self._build_ui()
        self._connect_signals()

    @staticmethod
    def _default_form_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("field_label")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return label

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        mode_row = QGridLayout()
        mode_row.setColumnStretch(1, 1)
        mode_row.addWidget(self._form_label_factory("模式:"), 0, 0)
        self.cmd_mode_combo = QComboBox()
        self.cmd_mode_combo.addItem("统一脚本", "single")
        self.cmd_mode_combo.addItem("按设备匹配", "per_device")
        mode_row.addWidget(self.cmd_mode_combo, 0, 1)
        layout.addLayout(mode_row)

        path_row = QGridLayout()
        path_row.setHorizontalSpacing(8)
        path_row.setVerticalSpacing(8)
        path_row.setColumnStretch(0, 0)
        path_row.setColumnStretch(1, 1)
        path_row.addWidget(self._form_label_factory("文件:"), 0, 0)
        self.cmd_file_label = QLabel("SSH_command.txt  (默认)")
        self.cmd_file_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )
        self.cmd_file_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: 12px; "
            f"background: {Theme.BG_CARD}; border: 1px solid {Theme.BORDER}; "
            "border-radius: 4px; padding: 4px 6px;"
        )
        self.cmd_file_label.setWordWrap(True)
        path_row.addWidget(self.cmd_file_label, 0, 1)
        layout.addLayout(path_row)

        button_row = QHBoxLayout()
        self.cmd_browse_btn = QPushButton("选择文件")
        self.cmd_browse_btn.setObjectName("btn_outline")
        self.cmd_reset_btn = QPushButton("恢复默认")
        self.cmd_reset_btn.setObjectName("btn_neutral")
        button_row.addWidget(self.cmd_browse_btn)
        button_row.addWidget(self.cmd_reset_btn)
        layout.addLayout(button_row)

        self._cmd_tip_label = QLabel("命令原样发送；每行一条，# 开头为注释")
        self._cmd_tip_label.setStyleSheet(
            f"color: {Theme.TEXT_HINT}; font-size: 16px;"
        )
        layout.addWidget(self._cmd_tip_label)

    def _connect_signals(self) -> None:
        self.cmd_mode_combo.currentIndexChanged.connect(
            lambda _index: self.mode_changed.emit()
        )
        self.cmd_browse_btn.clicked.connect(self.browse_requested.emit)
        self.cmd_reset_btn.clicked.connect(self.reset_requested.emit)
