"""Compose the main-window shell from existing reusable UI panels."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.aurora_header import AuroraHeader
from ui.collapsible_sidebar import CollapsibleSidebar, _render_svg_icon
from ui.device_workspace import DeviceWorkspace
from ui.icon_factory import build_app_icon
from ui.splitter import ModernSplitter
from ui.theme import Theme


class MainWindowLayoutBuilder:
    def __init__(self, window, app_name="AOMT"):
        self.window = window
        self.app_name = app_name

    def build(self):
        window = self.window
        central = QWidget()
        central.setObjectName("app_root")
        window.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.build_header())

        body = QWidget()
        body.setObjectName("workspace_body")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(12)

        splitter = ModernSplitter(Qt.Horizontal)
        splitter.setHandleWidth(10)
        splitter.setChildrenCollapsible(False)
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([CollapsibleSidebar.COLLAPSED_WIDTH, 1132])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        window._main_splitter = splitter
        window._left_panel = left_panel
        left_panel.expansionChanged.connect(
            window._on_left_sidebar_expansion_changed
        )
        splitter.splitterMoved.connect(
            lambda *_: window._update_ops_tools_columns()
        )
        window._update_left_panel_limit()

        body_layout.addWidget(splitter)
        root_layout.addWidget(body)
        self.decorate_action_buttons()

    def build_header(self) -> QWidget:
        window = self.window
        header = AuroraHeader()
        header.setFixedHeight(74)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        icon_label.setPixmap(
            build_app_icon().pixmap(46, 46, QIcon.Normal, QIcon.On)
        )
        layout.addWidget(icon_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFixedHeight(36)
        separator.setStyleSheet(
            "color: rgba(221,247,244,0.26); background: transparent;"
        )
        layout.addWidget(separator)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        window._title_lbl = QLabel(self.app_name)
        window._title_lbl.setStyleSheet(
            f"color: {Theme.TEXT_WHITE}; font-size: 21px; font-weight: 700; "
            "letter-spacing: 0px; background: transparent;"
        )
        window._subtitle_lbl = QLabel("NETWORK OPERATIONS CONSOLE")
        window._subtitle_lbl.setStyleSheet(
            "color: rgba(221,247,244,0.66); font-size: 12px; "
            "background: transparent;"
        )
        title_layout.addWidget(window._title_lbl)
        title_layout.addWidget(window._subtitle_lbl)
        layout.addLayout(title_layout)
        layout.addStretch()
        return header

    def create_left_panel(self) -> QWidget:
        window = self.window
        sidebar = CollapsibleSidebar(self.sidebar_icon_directory())
        pages = (
            (
                "devices",
                "设备库",
                "devices.svg",
                (
                    window._build_input_group(),
                    window._build_excel_group(),
                    window._build_device_list_actions_group(),
                ),
            ),
            (
                "tasks",
                "设备作业",
                "terminal-window.svg",
                (
                    window._build_task_target_group(),
                    window._build_command_group(),
                    window._build_execution_group(),
                    window._build_device_tools_group(),
                ),
            ),
            (
                "tools",
                "本机工具",
                "toolbox.svg",
                (window._build_local_tools_group(),),
            ),
            (
                "templates",
                "模板中心",
                "files.svg",
                (window._build_config_templates_group(),),
            ),
        )
        for key, title, icon_filename, groups in pages:
            sidebar.add_page(
                key,
                title,
                icon_filename,
                self.build_sidebar_page(groups),
            )
        window._left_content = sidebar
        return sidebar

    @staticmethod
    def sidebar_icon_directory() -> Path:
        return MainWindowLayoutBuilder._icon_directory("phosphor")

    @staticmethod
    def lucide_icon_directory() -> Path:
        return MainWindowLayoutBuilder._icon_directory("lucide")

    @staticmethod
    def _icon_directory(family: str) -> Path:
        relative = Path("assets") / "icons" / family
        candidates = [
            Path(__file__).resolve().parent.parent / relative,
            Path(sys.executable).resolve().parent / relative,
            Path.cwd() / relative,
        ]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0]

    def decorate_action_buttons(self):
        window = self.window
        actions = (
            (window.add_btn, "plus", "添加设备"),
            (window.import_btn, "folder-open", "导入 Excel 文件"),
            (window.encrypt_excel_btn, "lock-keyhole", "加密 Excel 认证信息"),
            (window.template_btn, "download", "下载 Excel 模板"),
            (window.cmd_browse_btn, "file-text", "选择文件"),
            (window.cmd_reset_btn, "rotate-ccw", "恢复默认"),
            (window.manage_task_targets_btn, "plus", "补充临时目标"),
            (window.clear_task_targets_btn, "rotate-ccw", "使用设备范围"),
            (window.delete_btn, "circle-minus", "移除选中"),
            (window.clear_btn, "trash-2", "清空列表"),
            (window.connect_btn, "play", "开始执行"),
            (window.ssh_console_btn, "terminal", "SSH 交互终端"),
            (window.ping_excel_btn, "radio", "批量 Ping"),
            (window.port_check_btn, "plug-zap", "端口检测"),
            (window.ssh_test_btn, "key-round", "SSH 登录测试"),
            (window.traceroute_btn, "route", "路由跟踪"),
            (window.config_backup_btn, "database-backup", "配置备份"),
            (window.health_check_btn, "clipboard-check", "一键设备巡检"),
            (window.terminal_locate_btn, "locate-fixed", "IP/MAC 终端定位"),
            (window.interface_diag_btn, "activity", "接口综合诊断"),
            (window.serial_console_btn, "cable", "串口控制台"),
            (window.file_transfer_btn, "arrow-left-right", "文件传输服务"),
            (window.packet_capture_btn, "scan-line", "网络抓包"),
            (window.subnet_calc_btn, "network", "子网计算"),
            (window.config_diff_btn, "arrow-left-right", "配置对比"),
            (window.use_template_btn, "play", "调用选中模板"),
            (window.add_template_btn, "plus", "添加模板"),
            (window.remove_template_btn, "circle-minus", "移除选中"),
            (window.log_btn, "folder-open", "日志"),
            (window.clear_log_btn, "eraser", "清空"),
            (window.result_center_btn, "list-checks", "结果中心"),
        )
        tool_buttons = set(window._device_tool_buttons + window._local_tool_buttons)
        toolbar_buttons = {
            window.log_btn,
            window.clear_log_btn,
            window.result_center_btn,
        }
        icon_directory = self.lucide_icon_directory()
        for button, icon_name, label in actions:
            if button in tool_buttons:
                button.setObjectName("tool_button")
            elif button in toolbar_buttons:
                button.setObjectName("toolbar_button")
            button.setText(label)
            button.setCursor(Qt.PointingHandCursor)
            icon_path = icon_directory / f"{icon_name}.svg"
            if not icon_path.is_file():
                continue
            foreground = (
                Theme.TEXT_WHITE
                if button.objectName()
                in {"btn_primary", "btn_success", "btn_neutral"}
                else Theme.ERROR
                if button.objectName() == "btn_danger"
                else Theme.PRIMARY_DARK
            )
            icon = QIcon()
            icon.addPixmap(
                _render_svg_icon(icon_path, foreground, 19),
                QIcon.Normal,
                QIcon.Off,
            )
            icon.addPixmap(
                _render_svg_icon(icon_path, "#8AA0A4", 19),
                QIcon.Disabled,
                QIcon.Off,
            )
            button.setIcon(icon)
            button.setIconSize(QSize(18, 18))

        for button in window.findChildren(QPushButton):
            button.setCursor(Qt.PointingHandCursor)

    @staticmethod
    def build_sidebar_page(groups) -> QWidget:
        page = QWidget()
        page.setObjectName("sidebar_page")
        page.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(10)
        for group in groups:
            group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            layout.addWidget(group, 0)
        layout.addStretch()
        return page

    def create_right_panel(self) -> QWidget:
        window = self.window
        workspace = DeviceWorkspace()
        window._device_workspace = workspace
        for name in (
            "device_search_input",
            "group_filter_combo",
            "execution_scope_combo",
            "device_table",
            "_log_title_label",
            "log_btn",
            "clear_log_btn",
            "result_center_btn",
            "log_text",
        ):
            setattr(window, name, getattr(workspace, name))

        workspace.search_changed.connect(window.apply_device_filters)
        workspace.group_filter_changed.connect(window.apply_device_filters)
        workspace.execution_scope_changed.connect(
            window._on_execution_scope_changed
        )
        workspace.selection_changed.connect(window._update_task_target_summary)
        workspace.view_logs_requested.connect(window.view_logs)
        workspace.clear_log_requested.connect(window.clear_connection_log)
        workspace.result_center_requested.connect(window.open_result_center)
        return workspace
