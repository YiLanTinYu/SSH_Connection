#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
主窗口UI
使用PyQt5实现交换机SSH管理界面
支持IPv4和IPv6地址 - 现代化UI版本
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QGridLayout,
                             QLabel, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QTextEdit, QFileDialog,
                             QMessageBox, QGroupBox, QSpinBox, QComboBox,
                             QHeaderView,
                             QAbstractItemView, QApplication, QCheckBox,
                             QScrollArea, QListWidget, QListWidgetItem,
                             QDialog, QDialogButtonBox, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QFont, QFontMetrics, QColor, QDesktopServices
from typing import List, Dict
from datetime import datetime
from pathlib import Path
import os
import sys
import re

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.device_config import DeviceConfigManager
from config.device_commands import CommandModule
from config.app_info import APP_AUTHOR, APP_NAME, APP_SHORT_NAME, APP_VERSION
from core.ssh_manager_simple import SSHManager
from ui.collapsible_sidebar import CollapsibleSidebar
from ui.result_dialog import ResultCenterDialog
from ui.maintenance_target_dialog import MaintenanceTargetDialog
from ui.serial_console import SerialConsoleDialog
from ui.ssh_console import SSHConsoleDialog
from ui.file_transfer_dialog import FileTransferDialog
from ui.packet_capture_dialog import PacketCaptureDialog
from ui.config_template_dialog import ConfigTemplateDialog
from ui.execution_preview_dialog import (
    ExecutionPreviewDialog,
    build_execution_preview,
)
from ui.task_history_dialog import TaskHistoryDialog
from ui.device_diagnostics_worker import DeviceDiagnosticsWorker
from ui.health_profile_dialog import HealthProfileDialog
from ui.theme import APP_STYLE, Theme
from ui.status_badge import StatusBadge
from ui.connection_worker import ConnectionWorker
from ui.ping_worker import PingWorker
from ui.maintenance_worker import MaintenanceWorker
from ui.icon_factory import build_app_icon
from ui.dialog_helpers import confirm_action, prompt_secret, show_input_warning
from ui.device_table_presenter import DeviceTablePresenter
from ui.task_target_panel import TaskTargetPanel
from ui.command_file_panel import CommandFilePanel
from ui.batch_execution_panel import BatchExecutionPanel
from ui.device_tools_panel import DeviceToolsPanel
from ui.local_tools_panel import LocalToolsPanel
from ui.device_form_panel import DeviceFormPanel
from ui.excel_import_panel import ExcelImportPanel
from ui.device_list_actions_panel import DeviceListActionsPanel
from ui.config_templates_panel import ConfigTemplatesPanel
from ui.config_diff_dialog import ConfigDiffDialog
from ui.subnet_calculator_dialog import SubnetCalculatorDialog
from ui.main_menu import build_main_menu, menu_action_routes
from ui.main_window_status import MainWindowStatusController
from ui.main_window_layout import MainWindowLayoutBuilder
from ui.responsive_layout import (
    calculate_font_size,
    expanded_sidebar_width,
    maximum_sidebar_width,
    operations_tool_columns,
)
from utils.logger import ConnectionLogger
from utils.ipv6_utils import IPv6Utils
from utils.maintenance_tools import (
    parse_tcp_ports,
    unified_config_diff,
)
from utils.device_diagnostics import (
    normalize_lookup_target,
    validate_interface_name,
)
from utils.task_audit import TaskAuditStore, preview_fingerprint
from services.device_management import (
    DeviceFormError,
    DeviceFormValues,
)
from services.maintenance_tasks import (
    diagnostic_result_counts,
    diagnostic_task_definition,
    maintenance_task_definition,
    save_maintenance_log,
)
from services.batch_execution import (
    BatchCommandSettings,
    command_source_label,
    configure_ssh_manager,
    devices_with_brand_mismatch,
    execution_device_keys,
)
from services.execution_results import (
    execution_audit_status,
    result_status_text,
    summarize_connections,
    upsert_execution_result,
)
from services.log_formatting import (
    current_timestamp,
    format_info_html,
    format_log_html,
)
from controllers.maintenance_controller import MaintenanceController
from controllers.device_inventory_controller import DeviceInventoryController
from controllers.config_template_controller import ConfigTemplateController
from controllers.batch_execution_controller import BatchExecutionController
from controllers.tool_window_controller import ToolWindowController
from controllers.main_window_action_controller import MainWindowActionController










# ─────────────────────── 状态标签组件 ───────────────────────


# ─────────────────────── 工作线程 ───────────────────────






