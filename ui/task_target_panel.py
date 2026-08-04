"""Task target scope controls used by the main device workspace."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui.theme import Theme


class TaskTargetPanel(QGroupBox):
    """Present task scope and temporary target management actions."""

    scope_changed = pyqtSignal()
    manage_targets_requested = pyqtSignal()
    clear_targets_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("目标设备", parent)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.task_scope_combo = QComboBox()
        self.task_scope_combo.addItem("全部设备", "all")
        self.task_scope_combo.addItem("当前筛选结果", "filtered")
        self.task_scope_combo.addItem("设备表选中行", "selected")
        layout.addWidget(self.task_scope_combo)

        self.task_target_summary = QLabel("当前设备列表为空")
        self.task_target_summary.setWordWrap(True)
        self.task_target_summary.setObjectName("task_target_summary")
        self.task_target_summary.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; background: {Theme.BG_CARD}; "
            f"border: 1px solid {Theme.BORDER}; border-radius: 4px; "
            "padding: 7px 8px;"
        )
        layout.addWidget(self.task_target_summary)

        button_row = QHBoxLayout()
        self.manage_task_targets_btn = QPushButton("补充临时目标")
        self.manage_task_targets_btn.setObjectName("btn_outline")
        self.manage_task_targets_btn.setToolTip(
            "补充仅在当前程序运行期间有效的 IP、SSH 或 Ping 网段目标"
        )
        self.clear_task_targets_btn = QPushButton("使用设备范围")
        self.clear_task_targets_btn.setObjectName("btn_neutral")
        self.clear_task_targets_btn.setEnabled(False)
        button_row.addWidget(self.manage_task_targets_btn)
        button_row.addWidget(self.clear_task_targets_btn)
        layout.addLayout(button_row)

        self.hint_label = QLabel(
            "批量命令、连接检测、巡检、诊断和备份共享此目标范围。"
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(
            f"color: {Theme.TEXT_HINT}; background: transparent;"
        )
        layout.addWidget(self.hint_label)

    def _connect_signals(self) -> None:
        self.task_scope_combo.currentIndexChanged.connect(
            lambda _index: self.scope_changed.emit()
        )
        self.manage_task_targets_btn.clicked.connect(
            self.manage_targets_requested.emit
        )
        self.clear_task_targets_btn.clicked.connect(
            self.clear_targets_requested.emit
        )
