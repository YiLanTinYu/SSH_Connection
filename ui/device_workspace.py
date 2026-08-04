"""Right-side device list and connection log workspace."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.theme import Theme


class DeviceWorkspace(QWidget):
    """Own the device table, filtering controls, and live log widgets."""

    search_changed = pyqtSignal()
    group_filter_changed = pyqtSignal()
    execution_scope_changed = pyqtSignal()
    selection_changed = pyqtSignal()
    view_logs_requested = pyqtSignal()
    clear_log_requested = pyqtSignal()
    result_center_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("right_workspace")
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        list_group = QGroupBox("设备列表")
        list_group.setObjectName("device_list_group")
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(10, 18, 10, 10)
        list_layout.setSpacing(8)

        filter_row = QHBoxLayout()
        self.device_search_input = QLineEdit()
        self.device_search_input.setPlaceholderText("搜索名称、IP、品牌或标签")
        self.device_search_input.setClearButtonEnabled(True)

        self.group_filter_combo = QComboBox()
        self.group_filter_combo.setMinimumWidth(130)
        self.group_filter_combo.addItem("全部分组", "")

        self.execution_scope_combo = QComboBox()
        self.execution_scope_combo.setMinimumWidth(160)
        self.execution_scope_combo.addItem("目标：全部设备", "all")
        self.execution_scope_combo.addItem("目标：筛选结果", "filtered")
        self.execution_scope_combo.addItem("目标：选中设备", "selected")

        filter_row.addWidget(self.device_search_input, 1)
        filter_row.addWidget(self.group_filter_combo)
        filter_row.addWidget(self.execution_scope_combo)
        list_layout.addLayout(filter_row)

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(10)
        self.device_table.setHorizontalHeaderLabels(
            [
                "设备名称",
                "分组",
                "标签",
                "品牌",
                "型号",
                "IP 地址",
                "IP 版本",
                "端口",
                "用户名",
                "状态",
            ]
        )
        self.device_table.setAlternatingRowColors(True)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_header = self.device_table.horizontalHeader()
        table_header.setSectionResizeMode(QHeaderView.Interactive)
        table_header.setMinimumSectionSize(64)
        table_header.setStretchLastSection(True)
        for column, width in enumerate(
            (130, 100, 120, 82, 180, 180, 90, 68, 110, 116)
        ):
            table_header.resizeSection(column, width)
        self.device_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.device_table.verticalHeader().setDefaultSectionSize(38)
        self.device_table.setShowGrid(False)
        list_layout.addWidget(self.device_table)
        layout.addWidget(list_group, stretch=5)

        log_group = QGroupBox("连接日志")
        log_group.setObjectName("connection_log_group")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 18, 10, 10)
        log_layout.setSpacing(7)

        log_toolbar = QHBoxLayout()
        self._log_title_label = QLabel("实时输出")
        self._log_title_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: 15px; "
            "background: transparent;"
        )
        log_toolbar.addWidget(self._log_title_label)
        log_toolbar.addStretch()

        self.log_btn = QPushButton("日志")
        self.log_btn.setObjectName("btn_neutral")
        self.log_btn.setToolTip("打开日志目录")
        self.clear_log_btn = QPushButton("清空")
        self.clear_log_btn.setObjectName("btn_outline")
        self.clear_log_btn.setToolTip("清空当前连接日志")
        self.result_center_btn = QPushButton("结果中心")
        self.result_center_btn.setObjectName("btn_outline")
        self.result_center_btn.setToolTip(
            "按设备查看完整命令输出、耗时与错误，并导出结果"
        )
        log_toolbar.addWidget(self.log_btn)
        log_toolbar.addWidget(self.clear_log_btn)
        log_toolbar.addWidget(self.result_center_btn)
        log_layout.addLayout(log_toolbar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 16))
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group, stretch=3)

    def _connect_signals(self) -> None:
        self.device_search_input.textChanged.connect(
            lambda _text: self.search_changed.emit()
        )
        self.group_filter_combo.currentIndexChanged.connect(
            lambda _index: self.group_filter_changed.emit()
        )
        self.execution_scope_combo.currentIndexChanged.connect(
            lambda _index: self.execution_scope_changed.emit()
        )
        self.device_table.itemSelectionChanged.connect(self.selection_changed.emit)
        self.log_btn.clicked.connect(self.view_logs_requested.emit)
        self.clear_log_btn.clicked.connect(self.clear_log_requested.emit)
        self.result_center_btn.clicked.connect(self.result_center_requested.emit)