# ─────────────────────── 主窗口 ───────────────────────
class MainWindow(QMainWindow):
    """主窗口 - 现代化 UI"""

    # 字体缩放锚点：(窗口宽度, pt字号)
    _FONT_ANCHORS = [(1024, 13), (1280, 14), (1600, 16), (1920, 17)]

    MENU_DEFINITIONS = (
        (
            "file",
            "文件(&F)",
            (
                ("file.import_excel", "导入 Excel 文件...", "import_excel"),
                (
                    "file.encrypt_excel",
                    "加密 Excel 认证信息...",
                    "encrypt_excel_passwords",
                ),
                (
                    "file.download_template",
                    "下载 Excel 模板...",
                    "download_template",
                ),
                None,
                ("file.exit", "退出", "_close_application"),
            ),
        ),
        (
            "device",
            "设备(&D)",
            (
                ("device.add", "添加设备...", "show_add_device_form"),
                None,
                (
                    "device.ssh_terminal",
                    "SSH 交互终端",
                    "show_ssh_console",
                ),
                (
                    "device.serial_console",
                    "串口控制台",
                    "show_serial_console",
                ),
                None,
                (
                    "device.remove_selected",
                    "移除选中设备...",
                    "delete_selected_device",
                ),
                (
                    "device.clear",
                    "清空设备列表...",
                    "clear_devices",
                ),
            ),
        ),
        (
            "task",
            "任务(&T)",
            (
                (
                    "task.select_script",
                    "选择业务命令文件...",
                    "browse_command_file",
                ),
                (
                    "task.default_script",
                    "恢复默认业务命令",
                    "reset_command_file",
                ),
                None,
                (
                    "task.start_execution",
                    "开始批量执行",
                    "start_connection",
                ),
                (
                    "task.health_check",
                    "一键设备巡检",
                    "start_health_check",
                ),
                (
                    "task.config_backup",
                    "配置备份",
                    "start_config_backup",
                ),
                None,
                (
                    "task.results",
                    "执行结果中心",
                    "open_result_center",
                ),
                (
                    "task.history",
                    "批量执行历史",
                    "show_task_history",
                ),
            ),
        ),
        (
            "tools",
            "工具(&L)",
            (
                (
                    "tools.file_transfer",
                    "文件传输服务",
                    "show_file_transfer",
                ),
                (
                    "tools.packet_capture",
                    "网络抓包",
                    "show_packet_capture",
                ),
                None,
                ("tools.ping", "批量 Ping", "batch_ping_devices"),
                ("tools.port_check", "端口检测", "start_port_check"),
                (
                    "tools.ssh_login",
                    "SSH 登录测试",
                    "start_ssh_login_test",
                ),
                (
                    "tools.traceroute",
                    "路由跟踪",
                    "start_traceroute",
                ),
                (
                    "tools.terminal_locate",
                    "IP/MAC 终端定位",
                    "start_terminal_locate",
                ),
                (
                    "tools.interface_diagnosis",
                    "接口综合诊断",
                    "start_interface_diagnosis",
                ),
                None,
                (
                    "tools.subnet_calculator",
                    "IPv4 / IPv6 子网计算器",
                    "show_subnet_calculator",
                ),
                (
                    "tools.config_diff",
                    "配置文件对比",
                    "show_config_diff",
                ),
            ),
        ),
        (
            "view",
            "视图(&V)",
            (
                (
                    "view.devices",
                    "设备库",
                    "show_device_library_page",
                ),
                (
                    "view.tasks",
                    "设备作业",
                    "show_device_tasks_page",
                ),
                (
                    "view.tools",
                    "本机工具",
                    "show_local_tools_page",
                ),
                (
                    "view.templates",
                    "模板中心",
                    "show_template_center_page",
                ),
                None,
                (
                    "view.toggle_sidebar",
                    "展开 / 收起侧栏",
                    "toggle_navigation_sidebar",
                ),
                (
                    "view.restore_layout",
                    "恢复默认布局",
                    "restore_default_layout",
                ),
                None,
                ("view.logs", "查看日志信息...", "view_logs"),
                (
                    "view.clear_log",
                    "清空实时日志...",
                    "clear_connection_log",
                ),
            ),
        ),
        (
            "help",
            "帮助(&H)",
            (
                ("help.guide", "使用说明", "open_user_guide"),
                ("help.about", "关于 AOMT", "show_about_dialog"),
            ),
        ),
    )

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_SHORT_NAME)
        self.setMinimumSize(1024, 768)
        self.resize(2560, 1600)
        self.setWindowIcon(build_app_icon())

        # 初始化管理器
        self.device_manager    = DeviceConfigManager()
        self._device_inventory_controller = DeviceInventoryController(
            self.device_manager
        )
        self.logger            = ConnectionLogger()
        self._batch_execution_controller = BatchExecutionController(
            logger=self.logger
        )
        self.ssh_manager       = self._batch_execution_controller.manager
        self._maintenance_controller = MaintenanceController(self.logger)
        self.command_module    = CommandModule()
        self.connection_worker = None
        self.ping_worker       = None
        self.maintenance_worker = None
        self.diagnostics_worker = None
        self._connected_count  = 0
        self._total_count      = 0
        self._ping_log_lines   = []
        self._maintenance_log_lines = []
        self._command_file     = None   # None = 使用默认 SSH_command.txt
        self._command_directory = None
        self._command_lines = None
        self._required_template_brand = ""
        self._active_template_name = ""
        self._active_template_sensitive = False
        self._template_secret_values = []
        self._custom_task_targets = []
        self._current_font_pt  = 14     # 当前字号，防止重复刷新
        self._form_labels      = []
        self._template_store_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "operation_templates.json",
        )
        self._config_template_controller = ConfigTemplateController(
            self._template_store_path
        )
        self._config_templates = []
        self.execution_results = []
        self._serial_console = None
        self._ssh_console = None
        self._file_transfer_dialog = None
        self._packet_capture_dialog = None
        self._tool_window_controller = ToolWindowController(self)
        self._main_action_controller = MainWindowActionController(
            self,
            APP_NAME,
            APP_VERSION,
            APP_AUTHOR,
            QDesktopServices,
            QUrl,
        )
        self._layout_builder = MainWindowLayoutBuilder(self, APP_NAME)
        self._task_audit_store = None
        self._active_batch_audit_id = None

        # 应用样式
        self.setStyleSheet(APP_STYLE)

        self.init_ui()
        self._batch_execution_controller.progress.connect(self.update_progress)
        self._batch_execution_controller.device_status.connect(
            self.on_device_status
        )
        self._batch_execution_controller.result.connect(self.handle_result)
        self._batch_execution_controller.finished.connect(
            self.connection_finished
        )
        self._maintenance_controller.ping_progress.connect(
            self._record_ping_log
        )
        self._maintenance_controller.ping_finished.connect(
            self.batch_ping_finished
        )
        self._maintenance_controller.maintenance_progress.connect(
            self._record_maintenance_log
        )
        self._maintenance_controller.maintenance_finished.connect(
            self._maintenance_task_finished
        )
        self._maintenance_controller.diagnostics_progress.connect(
            self._record_maintenance_log
        )
        self._maintenance_controller.diagnostics_finished.connect(
            self._diagnostics_task_finished
        )
        self._device_table_presenter = DeviceTablePresenter(
            self.device_table,
            self.device_search_input,
            self.group_filter_combo,
        )
        self._init_main_menu()
        self._init_statusbar()
        self._load_config_templates()
        self._apply_font_pt(self._calc_font_pt(self.width()))

    @classmethod
    def menu_action_routes(cls) -> Dict[str, str]:
        return menu_action_routes(cls.MENU_DEFINITIONS)

    def _init_main_menu(self):
        self.main_menus, self.menu_actions = build_main_menu(
            self,
            self.MENU_DEFINITIONS,
            self._dispatch_menu_action,
        )

    def _dispatch_menu_action(self, handler_name: str):
        handler = getattr(self, handler_name)
        handler()

    # ── 动态字体缩放 ────────────────────────────────────
    @staticmethod
    def _calc_font_pt(width: int) -> int:
        """根据窗口宽度线性插值计算字号（pt）"""
        return calculate_font_size(width, MainWindow._FONT_ANCHORS)

    def _apply_font_pt(self, pt: int):
        """Apply one responsive typography scale based on semantic UI roles."""
        body_px = max(15, min(17, pt))
        small_px = max(13, body_px - 2)
        group_title_px = body_px + 1
        section_title_px = body_px + 2
        page_title_px = body_px + 5
        header_title_px = body_px + 12
        header_subtitle_px = max(13, body_px - 3)
        log_px = 21  # The connection log remains 16 pt equivalent.

        def replace_size(style, selector_pattern, pixel_size):
            return re.sub(
                rf'({selector_pattern}\s*\{{[^}}]*font-size:\s*)\d+px',
                lambda match: match.group(1) + f'{pixel_size}px',
                style,
            )

        new_style = APP_STYLE
        new_style = replace_size(new_style, r'QMainWindow, QWidget', body_px)
        new_style = replace_size(new_style, r'QToolTip', small_px)
        new_style = replace_size(new_style, r'QGroupBox', body_px)
        new_style = replace_size(new_style, r'QGroupBox::title', group_title_px)
        new_style = replace_size(new_style, r'QLineEdit, QSpinBox, QComboBox', body_px)
        new_style = replace_size(new_style, r'QPushButton', body_px)
        new_style = replace_size(new_style, r'QPushButton#btn_success', body_px)
        new_style = replace_size(new_style, r'QTableWidget', body_px)
        new_style = replace_size(new_style, r'QHeaderView::section', group_title_px)
        new_style = replace_size(new_style, r'QTextEdit', log_px)
        new_style = replace_size(new_style, r'QStatusBar', small_px + 1)
        new_style = replace_size(new_style, r'QLabel#field_label', body_px)
        new_style = replace_size(new_style, r'QLabel#section_title', section_title_px)
        self.setStyleSheet(new_style)

        app = QApplication.instance()
        app_point_size = max(10, round(body_px * 0.75))
        if app:
            app.setFont(QFont("Microsoft YaHei", app_point_size))

        if hasattr(self, 'log_text'):
            self.log_text.setFont(QFont("Consolas", 16))
        if hasattr(self, '_title_lbl'):
            self._title_lbl.setStyleSheet(
                f"color: {Theme.TEXT_WHITE}; font-size: {header_title_px}px; "
                "font-weight: 700; letter-spacing: 0px; background: transparent;"
            )
        if hasattr(self, '_subtitle_lbl'):
            self._subtitle_lbl.setStyleSheet(
                "color: rgba(221,247,244,0.72); background: transparent; "
                f"font-size: {header_subtitle_px}px;"
            )
        if hasattr(self, '_left_panel') and isinstance(self._left_panel, CollapsibleSidebar):
            self._left_panel.set_page_title_font_size(page_title_px)
        if hasattr(self, '_ver_lbl'):
            self._ver_lbl.setStyleSheet(
                f"color: rgba(221,247,244,0.78); font-size: {small_px}px; "
                "background: transparent;"
            )
        if hasattr(self, 'cmd_file_label'):
            self.cmd_file_label.setStyleSheet(
                f"color: {Theme.TEXT_SECONDARY}; font-size: {body_px}px; "
                f"background: {Theme.BG_CARD}; border: 1px solid {Theme.BORDER}; "
                "border-radius: 4px; padding: 4px 6px;"
            )
        if hasattr(self, '_cmd_tip_label'):
            self._cmd_tip_label.setStyleSheet(
                f"color: {Theme.TEXT_HINT}; font-size: {small_px}px;"
            )
        if hasattr(self, 'save_check'):
            self.save_check.setStyleSheet(
                f"color: {Theme.TEXT_SECONDARY}; font-size: {body_px}px;"
            )
        if hasattr(self, 'l2_uplink_check'):
            self.l2_uplink_check.setStyleSheet(
                f"color: {Theme.TEXT_SECONDARY}; font-size: {body_px}px;"
            )
        if hasattr(self, '_log_title_label'):
            self._log_title_label.setStyleSheet(
                f"color: {Theme.TEXT_SECONDARY}; font-size: {small_px}px; "
                "background: transparent;"
            )

        self._status_badge_font_px = max(13, body_px - 3)
        if hasattr(self, 'device_table'):
            table_font = QFont("Microsoft YaHei")
            table_font.setPixelSize(body_px)
            row_height = max(36, QFontMetrics(table_font).height() + 14)
            vertical_header = self.device_table.verticalHeader()
            vertical_header.setMinimumSectionSize(row_height)
            vertical_header.setDefaultSectionSize(row_height)
            for row in range(self.device_table.rowCount()):
                self.device_table.setRowHeight(row, row_height)
                badge = self.device_table.cellWidget(row, 9)
                if isinstance(badge, StatusBadge):
                    badge.set_font_size(self._status_badge_font_px)

        self._update_form_labels(app_point_size)
        self._update_left_content_min_height()

    @staticmethod
    def _justify_form_label(text: str) -> str:
        labels = {
            "名 称:": "名　　称:",
            "品 牌:": "品　　牌:",
            "端 口:": "端　　口:",
            "密 码:": "密　　码:",
            "用户名:": "用 户 名:",
            "文件:": "文　　件:",
        }
        return labels.get(text, text)

    def _form_label_width(self, font: QFont) -> int:
        metrics = QFontMetrics(font)
        return max(
            metrics.horizontalAdvance(self._justify_form_label(getattr(label, '_form_raw_text', label.text())))
            for label in self._form_labels
        ) + 2

    def _create_form_label(self, text: str) -> QLabel:
        label = QLabel(self._justify_form_label(text))
        label._form_raw_text = text
        label.setObjectName("field_label")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._form_labels.append(label)
        return label

    def _update_form_labels(self, pt: int):
        if not getattr(self, '_form_labels', None):
            return
        font = QFont("Microsoft YaHei", pt)
        width = self._form_label_width(font)
        for label in self._form_labels:
            label.setFont(font)
            label.setText(self._justify_form_label(getattr(label, '_form_raw_text', label.text())))
            label.setFixedWidth(width)
            label.setMinimumWidth(width)
            label.setMaximumWidth(width)

    def _update_left_content_min_height(self):
        if hasattr(self, '_left_panel') and isinstance(self._left_panel, CollapsibleSidebar):
            self._left_panel.refresh_current_page_geometry()
        elif hasattr(self, '_left_content'):
            self._left_content.setMinimumHeight(self._left_content_minimum_height())

    def _left_content_minimum_height(self) -> int:
        if hasattr(self, '_left_panel') and isinstance(self._left_panel, CollapsibleSidebar):
            return self._left_panel.current_page_minimum_height()
        if not hasattr(self, '_left_content') or not self._left_content.layout():
            return 0
        layout = self._left_content.layout()
        margins = layout.contentsMargins()
        height = margins.top() + margins.bottom()
        visible_items = 0
        for index in range(layout.count()):
            item = layout.itemAt(index)
            widget = item.widget()
            if not widget or widget.isHidden():
                continue
            height += widget.minimumSizeHint().height()
            visible_items += 1
        if visible_items > 1:
            height += layout.spacing() * (visible_items - 1)
        return height

    def _resize_to_fit_default_content(self):
        if not hasattr(self, '_left_content'):
            return

        app = QApplication.instance()
        screen = app.primaryScreen() if app else None
        available = screen.availableGeometry() if screen else None

        desired_width = 1920
        if available:
            desired_width = min(desired_width, max(self.minimumWidth(), available.width()))

        self.resize(desired_width, self.height())
        self._apply_font_pt(self._calc_font_pt(desired_width))
        self._update_left_content_min_height()

        chrome_height = 132
        if hasattr(self, '_left_panel') and isinstance(self._left_panel, QScrollArea):
            viewport = self._left_panel.viewport()
            if viewport.height() > 0:
                chrome_height = max(chrome_height, self.height() - viewport.height())

        desired_height = self._left_content_minimum_height() + chrome_height + 4
        if available:
            desired_height = min(desired_height, max(self.minimumHeight(), available.height()))

        self.resize(desired_width, desired_height)

    def _update_left_panel_limit(self):
        if not hasattr(self, '_left_panel') or not hasattr(self, '_main_splitter'):
            return
        if isinstance(self._left_panel, CollapsibleSidebar):
            max_width = maximum_sidebar_width(
                self.width(),
                CollapsibleSidebar.MIN_EXPANDED_WIDTH,
            )
            self._left_panel.set_expanded_maximum_width(max_width)
            if not self._left_panel.is_expanded():
                return
        else:
            max_width = maximum_sidebar_width(self.width(), 360)
            self._left_panel.setMaximumWidth(max_width)
        sizes = self._main_splitter.sizes()
        if sizes and sizes[0] > max_width:
            total = sum(sizes)
            self._main_splitter.setSizes([max_width, max(1, total - max_width)])

    def _on_left_sidebar_expansion_changed(self, expanded: bool):
        if not hasattr(self, '_main_splitter'):
            return
        total = sum(self._main_splitter.sizes()) or self._main_splitter.width()
        if expanded:
            max_width = maximum_sidebar_width(
                self.width(),
                CollapsibleSidebar.MIN_EXPANDED_WIDTH,
            )
            target_width = expanded_sidebar_width(
                total,
                max_width,
                CollapsibleSidebar.MIN_EXPANDED_WIDTH,
            )
        else:
            target_width = CollapsibleSidebar.COLLAPSED_WIDTH
        self._main_splitter.setSizes([
            target_width,
            max(1, total - target_width),
        ])
        QTimer.singleShot(0, self._update_ops_tools_columns)

    def _update_ops_tools_columns(self):
        if not hasattr(self, '_tool_grid_specs') or not hasattr(self, '_left_panel'):
            return
        columns = operations_tool_columns(
            self._left_panel.is_expanded(),
            self._left_panel.width(),
        )
        if getattr(self, '_ops_tools_columns', None) == columns:
            return
        self._ops_tools_columns = columns
        for layout, buttons in self._tool_grid_specs:
            for button in buttons:
                layout.removeWidget(button)
            for index, button in enumerate(buttons):
                row, column = divmod(index, columns)
                layout.addWidget(button, row, column)
            for column in range(2):
                layout.setColumnStretch(
                    column,
                    1 if column < columns else 0,
                )
        self._update_left_content_min_height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_left_panel_limit()
        self._update_ops_tools_columns()
        pt = self._calc_font_pt(self.width())
        if pt != self._current_font_pt:
            self._current_font_pt = pt
            self._apply_font_pt(pt)

    # ── 状态栏 ──────────────────────────────────────────
    def _init_statusbar(self):
        self._status_controller = MainWindowStatusController(
            self,
            APP_NAME,
            APP_VERSION,
            APP_AUTHOR,
        )
        self._status_label = self._status_controller.status_label
        self.progress_bar = self._status_controller.progress_bar
        self._device_count_label = self._status_controller.device_count_label

    def _set_status(self, text: str):
        """更新右侧动态状态标签；左侧固定标题不受影响"""
        self._status_controller.set_status(text)

    def _show_progress(self):
        """显示进度条，仅在连接工作开始时调用"""
        self._status_controller.show_progress()

    def _hide_progress(self):
        """隐藏进度条，任务结束后调用"""
        self._status_controller.hide_progress()

    def _update_device_count(self):
        n = len(self.device_manager.get_devices())
        self._status_controller.update_device_count(n)

    # ── 主布局 ───────────────────────────────────────────
    def init_ui(self):
        return self._layout_builder.build()

    def _build_header(self) -> QWidget:
        return self._layout_builder.build_header()

    # ── 左侧面板 ─────────────────────────────────────────
    def create_left_panel(self) -> QWidget:
        return self._layout_builder.create_left_panel()

    @staticmethod
    def _sidebar_icon_directory() -> Path:
        return MainWindowLayoutBuilder.sidebar_icon_directory()

    @staticmethod
    def _lucide_icon_directory() -> Path:
        return MainWindowLayoutBuilder.lucide_icon_directory()

    def _decorate_action_buttons(self):
        return self._layout_builder.decorate_action_buttons()

    @staticmethod
    def _build_sidebar_page(groups) -> QWidget:
        return MainWindowLayoutBuilder.build_sidebar_page(groups)

    def _build_input_group(self) -> QGroupBox:
        panel = DeviceFormPanel(self._create_form_label)
        self._device_form_panel = panel
        for name in (
            "name_input", "brand_combo", "group_input", "tags_input",
            "ip_input", "port_spin", "username_input", "auth_method_combo",
            "password_input", "password_label", "private_key_input",
            "private_key_label", "private_key_row", "key_passphrase_input",
            "key_passphrase_label", "host_key_policy_combo", "add_btn",
        ):
            setattr(self, name, getattr(panel, name))
        panel.auth_method_changed.connect(self._update_auth_fields)
        panel.browse_private_key_requested.connect(self.browse_private_key)
        panel.add_requested.connect(self.add_device)
        self._update_auth_fields()
        return panel

    def _build_excel_group(self) -> QGroupBox:
        panel = ExcelImportPanel()
        self._excel_import_panel = panel
        self.import_btn = panel.import_btn
        self.encrypt_excel_btn = panel.encrypt_excel_btn
        self.template_btn = panel.template_btn
        panel.import_requested.connect(self.import_excel)
        panel.encrypt_requested.connect(self.encrypt_excel_passwords)
        panel.template_requested.connect(self.download_template)
        return panel

    def _build_command_group(self) -> QGroupBox:
        """命令文件选择区"""
        panel = CommandFilePanel(self._create_form_label)
        self._command_file_panel = panel
        for name in (
            "cmd_mode_combo",
            "cmd_file_label",
            "cmd_browse_btn",
            "cmd_reset_btn",
            "_cmd_tip_label",
        ):
            setattr(self, name, getattr(panel, name))
        panel.mode_changed.connect(self.on_command_mode_changed)
        panel.browse_requested.connect(self.browse_command_file)
        panel.reset_requested.connect(self.reset_command_file)
        return panel

    def _build_task_target_group(self) -> QGroupBox:
        panel = TaskTargetPanel()
        self._task_target_panel = panel
        for name in (
            "task_scope_combo",
            "task_target_summary",
            "manage_task_targets_btn",
            "clear_task_targets_btn",
        ):
            setattr(self, name, getattr(panel, name))
        panel.scope_changed.connect(self._on_task_scope_changed)
        panel.manage_targets_requested.connect(self.manage_custom_task_targets)
        panel.clear_targets_requested.connect(self.clear_custom_task_targets)
        return panel

    def _build_device_list_actions_group(self) -> QGroupBox:
        panel = DeviceListActionsPanel()
        self._device_list_actions_panel = panel
        self.delete_btn = panel.delete_btn
        self.clear_btn = panel.clear_btn
        panel.remove_selected_requested.connect(self.delete_selected_device)
        panel.clear_all_requested.connect(self.clear_devices)
        return panel

    def _build_execution_group(self) -> QGroupBox:
        panel = BatchExecutionPanel()
        self._batch_execution_panel = panel
        self.save_check = panel.save_check
        self.l2_uplink_check = panel.l2_uplink_check
        self.connect_btn = panel.connect_btn
        panel.start_requested.connect(self.start_connection)
        return panel

    def _build_device_tools_group(self) -> QGroupBox:
        panel = DeviceToolsPanel()
        self._device_tools_panel = panel
        for _key, attribute, _text, _tooltip, _maintenance in panel.TOOL_DEFINITIONS:
            setattr(self, attribute, getattr(panel, attribute))
        self._maintenance_buttons = panel.maintenance_buttons
        self._device_tools_layout = panel.tools_layout
        self._device_tool_buttons = panel.tool_buttons

        handlers = {
            "ssh_console": self.show_ssh_console,
            "batch_ping": self.batch_ping_devices,
            "port_check": self.start_port_check,
            "ssh_login_test": self.start_ssh_login_test,
            "traceroute": self.start_traceroute,
            "health_check": self.start_health_check,
            "terminal_locate": self.start_terminal_locate,
            "interface_diagnosis": self.start_interface_diagnosis,
            "config_backup": self.start_config_backup,
        }
        panel.tool_requested.connect(lambda key: handlers[key]())
        return panel

    def _build_local_tools_group(self) -> QGroupBox:
        panel = LocalToolsPanel()
        self._local_tools_panel = panel
        for _key, attribute, _text, _tooltip in panel.TOOL_DEFINITIONS:
            setattr(self, attribute, getattr(panel, attribute))
        self._local_tools_layout = panel.tools_layout
        self._local_tool_buttons = panel.tool_buttons
        self._ops_tool_buttons = (
            self._local_tool_buttons + self._device_tool_buttons
        )
        self._tool_grid_specs = [
            (self._device_tools_layout, self._device_tool_buttons),
            (self._local_tools_layout, self._local_tool_buttons),
        ]
        self._ops_tools_columns = 1
        handlers = {
            "serial_console": self.show_serial_console,
            "file_transfer": self.show_file_transfer,
            "packet_capture": self.show_packet_capture,
            "subnet_calculator": self.show_subnet_calculator,
            "config_diff": self.show_config_diff,
        }
        panel.tool_requested.connect(lambda key: handlers[key]())
        return panel

    def show_serial_console(self):
        return self._tool_window_controller.show_serial_console()

    def show_ssh_console(self):
        return self._tool_window_controller.show_ssh_console()

    def show_file_transfer(self):
        return self._tool_window_controller.show_file_transfer()

    def show_packet_capture(self):
        return self._tool_window_controller.show_packet_capture()

    def _build_config_templates_group(self) -> QGroupBox:
        panel = ConfigTemplatesPanel()
        self._config_templates_panel = panel
        self.config_template_list = panel.config_template_list
        self.use_template_btn = panel.use_template_btn
        self.add_template_btn = panel.add_template_btn
        self.remove_template_btn = panel.remove_template_btn
        panel.open_requested.connect(self.open_config_template)
        panel.use_requested.connect(self.use_config_template)
        panel.add_requested.connect(self.add_config_template)
        panel.remove_requested.connect(self.remove_config_template)
        return panel

    # ── 右侧面板 ─────────────────────────────────────────
    def create_right_panel(self) -> QWidget:
        return self._layout_builder.create_right_panel()

    # ── 业务逻辑 ─────────────────────────────────────────
    def _update_auth_fields(self):
        use_key = self.auth_method_combo.currentData() == "key"
        self.password_label.setVisible(not use_key)
        self.password_input.setVisible(not use_key)
        self.private_key_label.setVisible(use_key)
        self.private_key_row.setVisible(use_key)
        self.key_passphrase_label.setVisible(use_key)
        self.key_passphrase_input.setVisible(use_key)

    def browse_private_key(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 SSH 私钥", "",
            "SSH 私钥 (*.pem *.key *.ppk id_*);;所有文件 (*)",
        )
        if file_path:
            self.private_key_input.setText(file_path)

    def add_device(self):
        values = DeviceFormValues(
            brand=self.brand_combo.currentText(),
            ip=self.ip_input.text(),
            port=self.port_spin.value(),
            username=self.username_input.text(),
            password=self.password_input.text(),
            name=self.name_input.text(),
            group=self.group_input.text(),
            tags=self.tags_input.text(),
            auth_method=self.auth_method_combo.currentData(),
            private_key_path=self.private_key_input.text(),
            private_key_passphrase=self.key_passphrase_input.text(),
            host_key_policy=self.host_key_policy_combo.currentData(),
        )
        try:
            device = self._device_inventory_controller.add_from_form(values)
        except DeviceFormError as exc:
            self._warn(str(exc))
            return
        self.update_device_table()

        self.ip_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.name_input.clear()
        self.group_input.clear()
        self.tags_input.clear()
        self.private_key_input.clear()
        self.key_passphrase_input.clear()

        display = device.name or device.ip
        self._log_info(f"[添加]  {display}")
        self.logger.log_operation(f"添加设备: {display}")
        self._update_device_count()

    def update_device_table(self):
        devices = self.device_manager.get_devices()
        self._device_table_presenter.refresh(
            devices,
            status_font_px=getattr(self, "_status_badge_font_px", 14),
        )
        self._refresh_group_filter()
        self.apply_device_filters()
        self._update_device_count()
        self._update_task_target_summary()

    def _refresh_group_filter(self):
        self._device_table_presenter.refresh_group_filter(
            self.device_manager.get_devices()
        )

    def apply_device_filters(self):
        if not hasattr(self, "device_table"):
            return
        if not hasattr(self, "_device_table_presenter"):
            return
        self._device_table_presenter.apply_filters(
            self.device_manager.get_devices()
        )
        self._update_task_target_summary()

    def _get_execution_devices(self):
        devices = self.device_manager.get_devices()
        scope = self.execution_scope_combo.currentData()
        return self._device_table_presenter.devices_for_scope(devices, scope)

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: str) -> bool:
        index = combo.findData(value)
        if index < 0:
            return False
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)
        return True

    def _on_task_scope_changed(self):
        if not hasattr(self, "task_scope_combo"):
            return
        scope = self.task_scope_combo.currentData()
        if scope != "custom" and hasattr(self, "execution_scope_combo"):
            self._set_combo_data(self.execution_scope_combo, scope)
        self._update_task_target_summary()

    def _on_execution_scope_changed(self):
        if not hasattr(self, "task_scope_combo"):
            return
        scope = self.execution_scope_combo.currentData()
        self._set_combo_data(self.task_scope_combo, scope)
        self._update_task_target_summary()

    def _show_sidebar_page(self, key: str):
        """Open a sidebar page without collapsing it when already active."""
        if (
            self._left_panel.current_page_key() == key
            and self._left_panel.is_expanded()
        ):
            return
        self._left_panel.button(key).click()

    def show_add_device_form(self):
        self._show_sidebar_page("devices")
        self.name_input.setFocus()
        self.name_input.selectAll()

    def show_device_library_page(self):
        self._show_sidebar_page("devices")

    def show_device_tasks_page(self):
        self._show_sidebar_page("tasks")

    def show_local_tools_page(self):
        self._show_sidebar_page("tools")

    def show_template_center_page(self):
        self._show_sidebar_page("templates")

    def toggle_navigation_sidebar(self):
        self._left_panel.set_expanded(
            not self._left_panel.is_expanded()
        )

    def restore_default_layout(self):
        self._left_panel.set_expanded(False)
        total = sum(self._main_splitter.sizes()) or self._main_splitter.width()
        self._main_splitter.setSizes([
            CollapsibleSidebar.COLLAPSED_WIDTH,
            max(1, total - CollapsibleSidebar.COLLAPSED_WIDTH),
        ])
        self._set_status("已恢复默认布局")

    def open_user_guide(self):
        return self._main_action_controller.open_user_guide()

    def show_about_dialog(self):
        return self._main_action_controller.show_about_dialog()

    def _close_application(self):
        return self._main_action_controller.close_application()

    def _sync_temporary_task_devices(
        self,
        selected_devices: List,
        removed_devices=None,
    ) -> List:
        """Keep manually entered temporary devices aligned with the main list."""
        controller = getattr(self, "_device_inventory_controller", None)
        if controller is None:
            controller = DeviceInventoryController(self.device_manager)
        return controller.sync_temporary_targets(
            selected_devices,
            removed_devices,
        )

    def _valid_custom_task_targets(self) -> List:
        controller = getattr(self, "_device_inventory_controller", None)
        if controller is None:
            controller = DeviceInventoryController(self.device_manager)
        valid = controller.valid_custom_targets(self._custom_task_targets)
        if len(valid) != len(self._custom_task_targets):
            self._custom_task_targets = valid
        return list(valid)

    def _update_task_target_summary(self):
        if not hasattr(self, "task_target_summary"):
            return
        scope = self.task_scope_combo.currentData()
        if scope == "custom":
            devices = self._valid_custom_task_targets()
            self.task_target_summary.setText(
                self._device_inventory_controller.describe_targets(scope, devices)
            )
            self.clear_task_targets_btn.setEnabled(True)
            return

        devices = (
            self._get_execution_devices()
            if hasattr(self, "execution_scope_combo")
            else []
        )
        self.task_target_summary.setText(
            self._device_inventory_controller.describe_targets(scope, devices)
        )
        self.clear_task_targets_btn.setEnabled(False)

    def manage_custom_task_targets(self):
        current = (
            self._valid_custom_task_targets()
            if self.task_scope_combo.currentData() == "custom"
            else self._get_execution_devices()
        )
        dialog = MaintenanceTargetDialog(
            "shared_targets",
            current,
            self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        self._custom_task_targets = self._sync_temporary_task_devices(
            dialog.selected_devices(),
            dialog.removed_temporary_targets(),
        )
        self.update_device_table()
        if not self._custom_task_targets:
            custom_index = self.task_scope_combo.findData("custom")
            if custom_index >= 0:
                self.task_scope_combo.removeItem(custom_index)
            self._set_combo_data(
                self.task_scope_combo,
                self.execution_scope_combo.currentData(),
            )
            self._update_task_target_summary()
            self._set_status("临时目标已移除，已恢复使用设备表范围")
            return
        if self.task_scope_combo.findData("custom") < 0:
            self.task_scope_combo.addItem("自定义目标", "custom")
        self._set_combo_data(self.task_scope_combo, "custom")
        self._update_task_target_summary()
        self._set_status(
            f"已设置自定义作业目标：{len(self._custom_task_targets)} 个"
        )

    def clear_custom_task_targets(self):
        self._custom_task_targets = []
        custom_index = self.task_scope_combo.findData("custom")
        if custom_index >= 0:
            self.task_scope_combo.removeItem(custom_index)
        scope = self.execution_scope_combo.currentData()
        self._set_combo_data(self.task_scope_combo, scope)
        self._update_task_target_summary()
        self._set_status("已恢复使用设备表目标范围")

    def _get_task_devices(self, mode: str = "") -> List:
        if self.task_scope_combo.currentData() == "custom":
            devices = self._valid_custom_task_targets()
        else:
            devices = self._get_execution_devices()
        return self._device_inventory_controller.task_devices(devices, mode)

    def open_result_center(self):
        return self._tool_window_controller.open_result_center()

    def _get_task_audit_store(self):
        if self._task_audit_store is None:
            self._task_audit_store = TaskAuditStore()
        return self._task_audit_store

    def show_task_history(self):
        return self._tool_window_controller.show_task_history()

    def import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "", "Excel Files (*.xlsx *.xls)"
        )
        if not file_path:
            return

        try:
            password_mode = self.device_manager.inspect_excel_password_mode(file_path)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法读取 Excel 文件：\n{e}")
            return

        master_password = ""
        if password_mode in ("encrypted", "mixed"):
            master_password, accepted = prompt_secret(
                self,
                "解密认证信息",
                "请输入该 Excel 的主密码：",
            )
            if not accepted:
                return
            if not master_password:
                QMessageBox.warning(self, "主密码", "主密码不能为空")
                return
        elif password_mode == "plain":
            answer = QMessageBox.warning(
                self, "明文认证信息警告",
                "检测到 Excel 中保存了明文密码或私钥口令。"
                "建议先使用“加密 Excel 认证信息”生成加密副本。\n\n仍要继续导入吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        result = self._device_inventory_controller.import_excel(
            file_path,
            master_password=master_password,
        )
        self.update_device_table()

        QMessageBox.information(self, "导入结果", result.summary())
        self._log_info(
            f"[导入] Excel 文件 -> 新增 {result.added} 个，"
            f"跳过重复 {result.skipped} 个，失败 {result.failed} 个"
        )
        self.logger.log_operation(
            f"从 Excel 导入设备: 新增={result.added}, "
            f"跳过重复={result.skipped}, 失败={result.failed}"
        )
        self._set_status(
            f"导入完成: 新增 {result.added} / 跳过 {result.skipped}"
        )
        QTimer.singleShot(3000, self._update_device_count)

    def download_template(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存模板", "device_template.xlsx", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        if self.device_manager.create_template_excel(file_path):
            QMessageBox.information(self, "成功", f"模板已保存到:\n{file_path}")
        else:
            QMessageBox.critical(self, "错误", "模板创建失败")

    def _current_device_ips(self, devices=None) -> List[str]:
        ips = []
        seen = set()
        for device in (
            self.device_manager.get_devices() if devices is None else devices
        ):
            ip = str(getattr(device, "ip", "") or "").strip()
            if not ip:
                continue
            key = self._normalize_ip(ip).lower()
            if key in seen:
                continue
            seen.add(key)
            ips.append(ip)
        return ips

    def batch_ping_devices(self):
        blocking_reason = self._maintenance_controller.blocking_reason("ping")
        if blocking_reason:
            self._warn(blocking_reason)
            return

        devices = self._select_maintenance_targets("ping")
        if not devices:
            return
        ips = self._current_device_ips(devices)

        self.log_text.clear()
        self._ping_log_lines = []
        self._record_ping_log(
            f"[批量 Ping] 使用设备列表、手工地址或网段目标，"
            f"共 {len(ips)} 个地址"
        )

        self.ping_excel_btn.setEnabled(False)
        self._show_progress()
        self.progress_bar.setRange(0, 0)
        self._set_status(f"批量 Ping 中... 共 {len(ips)} 个 IP")

        self.ping_worker = self._maintenance_controller.start_ping(ips)

    def batch_ping_finished(self, total: int, success: int, failure: int):
        self.ping_excel_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        QTimer.singleShot(800, self._hide_progress)

        rate = (success / total * 100) if total else 0.0
        self._record_ping_log(f"[批量 Ping 完成] 总数: {total} 个，成功: {success} 个，失败: {failure} 个，成功率: {rate:.1f}%")
        log_path = self._save_ping_log_file()
        if log_path:
            self._log_info(f"[批量 Ping] 日志文件已生成: {log_path}")
        self._set_status(f"Ping 完成: {success} 成功 / {failure} 失败")
        self.logger.log_operation(f"批量 Ping 完成: 总数={total}, 成功={success}, 失败={failure}")
        QTimer.singleShot(3000, self._update_device_count)

    def _maintenance_devices(self) -> List:
        devices = self._get_task_devices()
        if not devices:
            QMessageBox.warning(
                self,
                "设备作业",
                "当前目标范围内没有可用设备，请调整目标范围或补充临时目标",
            )
            return []
        return devices

    def _select_maintenance_targets(self, mode: str) -> List:
        devices = self._get_task_devices(mode)
        if not devices:
            QMessageBox.warning(
                self,
                "未选择目标",
                "当前目标范围内没有适用于此任务的设备。\n\n"
                "请在“设备作业”的目标设备区域调整范围或补充临时目标。",
            )
            return []
        credential_modes = {
            "command",
            "ssh_login",
            "health_check",
            "terminal_locate",
            "interface_diagnosis",
            "backup",
        }
        if mode in credential_modes:
            missing = [
                device
                for device in devices
                if getattr(device, "_aomt_temporary", False)
                and not str(getattr(device, "username", "") or "").strip()
            ]
            if missing:
                QMessageBox.warning(
                    self,
                    "临时目标缺少 SSH 凭据",
                    "当前自定义目标中有临时地址未填写 SSH 用户名和密码。\n\n"
                    "请点击“补充临时目标”重新设置，或切换回设备表范围。",
                )
                return []
        return list(devices)

    def _start_maintenance_task(self, mode: str, options=None, devices=None):
        blocking_reason = self._maintenance_controller.blocking_reason(
            "maintenance"
        )
        if blocking_reason:
            self._warn(blocking_reason)
            return

        devices = list(devices) if devices is not None else (
            self._maintenance_devices()
        )
        if not devices:
            return

        label = maintenance_task_definition(mode).label
        self._maintenance_log_lines = []
        self.log_text.clear()
        self._record_maintenance_log(f"[{label}] 开始，共 {len(devices)} 台设备")
        self._set_maintenance_running(True)
        self._show_progress()
        self.progress_bar.setRange(0, 0)
        self._set_status(f"{label}正在执行...")

        self.maintenance_worker = self._maintenance_controller.start_maintenance(
            mode,
            devices,
            options=options,
        )

    def _start_diagnostics_task(self, mode: str, devices, options=None):
        blocking_reason = self._maintenance_controller.blocking_reason(
            "diagnostics"
        )
        if blocking_reason:
            self._warn(blocking_reason)
            return

        label = diagnostic_task_definition(mode).label
        self._maintenance_log_lines = []
        self.log_text.clear()
        self._record_maintenance_log(
            f"[{label}] 开始，共 {len(devices)} 台设备；"
            "当前支持 H3C/Comware 和 Huawei VRP"
        )
        self._set_maintenance_running(True)
        self._show_progress()
        self.progress_bar.setRange(0, 0)
        self._set_status(f"{label}正在执行...")

        self.diagnostics_worker = self._maintenance_controller.start_diagnostics(
            mode,
            devices,
            options=options,
        )

    def _diagnostics_task_finished(self, mode: str, results):
        definition = diagnostic_task_definition(mode)
        label, prefix = definition.result_label, definition.log_prefix
        results, success, failure = diagnostic_result_counts(results)
        self._record_maintenance_log(
            f"[{label}完成] 设备: {len(results)}，成功: {success}，"
            f"未找到或失败: {failure}"
        )
        log_path = self._save_maintenance_log(prefix)
        if log_path:
            self._log_info(f"[{label}] 日志文件已生成: {log_path}")

        self.execution_results = results
        self._set_maintenance_running(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        QTimer.singleShot(800, self._hide_progress)
        self._set_status(f"{label}完成: {success} 成功 / {failure} 未找到或失败")
        self.logger.log_operation(
            f"{label}完成: 设备={len(results)}, 成功={success}, "
            f"未找到或失败={failure}"
        )
        dialog = ResultCenterDialog(results, self)
        dialog.exec_()

    def _set_maintenance_running(self, running: bool):
        self.ping_excel_btn.setEnabled(not running)
        for button in self._maintenance_buttons:
            button.setEnabled(not running)

    def _record_maintenance_log(self, text: str):
        timestamped = f"[{self._ts()}] {text}"
        self._maintenance_log_lines.append(timestamped)
        self._log_append(text)

    def _maintenance_task_finished(
        self,
        mode: str,
        total: int,
        success: int,
        failure: int,
    ):
        definition = maintenance_task_definition(mode)
        label = definition.result_label
        prefix = definition.log_prefix
        self._record_maintenance_log(
            f"[{label}完成] 总任务: {total}，成功: {success}，失败: {failure}"
        )
        log_path = self._save_maintenance_log(prefix)
        if log_path:
            self._log_info(f"[{label}] 日志文件已生成: {log_path}")

        self._set_maintenance_running(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        QTimer.singleShot(800, self._hide_progress)
        self._set_status(f"{label}完成: {success} 成功 / {failure} 失败")
        self.logger.log_operation(
            f"{label}完成: 总任务={total}, 成功={success}, 失败={failure}"
        )
        QTimer.singleShot(3000, self._update_device_count)

    def _save_maintenance_log(self, prefix: str) -> str:
        try:
            return save_maintenance_log(
                self.logger.log_dir,
                prefix,
                self._maintenance_log_lines,
            )
        except OSError as exc:
            self._log_append(f"[运维工具] 日志文件生成失败: {exc}")
            return ""

    def start_health_check(self):
        devices = self._select_maintenance_targets("health_check")
        if not devices:
            return
        profile_dialog = HealthProfileDialog(self)
        if profile_dialog.exec_() != QDialog.Accepted:
            return
        options = profile_dialog.selected_options()
        builtin_count = len(options.get("builtin_items", []))
        custom_count = sum(
            len(commands)
            for commands in options.get("custom_commands", {}).values()
        )
        if not self._confirm_action(
            "确认一键设备巡检",
            f"将连接 {len(devices)} 台设备并执行只读巡检命令。\n\n"
            f"方案：{options.get('profile_name') or '未命名'}\n"
            f"内置项目：{builtin_count} 项；品牌自定义命令：{custom_count} 条。\n\n"
            "当前版本对 H3C/Comware 和 Huawei VRP 使用各自明确的命令；"
            "检测到其他品牌时会停止，不会尝试发送未经验证的命令。\n\n"
            "自定义命令只保留原始输出，不参与自动健康判定。",
        ):
            return
        self._start_diagnostics_task("health_check", devices, options)

    def start_terminal_locate(self):
        devices = self._select_maintenance_targets("terminal_locate")
        if not devices:
            return
        value, accepted = QInputDialog.getText(
            self,
            "IP/MAC 终端定位",
            "请输入需要定位的 IPv4 地址或 MAC 地址：",
        )
        if not accepted:
            return
        try:
            target_type, target = normalize_lookup_target(value)
        except ValueError as exc:
            QMessageBox.warning(self, "目标格式错误", str(exc))
            return
        self._start_diagnostics_task(
            "terminal_locate",
            devices,
            {"target_type": target_type, "target": target},
        )

    def start_interface_diagnosis(self):
        devices = self._select_maintenance_targets("interface_diagnosis")
        if not devices:
            return
        value, accepted = QInputDialog.getText(
            self,
            "接口综合诊断",
            "请输入需要检查的 H3C 接口名称：",
            text="GigabitEthernet1/0/1",
        )
        if not accepted:
            return
        try:
            interface = validate_interface_name(value)
        except ValueError as exc:
            QMessageBox.warning(self, "接口格式错误", str(exc))
            return
        self._start_diagnostics_task(
            "interface_diagnosis",
            devices,
            {"interface": interface},
        )

    def start_port_check(self):
        devices = self._select_maintenance_targets("port")
        if not devices:
            return
        value, accepted = QInputDialog.getText(
            self,
            "批量端口检测",
            "请输入 TCP 端口，使用逗号分隔：",
            text="22,23,80,443",
        )
        if not accepted:
            return
        try:
            ports = parse_tcp_ports(value)
        except ValueError as exc:
            QMessageBox.warning(self, "端口输入错误", str(exc))
            return
        self._start_maintenance_task(
            "port",
            {"ports": ports},
            devices=devices,
        )

    def start_ssh_login_test(self):
        devices = self._select_maintenance_targets("ssh_login")
        if not devices:
            return
        if not self._confirm_action(
            "确认 SSH 登录测试",
            f"将验证 {len(devices)} 台已选择或手工输入的设备。\n\n"
            "设备列表中的目标使用各自凭据，手工目标使用刚才填写的凭据。\n\n"
            "测试只进行 SSH 认证，不执行设备命令。请确认密码正确，"
            "避免连续认证失败触发设备账号锁定。",
        ):
            return
        self._start_maintenance_task("ssh_login", devices=devices)

    def start_traceroute(self):
        devices = self._select_maintenance_targets("traceroute")
        if not devices:
            return
        self._start_maintenance_task("traceroute", devices=devices)

    def start_config_backup(self):
        devices = self._select_maintenance_targets("backup")
        if not devices:
            return
        output_dir = QFileDialog.getExistingDirectory(self, "选择配置备份目录", "")
        if not output_dir:
            return
        if not self._confirm_action(
            "确认配置备份",
            f"将连接 {len(devices)} 台设备并执行只读的当前配置查询命令。\n\n"
            f"备份根目录：{output_dir}\n\n"
            "每台设备将建立独立目录，并保存 CFG 配置正文和 JSON 元数据。\n"
            "程序会显示实际查询命令；无法获得有效配置时不会生成备份文件。",
        ):
            return
        self._start_maintenance_task(
            "backup",
            {"output_dir": output_dir},
            devices=devices,
        )

    def show_config_diff(self):
        return self._tool_window_controller.show_config_diff()

    def show_subnet_calculator(self):
        return self._tool_window_controller.show_subnet_calculator()

    def encrypt_excel_passwords(self):
        source_path, _ = QFileDialog.getOpenFileName(
            self, "选择需要加密的 Excel", "", "Excel Files (*.xlsx)"
        )
        if not source_path:
            return

        master_password, accepted = prompt_secret(
            self,
            "设置主密码",
            "请输入主密码（至少 8 个字符）：",
        )
        if not accepted:
            return
        confirm_password, accepted = prompt_secret(
            self,
            "确认主密码",
            "请再次输入主密码：",
        )
        if not accepted:
            return
        if master_password != confirm_password:
            QMessageBox.warning(self, "主密码", "两次输入的主密码不一致")
            return

        base, _ = os.path.splitext(source_path)
        target_path, _ = QFileDialog.getSaveFileName(
            self, "保存加密 Excel", f"{base}_encrypted.xlsx", "Excel Files (*.xlsx)"
        )
        if not target_path:
            return
        try:
            count = self.device_manager.encrypt_excel_passwords(
                source_path, target_path, master_password
            )
        except Exception as e:
            QMessageBox.critical(self, "加密失败", str(e))
            return

        QMessageBox.information(
            self, "加密完成",
            f"已加密 {count} 个设备密码。\n\n文件：{target_path}\n\n请妥善保管主密码，遗失后无法恢复。",
        )
        self._log_info(f"[安全]  已生成加密 Excel，共加密 {count} 个设备密码")

    def _record_ping_log(self, text: str):
        self._ping_log_lines.append(f"[{self._ts()}] {text}")
        self._log_append(text)

    def _save_ping_log_file(self) -> str:
        try:
            log_dir = os.path.abspath(self.logger.log_dir)
            os.makedirs(log_dir, exist_ok=True)
            base_name = f"ping{datetime.now().strftime('%Y%m%d%H%M')}"
            log_path = os.path.join(log_dir, f"{base_name}.log")
            counter = 1
            while os.path.exists(log_path):
                log_path = os.path.join(log_dir, f"{base_name}_{counter}.log")
                counter += 1

            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(self._ping_log_lines))
                f.write("\n")
            return log_path
        except Exception as exc:
            self._log_append(f"[批量 Ping] 日志文件生成失败: {exc}")
            return ""

    def _load_config_templates(self):
        self._config_templates = []
        try:
            self._config_templates = self._config_template_controller.load()
        except Exception as exc:
            self._config_templates = []
            self._config_template_controller.replace_user_templates([])
            self._log_append(f"[模板] 配置模板加载失败: {exc}")
        self._refresh_config_template_list()

    def _save_config_templates(self):
        self._config_template_controller.replace_user_templates(
            self._config_templates
        )
        self._config_template_controller.save()

    def _refresh_config_template_list(self):
        if not hasattr(self, "config_template_list"):
            return
        self.config_template_list.clear()
        self._config_template_controller.replace_user_templates(
            self._config_templates
        )
        all_templates = self._config_template_controller.all_templates()
        for item in all_templates:
            path = item.get("path", "")
            name = item.get("name") or os.path.basename(path)
            builtin = bool(item.get("builtin"))
            prefix = "内置" if builtin else "自定义"
            list_item = QListWidgetItem(f"{prefix} · {name}")
            description = item.get("description", "")
            tooltip = f"{description}\n{path}".strip()
            list_item.setToolTip(tooltip)
            list_item.setData(Qt.UserRole, dict(item))
            if builtin:
                list_item.setForeground(QColor(Theme.PRIMARY_DARK))
            self.config_template_list.addItem(list_item)

    @staticmethod
    def _template_item_data(item):
        if item is None:
            return {}
        data = item.data(Qt.UserRole)
        if isinstance(data, dict):
            return data
        # Keep compatibility with list items created by older versions.
        return {
            "name": os.path.basename(data) if data else "模板",
            "path": data or "",
            "builtin": False,
        }

    def add_config_template(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "添加配置模板",
            "",
            "配置模板 (*.txt *.cfg *.conf *.log *.md);;所有文件 (*.*)",
        )
        if not file_paths:
            return

        self._config_template_controller.replace_user_templates(
            self._config_templates
        )
        added, skipped = self._config_template_controller.add(file_paths)
        self._config_templates = list(
            self._config_template_controller.user_templates
        )

        if not added:
            self._warn("选择的模板都已存在")
            return
        self._refresh_config_template_list()
        self._update_left_content_min_height()
        self._log_info(f"[模板] 已添加 {len(added)} 个配置模板")
        for path in added[:5]:
            self._log_info(f"[模板] {path}")
        if skipped:
            self._log_append(f"[模板] 已跳过 {len(skipped)} 个重复模板")
        self._set_status(f"配置模板已添加 {len(added)} 个")
        QTimer.singleShot(3000, self._update_device_count)

    def remove_config_template(self):
        row = self.config_template_list.currentRow()
        if row < 0:
            self._warn("请先选择要移除的模板")
            return
        item = self.config_template_list.item(row)
        template = self._template_item_data(item)
        if template.get("builtin"):
            self._warn("内置模板由程序提供，不能移除")
            return
        name = template.get("name") or "模板"
        if not self._confirm_action("确认移除", f"确定要移除配置模板“{name}”吗？\n\n此操作只会从列表移除，不会删除原文件。"):
            return
        self._config_template_controller.replace_user_templates(
            self._config_templates
        )
        self._config_templates = self._config_template_controller.remove(
            template.get("path", ""),
        )
        self._refresh_config_template_list()
        self._update_left_content_min_height()
        self._log_info(f"[模板] 已移除配置模板: {name}")

    def open_config_template(self, item: QListWidgetItem):
        template = self._template_item_data(item)
        file_path = template.get("path", "")
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "模板不存在", "模板文件不存在，可能已被移动或删除")
            return

        try:
            content = self._config_template_controller.read(file_path)
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self, "打开失败", f"无法读取模板文件:\n{exc}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"配置模板 - {os.path.basename(file_path)}")
        dialog.resize(900, 700)
        layout = QVBoxLayout(dialog)

        title = QLabel(file_path)
        title.setWordWrap(True)
        title.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 15px;")
        layout.addWidget(title)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setFont(QFont("Consolas", 14))
        viewer.setPlainText(content)
        layout.addWidget(viewer)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        self._log_info(f"[模板] 查看配置模板: {file_path}")
        dialog.exec_()

    def use_config_template(self):
        item = self.config_template_list.currentItem()
        if item is None:
            self._warn("请先选择要调用的模板")
            return

        template = self._template_item_data(item)
        file_path = template.get("path", "")
        name = template.get("name") or os.path.basename(file_path)
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "模板不存在", "模板文件不存在，可能已被移动或删除")
            return

        if template.get("parameterized"):
            dialog = ConfigTemplateDialog(template, self)
            if dialog.exec_() != QDialog.Accepted:
                return
            rendered = dialog.rendered_template
            if rendered is None:
                return
            single_index = self.cmd_mode_combo.findData("single")
            if single_index >= 0:
                self.cmd_mode_combo.setCurrentIndex(single_index)
            self._command_file = None
            self._command_directory = None
            self._command_lines = list(rendered.commands)
            self._required_template_brand = template.get("brand", "")
            self._active_template_name = name
            self._active_template_sensitive = rendered.contains_secrets
            self._template_secret_values = list(rendered.secret_values)
            self.cmd_file_label.setText(f"参数模板：{name}")
            self.cmd_file_label.setToolTip(
                f"仅适用于 {self._required_template_brand.upper()}；"
                "参数只保存在当前内存"
            )
            self._log_info(
                f"[模板] 已生成参数化模板: {name}，"
                f"共 {len(rendered.commands)} 条命令"
            )
            self._set_status(f"当前参数模板: {name}")
            self._show_sidebar_page("tasks")
            QTimer.singleShot(3000, self._update_device_count)
            return

        if not self._confirm_action(
            "调用配置模板",
            f"确定将“{name}”设为当前业务命令吗？\n\n"
            "程序不会转换模板命令。调用后仍需点击“开始执行”才会执行，"
            "请先双击模板核对目标设备是否支持。",
        ):
            return

        single_index = self.cmd_mode_combo.findData("single")
        if single_index >= 0:
            self.cmd_mode_combo.setCurrentIndex(single_index)
        self._command_directory = None
        self._command_file = file_path
        self._command_lines = None
        self._required_template_brand = ""
        self._active_template_name = ""
        self._active_template_sensitive = False
        self._template_secret_values = []
        self.cmd_file_label.setText(f"模板：{name}")
        self.cmd_file_label.setToolTip(file_path)
        self._log_info(f"[模板] 已调用配置模板: {name}")
        self._set_status(f"当前业务命令模板: {name}")
        self._show_sidebar_page("tasks")
        QTimer.singleShot(3000, self._update_device_count)

    def start_connection(self):
        if self._batch_execution_controller.is_running():
            self.stop_connection()
            return

        devices = self._select_maintenance_targets("command")
        if not devices:
            return

        self.ssh_manager = self._batch_execution_controller.prepare(
            BatchCommandSettings(
                command_file=self._command_file,
                command_directory=self._command_directory,
                command_lines=(
                    tuple(self._command_lines)
                    if self._command_lines is not None
                    else None
                ),
                command_label=self._active_template_name,
                required_brand=self._required_template_brand,
                sensitive_values=tuple(self._template_secret_values),
            )
        )

        if self._required_template_brand:
            mismatched = devices_with_brand_mismatch(
                devices,
                self._required_template_brand,
            )
            if mismatched:
                names = "、".join(
                    (device.name or device.ip) for device in mismatched[:8]
                )
                QMessageBox.warning(
                    self,
                    "模板品牌不匹配",
                    f"当前模板仅适用于 {self._required_template_brand.upper()}，"
                    f"以下设备品牌不匹配：\n{names}\n\n已阻止执行。",
                )
                return

        if self.cmd_mode_combo.currentData() == "per_device" and (
            not self._command_directory
            or not os.path.isdir(self._command_directory)
        ):
            QMessageBox.warning(self, "脚本目录", "请先选择有效的设备脚本目录")
            return

        preview_entries = build_execution_preview(devices, self.ssh_manager)
        preview_dialog = ExecutionPreviewDialog(
            preview_entries,
            save_after_exec=self.save_check.isChecked(),
            detect_l2_uplink=self.l2_uplink_check.isChecked(),
            parent=self,
        )
        if preview_dialog.exec_() != QDialog.Accepted:
            return

        source_label = command_source_label(
            self._active_template_name,
            self.cmd_mode_combo.currentData(),
            self._command_directory,
            self._command_file,
        )
        try:
            self._active_batch_audit_id = self._get_task_audit_store().start_task(
                "batch_command",
                source_label,
                preview_fingerprint(preview_entries),
                devices,
                {
                    "mode": self.cmd_mode_combo.currentData(),
                    "save_after_exec": self.save_check.isChecked(),
                    "detect_l2_uplink": self.l2_uplink_check.isChecked(),
                },
            )
        except Exception as exc:
            self._active_batch_audit_id = None
            self._log_append(f"[审计] 无法创建任务记录：{exc}")

        self._total_count    = len(devices)
        self._connected_count = 0
        self.execution_results = []

        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("停止任务")
        self.add_btn.setEnabled(False)
        self.import_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self._show_progress()               # 展开动画：仅在连接工作开始时显示
        self.progress_bar.setRange(0, 0)    # 不定进度（来回滚动）

        self.log_text.clear()
        self._log_info(f"[开始]  正在连接 {self._total_count} 台设备 ...")
        if self.save_check.isChecked():
            self._log_info("[选项]  执行后保存配置: 已启用")
        if self.l2_uplink_check.isChecked():
            self._log_info("[选项]  二层上联口探测: 已启用")
        self._set_status(f"连接中... 共 {self._total_count} 台设备")

        # 建议1：预置所有设备状态为"连接中"，消除启动到首台完成之间的视觉空白
        execution_keys = execution_device_keys(devices)
        all_devices = self.device_manager.get_devices()
        for i in range(self.device_table.rowCount()):
            device = all_devices[i]
            if (device.ip, int(device.port)) not in execution_keys:
                continue
            badge = self.device_table.cellWidget(i, 9)
            if isinstance(badge, StatusBadge):
                badge.setText("⏳ 连接中")
            else:
                b = StatusBadge(
                    "⏳ 连接中",
                    font_px=getattr(self, "_status_badge_font_px", 14),
                )
                self.device_table.setCellWidget(i, 9, b)

        self.connection_worker = self._batch_execution_controller.start(
            devices,
            save_after_exec=self.save_check.isChecked(),
            detect_l2_uplink=self.l2_uplink_check.isChecked(),
        )

    def stop_connection(self):
        self._batch_execution_controller.stop()
        self.connect_btn.setEnabled(False)
        self._log_info("[停止]  正在停止连接任务，已运行的 SSH 会话会被断开")
        self._set_status("正在停止连接任务...")

    def update_progress(self, message: str):
        self._log_append(message)

    # ─── 建议2+3+4：逐设备实时状态槽（在主线程执行，线程安全）───────────
    @staticmethod
    def _normalize_ip(ip: str) -> str:
        """建议3：规范化 IP 地址用于比对（统一 IPv6 压缩格式，消除大小写/括号差异）"""
        try:
            from utils.ipv6_utils import IPv6Utils
            ip = ip.strip()
            # 去除 IPv6 显示括号
            if ip.startswith("[") and ip.endswith("]"):
                ip = ip[1:-1]
            if ":" in ip:
                return IPv6Utils.normalize_ipv6(ip)
            return ip
        except Exception:
            return ip.strip("[]")

    def _find_row_by_ip(self, raw_ip: str) -> int:
        """按规范化 IP 在设备表中查找行号，返回 -1 表示未找到"""
        norm_target = self._normalize_ip(raw_ip)
        for i in range(self.device_table.rowCount()):
            cell = self.device_table.item(i, 5)
            if cell is None:
                continue
            norm_cell = self._normalize_ip(cell.text())
            if norm_cell == norm_target:
                return i
        return -1

    def on_device_status(self, ip: str, status_text: str,
                         is_success: bool, brand: str, model: str):
        """建议2：每台设备完成时立即更新状态列和型号列（不等待全部完成）"""
        if is_success:
            self._connected_count += 1

        row = self._find_row_by_ip(ip)
        if row == -1:
            return

        # 建议4：通过 StatusBadge cell widget 更新状态
        badge = self.device_table.cellWidget(row, 9)
        if isinstance(badge, StatusBadge):
            badge.setText(status_text)
        else:
            badge = StatusBadge(
                status_text,
                font_px=getattr(self, "_status_badge_font_px", 14),
            )
            self.device_table.setCellWidget(row, 9, badge)

        # 型号列同步更新
        if model:
            self.device_table.setItem(row, 4, QTableWidgetItem(model))

    def handle_result(self, result: dict):
        """全量结果兜底：补充型号列、更新连接计数（逐设备信号已处理状态列）"""
        self.execution_results = upsert_execution_result(
            self.execution_results,
            result,
        )
        device_info = result.get("device_info", {})
        ip = device_info.get("ip", "")
        model_detected = result.get("model_detected", "") or ""

        row = self._find_row_by_ip(ip)
        if row == -1:
            return

        # 型号列兜底（on_device_status 若已写入则此处覆盖为同值，无害）
        if model_detected:
            self.device_table.setItem(row, 4, QTableWidgetItem(model_detected))

        # 状态列兜底（处理 on_device_status 可能未触发的极端情况）
        badge = self.device_table.cellWidget(row, 9)
        if isinstance(badge, StatusBadge):
            current = badge.text()
            # 仅在仍为"连接中"或"待连接"时才执行兜底更新
            if "连接中" in current or "待连接" in current:
                badge.setText(result_status_text(result))

    def connection_finished(self):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("开始执行")
        self.add_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        # 先跳到 100% 给用户一个"任务完成"的视觉确认，再收缩隐藏
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        QTimer.singleShot(800, self._hide_progress)   # 800ms 后收缩消失

        results = self._batch_execution_controller.results()
        if self._active_batch_audit_id is not None:
            try:
                self._get_task_audit_store().finish_task(
                    self._active_batch_audit_id,
                    results,
                    execution_audit_status(results),
                )
            except Exception as exc:
                self._log_append(f"[审计] 无法完成任务记录：{exc}")
            finally:
                self._active_batch_audit_id = None
        if self.ssh_manager and self._active_template_sensitive:
            self._batch_execution_controller.clear_sensitive_commands()
        summary = summarize_connections(results, self._total_count)
        total = summary.total
        success = summary.success
        failure = summary.failure
        rate = summary.success_rate

        self._log_info(f"[完成] 成功: {success} 台，失败: {failure} 台，成功率: {rate:.1f}%")
        self._set_status(f"完成: {success} 成功 / {failure} 失败")
        self.logger.log_operation(f"连接任务完成: 成功={success}, 失败={failure}, 总数={total}")
        # 3 秒后右侧标签恢复为设备数显示
        QTimer.singleShot(3000, self._update_device_count)

        QMessageBox.information(self, "连接完成", summary.message())
        if self._active_template_sensitive:
            self._clear_parameterized_template(
                "包含密码的参数模板已在任务结束后从内存清除"
            )
            self.cmd_file_label.setText("SSH_command.txt  (默认)")
            self.cmd_file_label.setToolTip("")

    def delete_selected_device(self):
        return self._main_action_controller.delete_selected_device()

    def clear_devices(self):
        return self._main_action_controller.clear_devices()

    def view_logs(self):
        return self._main_action_controller.view_logs()

    def clear_connection_log(self):
        return self._main_action_controller.clear_connection_log()

    def browse_command_file(self):
        return self._main_action_controller.browse_command_file()

    def reset_command_file(self):
        return self._main_action_controller.reset_command_file()

    def on_command_mode_changed(self):
        return self._main_action_controller.on_command_mode_changed()

    def _clear_parameterized_template(self, log_message: str = ""):
        self._command_lines = None
        self._required_template_brand = ""
        self._active_template_name = ""
        self._active_template_sensitive = False
        self._template_secret_values = []
        if log_message:
            self._log_info(f"[模板] {log_message}")

    # ── 日志辅助 ─────────────────────────────────────────
    @staticmethod
    def _ts() -> str:
        """返回当前时间戳字符串，用于日志前缀"""
        return current_timestamp()

    def _log_info(self, text: str):
        self.log_text.append(format_info_html(text, self._ts()))

    def _log_append(self, text: str):
        self.log_text.append(format_log_html(text, self._ts()))

    def _warn(self, msg: str):
        show_input_warning(self, msg)

    def _confirm_action(self, title: str, message: str) -> bool:
        return confirm_action(self, title, message)


# ─────────────────────── 主函数 ───────────────────────
def main():
    from PyQt5.QtWidgets import QApplication
    import sys

    # 禁用 Qt 自动 DPI 缩放，由操作系统和 Fusion 样式自行处理，
    # 避免在非最大化窗口下控件尺寸被放大导致布局溢出。
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 全局字体 10pt
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 应用全局样式
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
