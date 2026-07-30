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
                             QProgressBar, QSplitter, QSplitterHandle, QHeaderView, QFrame,
                             QStatusBar, QToolBar, QAction, QSizePolicy,
                             QAbstractItemView, QApplication, QCheckBox,
                             QScrollArea, QListWidget, QListWidgetItem,
                             QDialog, QDialogButtonBox, QInputDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QRectF, QPointF
from PyQt5.QtGui import (
    QFont, QFontMetrics, QColor, QPalette, QIcon, QPixmap, QPainter,
    QBrush, QPen, QLinearGradient, QPainterPath,
)
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import os
import sys
import json
import subprocess
import html
import re
import paramiko

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.device_config import DeviceConfigManager, DeviceInfo
from config.device_commands import CommandModule, get_command
from config.builtin_templates import get_builtin_templates
from config.app_info import APP_AUTHOR, APP_NAME, APP_SHORT_NAME, APP_VERSION
from config.ssh_security import (
    build_connect_kwargs,
    configure_host_key_policy,
    normalize_host_key_policy,
    persist_host_keys,
)
from core.ssh_manager_simple import SSHManager, SSHConnection
from ui.collapsible_sidebar import CollapsibleSidebar
from ui.result_dialog import ResultCenterDialog
from ui.maintenance_target_dialog import MaintenanceTargetDialog
from ui.serial_console import SerialConsoleDialog
from ui.ssh_console import SSHConsoleDialog
from ui.file_transfer_dialog import FileTransferDialog
from ui.packet_capture_dialog import PacketCaptureDialog
from ui.config_template_dialog import ConfigTemplateDialog
from ui.device_diagnostics_worker import DeviceDiagnosticsWorker
from ui.health_profile_dialog import HealthProfileDialog
from utils.logger import ConnectionLogger
from utils.ipv6_utils import IPv6Utils, IPv6AddressValidator
from utils.maintenance_tools import (
    calculate_subnet,
    check_tcp_port,
    normalize_device_config,
    normalize_host,
    parse_tcp_ports,
    run_traceroute,
    unified_config_diff,
    write_config_backup,
    write_lines,
)
from utils.device_diagnostics import (
    normalize_lookup_target,
    validate_interface_name,
)


# ─────────────────────── 主题配色 ───────────────────────
class Theme:
    """AOMT aurora theme derived from the selected brand icon."""
    # 品牌色
    PRIMARY        = "#0788B5"
    PRIMARY_LIGHT  = "#E2F5F8"
    PRIMARY_DARK   = "#07566A"
    ACCENT         = "#16C7B7"
    CORAL          = "#F06449"
    
    # 背景
    BG_MAIN        = "#EAF1F2"
    BG_PANEL       = "#F9FBFA"
    BG_CARD        = "#F1F6F5"
    BG_HEADER      = "#E7F0F0"
    BG_INPUT       = "#FFFFFF"
    BG_DEEP        = "#063847"
    BG_DEEP_ALT    = "#082D3A"
    
    # 文字
    TEXT_PRIMARY   = "#12313A"
    TEXT_SECONDARY = "#45636B"
    TEXT_HINT      = "#789097"
    TEXT_WHITE     = "#F8FFFD"
    TEXT_HEADER    = "#DDF7F4"
    
    # 状态
    SUCCESS        = "#0B9F8D"
    SUCCESS_BG     = "#DDF8F2"
    WARNING        = "#D18A24"
    WARNING_BG     = "#FFF4D9"
    ERROR          = "#D95445"
    ERROR_BG       = "#FDE9E5"
    INFO           = "#0788B5"
    INFO_BG        = "#E2F5F8"
    
    # 边框
    BORDER         = "#C9DADB"
    BORDER_FOCUS   = "#16AFC2"
    
    # 按钮
    BTN_PRIMARY    = "#0788B5"
    BTN_PRIMARY_H  = "#08759A"
    BTN_SUCCESS    = "#0AA895"
    BTN_SUCCESS_H  = "#078A7B"
    BTN_DANGER     = "#D95445"
    BTN_DANGER_H   = "#BF4136"
    BTN_NEUTRAL    = "#42656E"
    BTN_NEUTRAL_H  = "#31515A"
    
    # 阴影/分割
    SHADOW         = "rgba(6,56,71,0.10)"
    DIVIDER        = "#D6E3E3"
    
    # 进度条
    PROGRESS_BG    = "#164B58"
    PROGRESS_CHUNK = "#16C7B7"

    # 表格行
    ROW_ALT        = "#F2F7F6"
    ROW_HOVER      = "#E4F4F2"
    ROW_SELECT     = "#D4F1EF"


class ModernSplitterHandle(QSplitterHandle):
    """A generous drag target with a restrained, centered visual grip."""

    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self._hovered = False
        self.setCursor(Qt.SplitHCursor if orientation == Qt.Horizontal else Qt.SplitVCursor)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(Theme.ACCENT if self._hovered else "#9CB8BB")
        center = self.rect().center()

        if self.orientation() == Qt.Horizontal:
            grip_width = 4
            grip_height = min(68, max(36, self.height() // 8))
            grip_rect = QRectF(
                center.x() - grip_width / 2,
                center.y() - grip_height / 2,
                grip_width,
                grip_height,
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(grip_rect, 2, 2)
            dot_color = QColor(Theme.BG_PANEL)
            painter.setBrush(dot_color)
            for offset in (-9, 0, 9):
                painter.drawEllipse(QPointF(center.x(), center.y() + offset), 1.2, 1.2)
        else:
            grip_width = min(68, max(36, self.width() // 8))
            grip_height = 4
            grip_rect = QRectF(
                center.x() - grip_width / 2,
                center.y() - grip_height / 2,
                grip_width,
                grip_height,
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(grip_rect, 2, 2)
        painter.end()


class ModernSplitter(QSplitter):
    def createHandle(self):
        return ModernSplitterHandle(self.orientation(), self)


def make_icon(color: str, shape: str = "circle") -> QIcon:
    """动态生成简单图标"""
    pix = QPixmap(24, 24)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.NoPen)
    if shape == "circle":
        painter.drawEllipse(2, 2, 20, 20)
    elif shape == "rect":
        painter.drawRoundedRect(2, 2, 20, 20, 4, 4)
    painter.end()
    return QIcon(pix)


def build_app_icon() -> QIcon:
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "app.ico"))
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "app.ico"))

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.extend([
        os.path.join(project_root, "app.ico"),
        os.path.join(os.getcwd(), "app.ico"),
    ])

    for icon_path in candidates:
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            if not icon.isNull():
                return icon
    """构建应用程序图标（网络/交换机样式）"""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    # 背景圆角矩形渐变
    grad = QLinearGradient(0, 0, 64, 64)
    grad.setColorAt(0.0, QColor("#1565C0"))
    grad.setColorAt(1.0, QColor("#00BCD4"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 12, 12)
    # 绘制网络节点
    p.setBrush(QBrush(QColor("#FFFFFF")))
    nodes = [(32, 16), (16, 40), (48, 40)]
    for nx, ny in nodes:
        p.drawEllipse(nx - 5, ny - 5, 10, 10)
    p.setPen(QPen(QColor("#FFFFFF"), 2))
    for nx, ny in nodes[1:]:
        p.drawLine(32, 16, nx, ny)
    p.drawLine(16, 40, 48, 40)
    p.end()
    return QIcon(pix)


# ─────────────────────── 样式表 ───────────────────────
APP_STYLE = f"""
/* 全局  10pt → 13px (96dpi) */
QMainWindow, QWidget {{
    background-color: {Theme.BG_MAIN};
    color: {Theme.TEXT_PRIMARY};
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QWidget#app_root, QWidget#workspace_body {{
    background-color: {Theme.BG_MAIN};
}}
QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QToolTip {{
    color: {Theme.TEXT_WHITE};
    background-color: {Theme.BG_DEEP};
    border: 1px solid #1A6674;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    font-weight: 400;
}}

/* GroupBox */
QGroupBox {{
    background-color: {Theme.BG_PANEL};
    border: 1px solid {Theme.BORDER};
    border-radius: 7px;
    margin-top: 15px;
    padding: 14px 11px 11px 11px;
    font-size: 13px;
    font-weight: 600;
    color: {Theme.TEXT_PRIMARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 1px 9px;
    left: 10px;
    color: {Theme.PRIMARY_DARK};
    background-color: {Theme.BG_PANEL};
    font-size: 13px;
    font-weight: 700;
}}
QGroupBox#device_list_group,
QGroupBox#connection_log_group {{
    background: transparent;
}}
QGroupBox#device_list_group {{
    border-top: 2px solid {Theme.PRIMARY};
}}
QGroupBox#connection_log_group {{
    border-top: 2px solid {Theme.ACCENT};
}}
QGroupBox#device_list_group::title,
QGroupBox#connection_log_group::title {{
    background-color: {Theme.BG_MAIN};
}}

/* 输入框 */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {Theme.BG_INPUT};
    border: 1px solid {Theme.BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    color: {Theme.TEXT_PRIMARY};
    min-height: 28px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {Theme.BORDER_FOCUS};
    background-color: #FFFFFF;
}}
QLineEdit::placeholder {{
    color: {Theme.TEXT_HINT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    border: 1px solid {Theme.BORDER};
    border-radius: 5px;
    background: {Theme.BG_PANEL};
    selection-background-color: {Theme.ROW_SELECT};
    selection-color: {Theme.PRIMARY_DARK};
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    border: none;
    background: transparent;
    width: 16px;
}}

/* 通用按钮基类 */
QPushButton {{
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
    min-height: 30px;
    cursor: pointer;
}}
QPushButton:disabled {{
    background-color: #DDE7E7;
    color: #8AA0A4;
}}

/* 主操作按钮 */
QPushButton#btn_primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Theme.PRIMARY_DARK}, stop:0.55 {Theme.BTN_PRIMARY}, stop:1 #16AFC2);
    color: white;
}}
QPushButton#btn_primary:hover {{
    background-color: {Theme.BTN_PRIMARY_H};
}}
QPushButton#btn_primary:pressed {{
    background-color: {Theme.PRIMARY_DARK};
}}

/* 成功按钮（开始连接） */
QPushButton#btn_success {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #087B72, stop:0.5 {Theme.BTN_SUCCESS}, stop:1 {Theme.ACCENT});
    color: white;
    font-size: 13px;
    min-height: 36px;
    border-radius: 6px;
    letter-spacing: 0px;
}}
QPushButton#btn_success:hover {{
    background-color: {Theme.BTN_SUCCESS_H};
}}
QPushButton#btn_success:pressed {{
    background-color: #066B63;
}}

/* 危险按钮（清空） */
QPushButton#btn_danger {{
    background-color: {Theme.ERROR_BG};
    color: {Theme.BTN_DANGER};
    border: 1px solid #E9A79E;
}}
QPushButton#btn_danger:hover {{
    background-color: {Theme.BTN_DANGER_H};
    color: white;
}}

/* 中性按钮 */
QPushButton#btn_neutral {{
    background-color: {Theme.BTN_NEUTRAL};
    color: white;
}}
QPushButton#btn_neutral:hover {{
    background-color: {Theme.BTN_NEUTRAL_H};
}}

/* 轮廓按钮 */
QPushButton#btn_outline {{
    background-color: {Theme.BG_PANEL};
    color: {Theme.PRIMARY_DARK};
    border: 1px solid #75B9C4;
}}
QPushButton#btn_outline:hover {{
    background-color: {Theme.INFO_BG};
    border-color: {Theme.PRIMARY};
}}

QCheckBox {{
    color: {Theme.TEXT_SECONDARY};
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border: 1px solid #8FA8AD;
    border-radius: 4px;
    background: {Theme.BG_INPUT};
}}
QCheckBox::indicator:hover {{
    border-color: {Theme.ACCENT};
}}
QCheckBox::indicator:checked {{
    background-color: {Theme.ACCENT};
    border-color: {Theme.ACCENT};
}}

/* 表格 */
QTableWidget {{
    background-color: {Theme.BG_PANEL};
    border: 1px solid {Theme.BORDER};
    border-radius: 7px;
    gridline-color: {Theme.DIVIDER};
    alternate-background-color: {Theme.ROW_ALT};
    selection-background-color: {Theme.ROW_SELECT};
    selection-color: {Theme.PRIMARY_DARK};
    font-size: 13px;
    outline: none;
}}
QTableWidget::item {{
    padding: 7px 10px;
    border-bottom: 1px solid {Theme.BORDER};
}}
QTableWidget::item:hover {{
    background-color: {Theme.ROW_HOVER};
}}
QHeaderView::section {{
    background-color: {Theme.BG_DEEP};
    color: {Theme.TEXT_HEADER};
    font-weight: 700;
    font-size: 13px;
    padding: 9px 10px;
    border: none;
    border-bottom: 1px solid #0C5261;
    border-right: 1px solid #164E5A;
}}
QHeaderView::section:first {{
    border-top-left-radius: 8px;
}}
QHeaderView::section:last {{
    border-top-right-radius: 8px;
    border-right: none;
}}

/* 日志文本 */
QTextEdit {{
    background-color: {Theme.BG_DEEP_ALT};
    color: #D6F2EF;
    border: 1px solid #155565;
    border-radius: 7px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 9px;
    selection-background-color: #087E91;
}}

/* 进度条 */
QProgressBar {{
    background-color: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 5px;
    height: 12px;
    text-align: center;
    font-size: 12px;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Theme.PRIMARY}, stop:1 {Theme.ACCENT});
    border-radius: 5px;
}}

/* 状态栏 */
QStatusBar {{
    background-color: {Theme.BG_DEEP};
    color: rgba(248,255,253,0.88);
    font-size: 12px;
    padding: 7px 12px;
    min-height: 38px;
    border-top: 1px solid #0C5261;
}}
QStatusBar::item {{
    border: none;
}}

/* 标签 */
QLabel#section_title {{
    color: {Theme.PRIMARY_DARK};
    font-size: 13px;
    font-weight: 700;
}}
QLabel#field_label {{
    color: {Theme.TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
    padding: 0;
    margin: 0;
}}

/* 分割线 */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {Theme.DIVIDER};
}}

/* 滚动条 */
QScrollBar:vertical {{
    background: rgba(156,184,187,0.16);
    width: 7px;
    margin: 2px 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: #AFC7C9;
    border-radius: 3px;
    min-height: 44px;
    margin: 0 1px;
}}
QScrollBar::handle:vertical:hover {{
    background: {Theme.ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: rgba(156,184,187,0.16);
    height: 7px;
    margin: 0 2px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: #AFC7C9;
    border-radius: 3px;
    min-width: 44px;
    margin: 1px 0;
}}
QScrollBar::handle:horizontal:hover {{
    background: {Theme.ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* Splitter */
QSplitter::handle {{
    background: transparent;
}}

QListWidget {{
    background-color: {Theme.BG_CARD};
    border: 1px solid {Theme.BORDER};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
    color: {Theme.TEXT_PRIMARY};
}}
QListWidget::item:hover {{
    background-color: {Theme.ROW_HOVER};
}}
QListWidget::item:selected {{
    background-color: {Theme.ROW_SELECT};
    color: {Theme.PRIMARY_DARK};
}}

/* MessageBox */
QMessageBox {{
    background-color: {Theme.BG_PANEL};
}}
QMessageBox QPushButton {{
    min-width: 80px;
    background-color: {Theme.BTN_PRIMARY};
    color: white;
}}
QMessageBox QPushButton:hover {{
    background-color: {Theme.BTN_PRIMARY_H};
}}
"""


class AuroraHeader(QWidget):
    """Paints the restrained data-flow header used by the AOMT brand."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aurora_header")
        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        background = QLinearGradient(0, 0, self.width(), 0)
        background.setColorAt(0.0, QColor("#063847"))
        background.setColorAt(0.58, QColor("#075466"))
        background.setColorAt(1.0, QColor("#083D52"))
        painter.fillRect(self.rect(), background)

        width = max(1, self.width())
        height = max(1, self.height())

        main_flow = QPainterPath()
        main_flow.moveTo(width * 0.47, height * 1.08)
        main_flow.cubicTo(
            width * 0.60, height * 0.85,
            width * 0.68, height * 0.08,
            width * 0.86, height * -0.10,
        )
        flow_gradient = QLinearGradient(width * 0.48, height, width * 0.87, 0)
        flow_gradient.setColorAt(0.0, QColor(19, 198, 181, 72))
        flow_gradient.setColorAt(0.55, QColor(13, 177, 201, 108))
        flow_gradient.setColorAt(1.0, QColor(27, 116, 219, 82))
        painter.setPen(QPen(QBrush(flow_gradient), max(18, int(height * 0.34)),
                            Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(main_flow)

        light_flow = QPainterPath()
        light_flow.moveTo(width * 0.58, height * 1.06)
        light_flow.cubicTo(
            width * 0.69, height * 0.67,
            width * 0.75, height * 0.22,
            width * 0.94, height * 0.02,
        )
        painter.setPen(QPen(QColor(139, 240, 230, 42), 2.0,
                            Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(light_flow)

        painter.end()


# ─────────────────────── 状态标签组件 ───────────────────────
class StatusBadge(QLabel):
    """彩色状态徽章（建议4：作为 cell widget 嵌入表格状态列）

    支持状态：待连接 / 连接中 / 连接成功(✔) / 连接失败(✘)
    """
    _STYLES = {
        "待连接":  (Theme.TEXT_SECONDARY, "#DDE8E8"),
        "连接成功": (Theme.SUCCESS,        Theme.SUCCESS_BG),
        "✔":      (Theme.SUCCESS,        Theme.SUCCESS_BG),
        "连接中":  (Theme.WARNING,         Theme.WARNING_BG),
        "⏳":     (Theme.WARNING,         Theme.WARNING_BG),
    }

    def __init__(self, text: str, parent=None, font_px: int = 14):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self._font_px = font_px
        self._set_style(text)

    def setText(self, text: str):
        super().setText(text)
        self._set_style(text)

    def set_font_size(self, font_px: int):
        self._font_px = max(12, int(font_px))
        self._set_style(self.text())

    def _set_style(self, text: str):
        color, bg = Theme.TEXT_SECONDARY, "#DDE8E8"
        for key, (c, b) in self._STYLES.items():
            if text.startswith(key):
                color, bg = c, b
                break
        if "✘" in text or "失败" in text or "错误" in text:
            color, bg = Theme.ERROR, Theme.ERROR_BG
        self.setStyleSheet(
            f"color: {color}; background-color: {bg}; border-radius: 8px;"
            f"margin: 4px 6px; padding: 1px 8px; min-height: 20px;"
            f"font-size: {self._font_px}px; font-weight: 600;"
        )


# ─────────────────────── 工作线程 ───────────────────────
class ConnectionWorker(QThread):
    """连接工作线程

    修复说明：
    - 新增 device_status_signal：每台设备完成后立即 emit，实现逐设备实时刷新（建议2）
    - result_signal 保留，用于传递完整结构化结果（型号/品牌填充）
    """

    progress_signal      = pyqtSignal(str)
    finished_signal      = pyqtSignal()
    result_signal        = pyqtSignal(dict)
    # 建议2：逐设备实时状态信号 (ip, status_text, is_success, brand, model)
    device_status_signal = pyqtSignal(str, str, bool, str, str)

    def __init__(self, ssh_manager, device_infos):
        super().__init__()
        self.ssh_manager  = ssh_manager
        self.device_infos = device_infos
        self.logger       = None

    def set_logger(self, logger):
        self.logger = logger
        self.ssh_manager.logger = logger

    def run(self):
        self.ssh_manager.add_devices(self.device_infos)
        self.ssh_manager.set_progress_callback(
            lambda msg: self.progress_signal.emit(msg)
        )
        # 建议2：注册逐设备完成回调，每台完成立即通知主线程
        self.ssh_manager.set_device_done_callback(self._on_device_done)
        self.ssh_manager.start_connections()
        self.ssh_manager.wait_for_completion()
        self.finished_signal.emit()

    def _on_device_done(self, result: dict):
        """SSHManager 每台设备完成时的回调（在工作线程中执行，通过信号转发到主线程）"""
        self.result_signal.emit(result)
        device_info   = result.get("device_info", {})
        is_connected  = result.get("is_connected", False)
        error_message = result.get("error_message", "") or ""
        ip            = device_info.get("ip", "")
        brand         = result.get("brand_detected", "") or ""
        model         = result.get("model_detected", "") or ""

        if is_connected:
            status_text = f"✔ 成功  {brand}" if brand else "✔ 连接成功"
        else:
            # 截断错误信息，避免状态列过宽
            short_err = error_message[:30] + "..." if len(error_message) > 30 else error_message
            status_text = f"✘ {short_err}"

        self.device_status_signal.emit(ip, status_text, is_connected, brand, model)


class PingWorker(QThread):
    """批量 Ping 工作线程，避免阻塞界面。"""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int, int)

    def __init__(self, ips: List[str]):
        super().__init__()
        self.ips = ips
        self._is_windows = sys.platform.startswith("win")

    def run(self):
        success = 0
        failure = 0
        total = len(self.ips)

        max_workers = min(32, max(1, total))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._ping, ip): ip
                for ip in self.ips
            }
            for index, future in enumerate(as_completed(futures), start=1):
                ip = futures[future]
                try:
                    ok, detail = future.result()
                except Exception as exc:
                    ok, detail = False, f"执行失败: {exc}"
                if ok:
                    success += 1
                    self.progress_signal.emit(
                        f"[Ping] ({index}/{total}) {ip} 可达，响应正常"
                    )
                else:
                    failure += 1
                    self.progress_signal.emit(
                        f"[Ping] ({index}/{total}) {ip} 不可达，{detail}"
                    )

        self.finished_signal.emit(total, success, failure)

    def _ping(self, ip: str) -> tuple:
        if self._is_windows:
            cmd = ["ping", "-n", "1", "-w", "1000", ip]
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            cmd = ["ping", "-c", "1", "-W", "1", ip]
            creationflags = 0

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=creationflags,
            )
            if result.returncode == 0:
                return True, ""
            output = (result.stdout or result.stderr or "").strip().splitlines()
            detail = output[-1] if output else "无响应或超时"
            return False, detail
        except subprocess.TimeoutExpired:
            return False, "请求超时"
        except Exception as exc:
            return False, f"执行失败: {exc}"


class MaintenanceWorker(QThread):
    """Run batch maintenance checks without blocking the UI thread."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, int, int, int)

    def __init__(self, mode: str, devices: List, options=None, logger=None):
        super().__init__()
        self.mode = mode
        self.devices = list(devices)
        self.options = options or {}
        self.logger = logger

    def run(self):
        if self.mode == "port":
            tasks = [
                (device, port)
                for device in self.devices
                for port in self.options.get("ports", [])
            ]
            self._run_parallel(tasks, self._check_port, max_workers=10)
        elif self.mode == "ssh_login":
            self._run_parallel(self.devices, self._test_ssh_login, max_workers=5)
        elif self.mode == "traceroute":
            self._run_parallel(self.devices, self._trace_device, max_workers=3)
        elif self.mode == "backup":
            self._run_parallel(self.devices, self._backup_config, max_workers=5)
        else:
            self.finished_signal.emit(self.mode, 0, 0, 0)

    def _run_parallel(self, tasks, handler, max_workers: int):
        total = len(tasks)
        success = 0
        failure = 0
        if not tasks:
            self.finished_signal.emit(self.mode, 0, 0, 0)
            return

        with ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
            futures = {executor.submit(handler, task): task for task in tasks}
            for index, future in enumerate(as_completed(futures), start=1):
                try:
                    ok, message = future.result()
                except Exception as exc:
                    ok, message = False, f"任务异常: {exc}"
                success += int(ok)
                failure += int(not ok)
                self.progress_signal.emit(f"({index}/{total}) {message}")

        self.finished_signal.emit(self.mode, total, success, failure)

    @staticmethod
    def _device_label(device) -> str:
        name = str(getattr(device, "name", "") or "").strip()
        ip = str(getattr(device, "ip", "") or "").strip()
        return f"{name} [{ip}]" if name else ip

    def _check_port(self, task):
        device, port = task
        ip = str(getattr(device, "ip", "") or "")
        ok, detail = check_tcp_port(ip, port)
        state = "开放" if ok else "不可用"
        return ok, f"[端口检测] {self._device_label(device)} TCP/{port} {state}，{detail}"

    def _test_ssh_login(self, device):
        client = paramiko.SSHClient()
        policy = normalize_host_key_policy(
            getattr(device, "host_key_policy", "tofu")
        )
        known_hosts_path = configure_host_key_policy(client, policy)
        try:
            kwargs = build_connect_kwargs(
                device, normalize_host(getattr(device, "ip", ""))
            )
            kwargs.update(timeout=10, banner_timeout=10, auth_timeout=10)
            client.connect(**kwargs)
            persist_host_keys(client, policy, known_hosts_path)
            transport = client.get_transport()
            if not transport or not transport.is_active():
                return False, f"[SSH 登录] {self._device_label(device)} 会话未激活"
            return True, f"[SSH 登录] {self._device_label(device)} 认证成功，未执行设备命令"
        except paramiko.AuthenticationException:
            return False, f"[SSH 登录] {self._device_label(device)} 认证失败"
        except paramiko.SSHException as exc:
            return False, f"[SSH 登录] {self._device_label(device)} SSH 协议错误: {exc}"
        except OSError as exc:
            return False, f"[SSH 登录] {self._device_label(device)} 连接失败: {exc}"
        finally:
            client.close()

    def _trace_device(self, device):
        ip = str(getattr(device, "ip", "") or "")
        ok, output = run_traceroute(ip)
        state = "完成" if ok else "失败"
        return ok, f"[路由跟踪] {self._device_label(device)} {state}\n{output}"

    def _backup_config(self, device):
        connection = SSHConnection(device, self.logger)
        try:
            if not connection.connect():
                return False, (
                    f"[配置备份] {self._device_label(device)} 连接失败: "
                    f"{connection.error_message or '未知错误'}"
                )

            brand = connection.brand_detected or getattr(device, "brand", "") or "h3c"
            command = get_command(brand, "display_config")
            output = connection.execute_command(command, sleep_time=0.5)
            if not output or re.search(
                r"%\s*Invalid|Unrecognized command|命令执行失败|Error:",
                output,
                re.IGNORECASE,
            ):
                return False, (
                    f"[配置备份] {self._device_label(device)} 未获得有效配置，"
                    f"实际查询命令: {command}"
                )

            config_text = normalize_device_config(output, command)
            if not config_text:
                return False, (
                    f"[配置备份] {self._device_label(device)} 清理终端信息后"
                    "没有可保存的配置内容"
                )

            output_dir = self.options["output_dir"]
            device_name = getattr(device, "name", "") or getattr(device, "ip", "")
            config_path, metadata_path = write_config_backup(
                output_dir,
                device_name=device_name,
                device_ip=getattr(device, "ip", ""),
                device_port=getattr(device, "port", 22),
                brand=brand,
                command=command,
                config_text=config_text,
            )
            return True, (
                f"[配置备份] {self._device_label(device)} 已保存配置: "
                f"{config_path}；元数据: {metadata_path}"
            )
        finally:
            connection.disconnect()


# ─────────────────────── 主窗口 ───────────────────────
class MainWindow(QMainWindow):
    """主窗口 - 现代化 UI"""

    # 字体缩放锚点：(窗口宽度, pt字号)
    _FONT_ANCHORS = [(1024, 13), (1280, 14), (1600, 16), (1920, 17)]

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_SHORT_NAME} v{APP_VERSION}")
        self.setMinimumSize(1024, 768)
        self.resize(2560, 1600)
        self.setWindowIcon(build_app_icon())

        # 初始化管理器
        self.device_manager    = DeviceConfigManager()
        self.ssh_manager       = SSHManager(max_connections=5)
        self.logger            = ConnectionLogger()
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
        self._current_font_pt  = 14     # 当前字号，防止重复刷新
        self._form_labels      = []
        self._template_store_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "operation_templates.json",
        )
        self._config_templates = []
        self.execution_results = []
        self._serial_console = None
        self._ssh_console = None
        self._file_transfer_dialog = None
        self._packet_capture_dialog = None

        # 应用样式
        self.setStyleSheet(APP_STYLE)

        self.init_ui()
        self._init_statusbar()
        self._load_config_templates()
        self._apply_font_pt(self._calc_font_pt(self.width()))

    # ── 动态字体缩放 ────────────────────────────────────
    @staticmethod
    def _calc_font_pt(width: int) -> int:
        """根据窗口宽度线性插值计算字号（pt）"""
        anchors = MainWindow._FONT_ANCHORS
        if width <= anchors[0][0]:
            return anchors[0][1]
        if width >= anchors[-1][0]:
            return anchors[-1][1]
        for i in range(len(anchors) - 1):
            w0, f0 = anchors[i]
            w1, f1 = anchors[i + 1]
            if w0 <= width <= w1:
                ratio = (width - w0) / (w1 - w0)
                return round(f0 + ratio * (f1 - f0))
        return 10

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
            max_width = max(
                CollapsibleSidebar.MIN_EXPANDED_WIDTH,
                self.width() // 2,
            )
            self._left_panel.set_expanded_maximum_width(max_width)
            if not self._left_panel.is_expanded():
                return
        else:
            max_width = max(360, self.width() // 2)
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
            max_width = max(
                CollapsibleSidebar.MIN_EXPANDED_WIDTH,
                self.width() // 2,
            )
            target_width = min(
                max(CollapsibleSidebar.MIN_EXPANDED_WIDTH, int(total * 0.30)),
                max_width,
            )
        else:
            target_width = CollapsibleSidebar.COLLAPSED_WIDTH
        self._main_splitter.setSizes([
            target_width,
            max(1, total - target_width),
        ])
        QTimer.singleShot(0, self._update_ops_tools_columns)

    def _update_ops_tools_columns(self):
        if not hasattr(self, '_ops_tools_layout') or not hasattr(self, '_left_panel'):
            return
        columns = 2 if self._left_panel.is_expanded() and self._left_panel.width() >= 660 else 1
        if getattr(self, '_ops_tools_columns', None) == columns:
            return
        self._ops_tools_columns = columns
        for button in self._ops_tool_buttons:
            self._ops_tools_layout.removeWidget(button)
        for index, button in enumerate(self._ops_tool_buttons):
            row, column = divmod(index, columns)
            self._ops_tools_layout.addWidget(button, row, column)
        for column in range(2):
            self._ops_tools_layout.setColumnStretch(column, 1 if column < columns else 0)
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
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        sb.setMinimumHeight(52)
        self.setStatusBar(sb)

        # 左侧固定标题（永不改变）
        self._status_label = QLabel(
            f"{APP_NAME}  |  版本 v{APP_VERSION}  |  作者：{APP_AUTHOR}"
        )
        self._status_label.setContentsMargins(4, 4, 4, 4)
        self._status_label.setStyleSheet("color: rgba(255,255,255,0.75); background: transparent;")
        sb.addWidget(self._status_label)

        # 右侧进度条（平时隐藏，仅工作期间显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedSize(120, 12)
        self.progress_bar.setTextVisible(False)
        sb.addPermanentWidget(self.progress_bar)

        # 右侧动态状态/设备数标签
        self._device_count_label = QLabel("设备数: 0")
        self._device_count_label.setContentsMargins(4, 4, 4, 4)
        self._device_count_label.setStyleSheet(
            "color: rgba(255,255,255,0.75); background: transparent; margin-right: 8px;"
        )
        sb.addPermanentWidget(self._device_count_label)

    def _set_status(self, text: str):
        """更新右侧动态状态标签；左侧固定标题不受影响"""
        self._device_count_label.setText(text)

    def _show_progress(self):
        """显示进度条，仅在连接工作开始时调用"""
        self.progress_bar.setVisible(True)

    def _hide_progress(self):
        """隐藏进度条，任务结束后调用"""
        self.progress_bar.setVisible(False)

    def _update_device_count(self):
        n = len(self.device_manager.get_devices())
        self._device_count_label.setText(f"设备数: {n}")

    # ── 主布局 ───────────────────────────────────────────
    def init_ui(self):
        central = QWidget()
        central.setObjectName("app_root")
        self.setCentralWidget(central)

        # 顶部标题栏
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        header = self._build_header()
        root_layout.addWidget(header)

        # 主体内容
        body = QWidget()
        body.setObjectName("workspace_body")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(14, 14, 14, 14)
        body_layout.setSpacing(14)

        splitter = ModernSplitter(Qt.Horizontal)
        splitter.setHandleWidth(12)
        splitter.setChildrenCollapsible(False)

        left_panel  = self.create_left_panel()
        right_panel = self.create_right_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([CollapsibleSidebar.COLLAPSED_WIDTH, 1132])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self._main_splitter = splitter
        self._left_panel = left_panel
        left_panel.expansionChanged.connect(self._on_left_sidebar_expansion_changed)
        splitter.splitterMoved.connect(lambda *_: self._update_ops_tools_columns())
        self._update_left_panel_limit()

        body_layout.addWidget(splitter)
        root_layout.addWidget(body)

    def _build_header(self) -> QWidget:
        """AOMT brand header with the selected aurora data-flow language."""
        header = AuroraHeader()
        header.setFixedHeight(84)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(16)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(56, 56)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        icon_lbl.setPixmap(
            build_app_icon().pixmap(52, 52, QIcon.Normal, QIcon.On)
        )
        hl.addWidget(icon_lbl)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFixedHeight(42)
        separator.setStyleSheet("color: rgba(221,247,244,0.26); background: transparent;")
        hl.addWidget(separator)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        self._title_lbl = QLabel(APP_NAME)
        self._title_lbl.setStyleSheet(
            f"color: {Theme.TEXT_WHITE}; font-size: 21px; font-weight: 700; "
            "letter-spacing: 0px; background: transparent;"
        )
        self._subtitle_lbl = QLabel("NETWORK OPERATIONS CONSOLE")
        self._subtitle_lbl.setStyleSheet(
            "color: rgba(221,247,244,0.66); font-size: 12px; background: transparent;"
        )
        title_layout.addWidget(self._title_lbl)
        title_layout.addWidget(self._subtitle_lbl)
        hl.addLayout(title_layout)
        hl.addStretch()
        return header

    # ── 左侧面板 ─────────────────────────────────────────
    def create_left_panel(self) -> QWidget:
        sidebar = CollapsibleSidebar(self._sidebar_icon_directory())
        pages = (
            (
                "devices",
                "设备管理",
                "devices.svg",
                (self._build_input_group(), self._build_excel_group()),
            ),
            (
                "tasks",
                "执行任务",
                "terminal-window.svg",
                (self._build_command_group(), self._build_action_group()),
            ),
            (
                "tools",
                "运维工具",
                "toolbox.svg",
                (self._build_ops_tools_group(),),
            ),
            (
                "templates",
                "配置模板",
                "files.svg",
                (self._build_config_templates_group(),),
            ),
        )
        for key, title, icon_filename, groups in pages:
            sidebar.add_page(
                key,
                title,
                icon_filename,
                self._build_sidebar_page(groups),
            )
        self._left_content = sidebar
        return sidebar

    @staticmethod
    def _sidebar_icon_directory() -> Path:
        relative = Path("assets") / "icons" / "phosphor"
        candidates = [
            Path(__file__).resolve().parent.parent / relative,
            Path(sys.executable).resolve().parent / relative,
            Path.cwd() / relative,
        ]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0]

    @staticmethod
    def _build_sidebar_page(groups) -> QWidget:
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

    def _build_input_group(self) -> QGroupBox:
        group = QGroupBox("添加设备")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)
        form.setColumnMinimumWidth(0, 0)
        form.setColumnStretch(0, 0)
        form.setColumnStretch(1, 1)

        def add_form_row(row_index, label_text, widget):
            lbl = self._create_form_label(label_text)
            widget.setSizePolicy(QSizePolicy.Expanding, widget.sizePolicy().verticalPolicy())
            form.addWidget(lbl, row_index, 0)
            form.addWidget(widget, row_index, 1)

        # 设备名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如：SW1")
        add_form_row(0, "名 称:", self.name_input)

        # 品牌
        self.brand_combo = QComboBox()
        self.brand_combo.addItems(["H3C", "Huawei", "Ruijie", "Cisco", "TP-Link"])
        add_form_row(1, "品 牌:", self.brand_combo)

        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("例如：核心交换机")
        add_form_row(2, "分 组:", self.group_input)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("例如：机房A,核心")
        add_form_row(3, "标 签:", self.tags_input)

        # IP
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.1  或  2001:db8::1")
        add_form_row(4, "IP 地址:", self.ip_input)

        # 端口
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        add_form_row(5, "端 口:", self.port_spin)

        # 用户名
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("admin")
        add_form_row(6, "用户名:", self.username_input)

        self.auth_method_combo = QComboBox()
        self.auth_method_combo.addItem("密码认证", "password")
        self.auth_method_combo.addItem("私钥认证", "key")
        self.auth_method_combo.currentIndexChanged.connect(
            self._update_auth_fields
        )
        add_form_row(7, "认 证:", self.auth_method_combo)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_label = self._create_form_label("密 码:")
        form.addWidget(self.password_label, 8, 0)
        form.addWidget(self.password_input, 8, 1)

        self.private_key_row = QWidget()
        key_layout = QHBoxLayout(self.private_key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(6)
        self.private_key_input = QLineEdit()
        self.private_key_input.setPlaceholderText("选择 OpenSSH/PEM 私钥")
        key_button = QPushButton("…")
        key_button.setFixedWidth(42)
        key_button.setToolTip("选择 SSH 私钥文件")
        key_button.clicked.connect(self.browse_private_key)
        key_layout.addWidget(self.private_key_input, 1)
        key_layout.addWidget(key_button)
        self.private_key_label = self._create_form_label("私 钥:")
        form.addWidget(self.private_key_label, 9, 0)
        form.addWidget(self.private_key_row, 9, 1)

        self.key_passphrase_input = QLineEdit()
        self.key_passphrase_input.setEchoMode(QLineEdit.Password)
        self.key_passphrase_input.setPlaceholderText("私钥无口令可留空")
        self.key_passphrase_label = self._create_form_label("口 令:")
        form.addWidget(self.key_passphrase_label, 10, 0)
        form.addWidget(self.key_passphrase_input, 10, 1)

        self.host_key_policy_combo = QComboBox()
        self.host_key_policy_combo.addItem("首次信任，后续校验", "tofu")
        self.host_key_policy_combo.addItem("严格校验", "strict")
        self.host_key_policy_combo.addItem("不校验（不推荐）", "insecure")
        add_form_row(11, "主机键:", self.host_key_policy_combo)

        layout.addLayout(form)
        self._update_auth_fields()

        # 添加按钮
        self.add_btn = QPushButton("＋  添加设备")
        self.add_btn.setObjectName("btn_primary")
        self.add_btn.clicked.connect(self.add_device)
        layout.addWidget(self.add_btn)

        return group

    def _build_excel_group(self) -> QGroupBox:
        group = QGroupBox("批量导入")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.import_btn = QPushButton("📂  导入 Excel 文件")
        self.import_btn.setObjectName("btn_outline")
        self.import_btn.clicked.connect(self.import_excel)
        layout.addWidget(self.import_btn)

        self.encrypt_excel_btn = QPushButton("🔒  加密 Excel 认证信息")
        self.encrypt_excel_btn.setObjectName("btn_outline")
        self.encrypt_excel_btn.clicked.connect(self.encrypt_excel_passwords)
        layout.addWidget(self.encrypt_excel_btn)

        self.template_btn = QPushButton("⬇  下载 Excel 模板")
        self.template_btn.setObjectName("btn_outline")
        self.template_btn.clicked.connect(self.download_template)
        layout.addWidget(self.template_btn)

        return group

    def _build_command_group(self) -> QGroupBox:
        """命令文件选择区"""
        group = QGroupBox("业务命令文件")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        mode_row = QGridLayout()
        mode_row.setColumnStretch(1, 1)
        mode_row.addWidget(self._create_form_label("模式:"), 0, 0)
        self.cmd_mode_combo = QComboBox()
        self.cmd_mode_combo.addItem("统一脚本", "single")
        self.cmd_mode_combo.addItem("按设备匹配", "per_device")
        self.cmd_mode_combo.currentIndexChanged.connect(self.on_command_mode_changed)
        mode_row.addWidget(self.cmd_mode_combo, 0, 1)
        layout.addLayout(mode_row)

        # 当前文件路径显示
        path_row = QGridLayout()
        path_row.setHorizontalSpacing(8)
        path_row.setVerticalSpacing(8)
        path_row.setColumnStretch(0, 0)
        path_row.setColumnStretch(1, 1)
        path_lbl = self._create_form_label("文件:")
        self.cmd_file_label = QLabel("SSH_command.txt  (默认)")
        self.cmd_file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.cmd_file_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: 12px; "
            f"background: {Theme.BG_CARD}; border: 1px solid {Theme.BORDER}; "
            f"border-radius: 4px; padding: 4px 6px;"
        )
        self.cmd_file_label.setWordWrap(True)
        path_row.addWidget(path_lbl, 0, 0)
        path_row.addWidget(self.cmd_file_label, 0, 1)
        layout.addLayout(path_row)

        # 按钮行
        btn_row = QHBoxLayout()
        self.cmd_browse_btn = QPushButton("📄  选择文件")
        self.cmd_browse_btn.setObjectName("btn_outline")
        self.cmd_browse_btn.clicked.connect(self.browse_command_file)

        self.cmd_reset_btn = QPushButton("↺  恢复默认")
        self.cmd_reset_btn.setObjectName("btn_neutral")
        self.cmd_reset_btn.clicked.connect(self.reset_command_file)

        btn_row.addWidget(self.cmd_browse_btn)
        btn_row.addWidget(self.cmd_reset_btn)
        layout.addLayout(btn_row)

        # 提示文字
        self._cmd_tip_label = QLabel("命令原样发送；每行一条，# 开头为注释")
        self._cmd_tip_label.setStyleSheet(f"color: {Theme.TEXT_HINT}; font-size: 16px;")
        layout.addWidget(self._cmd_tip_label)

        return group

    def _build_action_group(self) -> QGroupBox:
        group = QGroupBox("操作")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # ── 运维选项（借鉴 w-sw-ssh --save 和 --l2_sw）────
        opt_row1 = QHBoxLayout()
        self.save_check = QCheckBox("执行后保存配置")
        self.save_check.setToolTip("连接成功并执行命令后自动执行 save/write 保存配置（对应 w-sw-ssh --save）")
        self.save_check.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 12px;")
        opt_row1.addWidget(self.save_check)
        opt_row1.addStretch()
        layout.addLayout(opt_row1)

        opt_row2 = QHBoxLayout()
        self.l2_uplink_check = QCheckBox("探测二层上联口")
        self.l2_uplink_check.setToolTip(
            "通过 路由表→ARP→MAC表 三步查询探测上联端口（移植自 w-sw-ssh --l2_sw）"
        )
        self.l2_uplink_check.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 12px;")
        opt_row2.addWidget(self.l2_uplink_check)
        opt_row2.addStretch()
        layout.addLayout(opt_row2)

        # 分割线
        sep0 = QFrame()
        sep0.setFrameShape(QFrame.HLine)
        sep0.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep0)

        # 开始连接
        self.connect_btn = QPushButton("▶  开始连接")
        self.connect_btn.setObjectName("btn_success")
        self.connect_btn.clicked.connect(self.start_connection)
        layout.addWidget(self.connect_btn)

        # 进度条已移至状态栏（_init_statusbar），此处无需再添加

        # 分割线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # 移除选中 / 清空 / 日志
        hl1 = QHBoxLayout()
        self.delete_btn = QPushButton("✂  移除选中")
        self.delete_btn.setObjectName("btn_neutral")
        self.delete_btn.clicked.connect(self.delete_selected_device)

        self.clear_btn = QPushButton("🗑  清空列表")
        self.clear_btn.setObjectName("btn_danger")
        self.clear_btn.clicked.connect(self.clear_devices)
        hl1.addWidget(self.delete_btn)
        hl1.addWidget(self.clear_btn)
        layout.addLayout(hl1)

        log_row = QHBoxLayout()
        self.log_btn = QPushButton("📋  查看日志")
        self.log_btn.setObjectName("btn_neutral")
        self.log_btn.clicked.connect(self.view_logs)

        self.clear_log_btn = QPushButton("🧹  清空日志")
        self.clear_log_btn.setObjectName("btn_outline")
        self.clear_log_btn.clicked.connect(self.clear_connection_log)

        log_row.addWidget(self.log_btn)
        log_row.addWidget(self.clear_log_btn)
        layout.addLayout(log_row)

        self.result_center_btn = QPushButton("▤  执行结果中心")
        self.result_center_btn.setObjectName("btn_outline")
        self.result_center_btn.setToolTip("按设备查看完整命令输出、耗时与错误，并导出结果")
        self.result_center_btn.clicked.connect(self.open_result_center)
        layout.addWidget(self.result_center_btn)

        return group

    def _build_ops_tools_group(self) -> QGroupBox:
        group = QGroupBox("常用运维工具")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)

        self.ping_excel_btn = QPushButton("📡  批量 Ping")
        self.ping_excel_btn.setObjectName("btn_outline")
        self.ping_excel_btn.setToolTip(
            "使用设备列表、手工地址或 CIDR 网段执行批量 Ping，"
            "结果显示在右侧日志窗口"
        )
        self.ping_excel_btn.clicked.connect(self.batch_ping_devices)

        self.port_check_btn = QPushButton("🔌  端口检测")
        self.port_check_btn.setObjectName("btn_outline")
        self.port_check_btn.setToolTip("批量检测指定 TCP 端口，不发送应用数据")
        self.port_check_btn.clicked.connect(self.start_port_check)

        self.ssh_test_btn = QPushButton("🔐  SSH 登录测试")
        self.ssh_test_btn.setObjectName("btn_outline")
        self.ssh_test_btn.setToolTip("仅验证 SSH 认证，不执行任何设备命令")
        self.ssh_test_btn.clicked.connect(self.start_ssh_login_test)

        self.traceroute_btn = QPushButton("🧭  路由跟踪")
        self.traceroute_btn.setObjectName("btn_outline")
        self.traceroute_btn.setToolTip("批量执行系统 Traceroute/Tracert")
        self.traceroute_btn.clicked.connect(self.start_traceroute)

        self.config_diff_btn = QPushButton("⇄  配置对比")
        self.config_diff_btn.setObjectName("btn_outline")
        self.config_diff_btn.setToolTip("比较两份本地配置文件的差异")
        self.config_diff_btn.clicked.connect(self.show_config_diff)

        self.config_backup_btn = QPushButton("💾  配置备份")
        self.config_backup_btn.setObjectName("btn_outline")
        self.config_backup_btn.setToolTip(
            "按设备建立目录，保存版本化 CFG 配置和 JSON 元数据"
        )
        self.config_backup_btn.clicked.connect(self.start_config_backup)

        self.subnet_calc_btn = QPushButton("▦  子网计算")
        self.subnet_calc_btn.setObjectName("btn_outline")
        self.subnet_calc_btn.setToolTip("计算 IPv4/IPv6 网络范围和地址数量")
        self.subnet_calc_btn.clicked.connect(self.show_subnet_calculator)

        self.serial_console_btn = QPushButton("⌁  串口控制台")
        self.serial_console_btn.setObjectName("btn_outline")
        self.serial_console_btn.setToolTip("通过 Windows COM 串口连接交换机 Console")
        self.serial_console_btn.clicked.connect(self.show_serial_console)

        self.ssh_console_btn = QPushButton("⌨  SSH 交互终端")
        self.ssh_console_btn.setObjectName("btn_outline")
        self.ssh_console_btn.setToolTip("从设备列表选择一台设备并打开交互式 SSH 会话")
        self.ssh_console_btn.clicked.connect(self.show_ssh_console)

        self.file_transfer_btn = QPushButton("⇅  文件传输服务")
        self.file_transfer_btn.setObjectName("btn_outline")
        self.file_transfer_btn.setToolTip(
            "临时启动 FTP 或 TFTP 服务，与交换机上传、下载文件"
        )
        self.file_transfer_btn.clicked.connect(self.show_file_transfer)

        self.packet_capture_btn = QPushButton("◉  网络抓包")
        self.packet_capture_btn.setObjectName("btn_outline")
        self.packet_capture_btn.setToolTip(
            "调用 Wireshark Dumpcap 抓取本机网卡可见流量并保存为 pcapng"
        )
        self.packet_capture_btn.clicked.connect(self.show_packet_capture)

        self.health_check_btn = QPushButton("▣  一键设备巡检")
        self.health_check_btn.setObjectName("btn_outline")
        self.health_check_btn.setToolTip(
            "只读采集 H3C/Comware、Huawei VRP 的 CPU、内存、温度、"
            "风扇、电源和接口摘要"
        )
        self.health_check_btn.clicked.connect(self.start_health_check)

        self.terminal_locate_btn = QPushButton("⌖  IP/MAC 终端定位")
        self.terminal_locate_btn.setObjectName("btn_outline")
        self.terminal_locate_btn.setToolTip(
            "通过 H3C/Comware、Huawei VRP 的 ARP 表和 MAC 地址表定位终端接口"
        )
        self.terminal_locate_btn.clicked.connect(self.start_terminal_locate)

        self.interface_diag_btn = QPushButton("≋  接口综合诊断")
        self.interface_diag_btn.setObjectName("btn_outline")
        self.interface_diag_btn.setToolTip(
            "只读检查 H3C/Comware、Huawei VRP 接口状态、速率、双工、"
            "VLAN 和光模块信息"
        )
        self.interface_diag_btn.clicked.connect(self.start_interface_diagnosis)

        self._maintenance_buttons = [
            self.port_check_btn,
            self.ssh_test_btn,
            self.traceroute_btn,
            self.config_backup_btn,
            self.health_check_btn,
            self.terminal_locate_btn,
            self.interface_diag_btn,
        ]

        self._ops_tools_layout = layout
        self._ops_tool_buttons = [
            self.serial_console_btn,
            self.ssh_console_btn,
            self.file_transfer_btn,
            self.packet_capture_btn,
            self.health_check_btn,
            self.terminal_locate_btn,
            self.interface_diag_btn,
            self.ping_excel_btn,
            self.port_check_btn,
            self.ssh_test_btn,
            self.traceroute_btn,
            self.config_diff_btn,
            self.config_backup_btn,
            self.subnet_calc_btn,
        ]
        self._ops_tools_columns = 1
        for row, button in enumerate(self._ops_tool_buttons):
            layout.addWidget(button, row, 0)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)

        return group

    def show_serial_console(self):
        if self._serial_console is None:
            self._serial_console = SerialConsoleDialog(self)
            self._serial_console.setAttribute(Qt.WA_DeleteOnClose)
            self._serial_console.destroyed.connect(
                lambda: setattr(self, "_serial_console", None)
            )
        self._serial_console.show()
        self._serial_console.raise_()
        self._serial_console.activateWindow()

    def show_ssh_console(self):
        devices = list(self.device_manager.devices)
        if self._ssh_console is None:
            self._ssh_console = SSHConsoleDialog(devices, self)
            self._ssh_console.setAttribute(Qt.WA_DeleteOnClose)
            self._ssh_console.destroyed.connect(
                lambda: setattr(self, "_ssh_console", None)
            )
        else:
            self._ssh_console.set_devices(devices)
        self._ssh_console.show()
        self._ssh_console.raise_()
        self._ssh_console.activateWindow()

    def show_file_transfer(self):
        if self._file_transfer_dialog is None:
            self._file_transfer_dialog = FileTransferDialog(self)
            self._file_transfer_dialog.setAttribute(Qt.WA_DeleteOnClose)
            self._file_transfer_dialog.destroyed.connect(
                lambda: setattr(self, "_file_transfer_dialog", None)
            )
        self._file_transfer_dialog.show()
        self._file_transfer_dialog.raise_()
        self._file_transfer_dialog.activateWindow()

    def show_packet_capture(self):
        if self._packet_capture_dialog is None:
            self._packet_capture_dialog = PacketCaptureDialog(self)
            self._packet_capture_dialog.setAttribute(Qt.WA_DeleteOnClose)
            self._packet_capture_dialog.destroyed.connect(
                lambda: setattr(self, "_packet_capture_dialog", None)
            )
        self._packet_capture_dialog.show()
        self._packet_capture_dialog.raise_()
        self._packet_capture_dialog.activateWindow()

    def _build_config_templates_group(self) -> QGroupBox:
        group = QGroupBox("常用配置模板")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.config_template_list = QListWidget()
        self.config_template_list.setMinimumHeight(118)
        self.config_template_list.setMaximumHeight(180)
        self.config_template_list.setAlternatingRowColors(True)
        self.config_template_list.itemDoubleClicked.connect(self.open_config_template)
        layout.addWidget(self.config_template_list)

        self.use_template_btn = QPushButton("▶  调用选中模板")
        self.use_template_btn.setObjectName("btn_primary")
        self.use_template_btn.setToolTip("将选中模板设为当前统一业务命令文件")
        self.use_template_btn.clicked.connect(self.use_config_template)
        layout.addWidget(self.use_template_btn)

        btn_row = QHBoxLayout()
        self.add_template_btn = QPushButton("＋  添加模板")
        self.add_template_btn.setObjectName("btn_outline")
        self.add_template_btn.setToolTip("批量添加自己的配置模板")
        self.add_template_btn.clicked.connect(self.add_config_template)

        self.remove_template_btn = QPushButton("✂  移除选中")
        self.remove_template_btn.setObjectName("btn_neutral")
        self.remove_template_btn.setToolTip("仅自定义模板可以从列表中移除")
        self.remove_template_btn.clicked.connect(self.remove_config_template)

        btn_row.addWidget(self.add_template_btn)
        btn_row.addWidget(self.remove_template_btn)
        layout.addLayout(btn_row)

        return group

    # ── 右侧面板 ─────────────────────────────────────────
    def create_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("right_workspace")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 设备列表
        list_group = QGroupBox("设备列表")
        list_group.setObjectName("device_list_group")
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(8, 16, 8, 8)

        filter_row = QHBoxLayout()
        self.device_search_input = QLineEdit()
        self.device_search_input.setPlaceholderText("搜索名称、IP、品牌或标签")
        self.device_search_input.setClearButtonEnabled(True)
        self.device_search_input.textChanged.connect(self.apply_device_filters)
        self.group_filter_combo = QComboBox()
        self.group_filter_combo.addItem("全部分组", "")
        self.group_filter_combo.currentIndexChanged.connect(
            self.apply_device_filters
        )
        self.execution_scope_combo = QComboBox()
        self.execution_scope_combo.addItem("执行全部设备", "all")
        self.execution_scope_combo.addItem("执行筛选结果", "filtered")
        self.execution_scope_combo.addItem("执行选中设备", "selected")
        filter_row.addWidget(self.device_search_input, 1)
        filter_row.addWidget(self.group_filter_combo)
        filter_row.addWidget(self.execution_scope_combo)
        list_layout.addLayout(filter_row)

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(10)
        self.device_table.setHorizontalHeaderLabels(
            [
                "设备名称", "分组", "标签", "品牌", "型号",
                "IP 地址", "IP 版本", "端口", "用户名", "状态",
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

        # 日志
        log_group = QGroupBox("连接日志")
        log_group.setObjectName("connection_log_group")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 16, 8, 8)

        # 日志工具栏
        log_toolbar = QHBoxLayout()
        self._log_title_label = QLabel("实时输出")
        self._log_title_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: 15px; background: transparent;"
        )
        log_toolbar.addWidget(self._log_title_label)
        log_toolbar.addStretch()
        log_layout.addLayout(log_toolbar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 16))
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group, stretch=3)

        return panel

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
        brand    = self.brand_combo.currentText()
        ip       = self.ip_input.text().strip()
        port     = self.port_spin.value()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        name     = self.name_input.text().strip()
        group = self.group_input.text().strip()
        tags = self.tags_input.text().strip()
        auth_method = self.auth_method_combo.currentData()
        private_key_path = self.private_key_input.text().strip()
        private_key_passphrase = self.key_passphrase_input.text()
        host_key_policy = self.host_key_policy_combo.currentData()

        if not ip:
            self._warn("请输入 IP 地址")
            return
        validator = IPv6AddressValidator()
        is_valid, error_msg = validator.validate_for_ssh(ip)
        if not is_valid:
            self._warn(f"IP 地址格式错误:\n{error_msg}")
            return
        if not username:
            self._warn("请输入用户名")
            return
        if auth_method == "password" and not password:
            self._warn("请输入密码")
            return
        if auth_method == "key" and not private_key_path:
            self._warn("请选择 SSH 私钥文件")
            return
        if auth_method == "key" and not os.path.isfile(private_key_path):
            self._warn("SSH 私钥文件不存在")
            return

        device = DeviceInfo(
            brand, ip, port, username, password, name,
            group=group, tags=tags, auth_method=auth_method,
            private_key_path=private_key_path,
            private_key_passphrase=private_key_passphrase,
            host_key_policy=host_key_policy,
        )
        if not self.device_manager.add_device(device):
            self._warn(f"设备已存在，已跳过: {ip}:{port}")
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

        display = name or ip
        self._log_info(f"[添加]  {display}")
        self.logger.log_operation(f"添加设备: {display}")
        self._update_device_count()

    def update_device_table(self):
        devices = self.device_manager.get_devices()
        self.device_table.setRowCount(len(devices))

        for i, device in enumerate(devices):
            display_ip   = device.get_display_address()
            ip_version   = device.ip_version.value if device.ip_version else 0
            version_text = "IPv6" if ip_version == 6 else "IPv4" if ip_version == 4 else "未知"

            self.device_table.setItem(i, 0, QTableWidgetItem(device.name))
            self.device_table.setItem(i, 1, QTableWidgetItem(device.group))
            self.device_table.setItem(i, 2, QTableWidgetItem(device.tags))
            self.device_table.setItem(i, 3, QTableWidgetItem(device.brand))
            self.device_table.setItem(i, 4, QTableWidgetItem(""))
            self.device_table.setItem(i, 5, QTableWidgetItem(display_ip))
            self.device_table.setItem(i, 6, QTableWidgetItem(version_text))
            self.device_table.setItem(i, 7, QTableWidgetItem(str(device.port)))
            self.device_table.setItem(i, 8, QTableWidgetItem(device.username))

            # 建议4：状态列使用 StatusBadge cell widget，充分利用颜色语义
            badge = StatusBadge(
                "待连接",
                font_px=getattr(self, "_status_badge_font_px", 14),
            )
            self.device_table.setCellWidget(i, 9, badge)

        self._refresh_group_filter()
        self.apply_device_filters()
        self._update_device_count()

    def _refresh_group_filter(self):
        current = self.group_filter_combo.currentData()
        groups = sorted({
            device.group for device in self.device_manager.get_devices()
            if device.group
        })
        self.group_filter_combo.blockSignals(True)
        self.group_filter_combo.clear()
        self.group_filter_combo.addItem("全部分组", "")
        for group in groups:
            self.group_filter_combo.addItem(group, group)
        index = self.group_filter_combo.findData(current)
        self.group_filter_combo.setCurrentIndex(max(0, index))
        self.group_filter_combo.blockSignals(False)

    def apply_device_filters(self):
        if not hasattr(self, "device_table"):
            return
        query = self.device_search_input.text().strip().lower()
        group = self.group_filter_combo.currentData() or ""
        devices = self.device_manager.get_devices()
        for row, device in enumerate(devices):
            haystack = " ".join([
                device.name, device.ip, device.brand, device.group, device.tags,
                device.username,
            ]).lower()
            visible = (not query or query in haystack) and (
                not group or device.group == group
            )
            self.device_table.setRowHidden(row, not visible)

    def _get_execution_devices(self):
        devices = self.device_manager.get_devices()
        scope = self.execution_scope_combo.currentData()
        if scope == "filtered":
            return [
                device for row, device in enumerate(devices)
                if not self.device_table.isRowHidden(row)
            ]
        if scope == "selected":
            rows = sorted({index.row() for index in self.device_table.selectedIndexes()})
            return [devices[row] for row in rows if 0 <= row < len(devices)]
        return list(devices)

    def open_result_center(self):
        results = self.execution_results
        if not results and self.ssh_manager:
            results = self.ssh_manager.get_results()
        dialog = ResultCenterDialog(results, self)
        dialog.exec_()

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
            master_password, accepted = QInputDialog.getText(
                self, "解密认证信息", "请输入该 Excel 的主密码：", QLineEdit.Password
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

        success_count, error_count, errors = self.device_manager.import_from_excel(
            file_path, master_password=master_password
        )
        skipped_count = getattr(self.device_manager, 'last_import_skipped_count', 0)
        skipped = getattr(self.device_manager, 'last_import_skipped', [])
        self.update_device_table()

        msg = (
            f"导入完成！\n"
            f"新增: {success_count} 个\n"
            f"跳过重复: {skipped_count} 个\n"
            f"失败: {error_count} 个"
        )
        detail_lines = []
        if skipped:
            detail_lines.append("重复设备:")
            detail_lines.extend(skipped[:5])
        if errors:
            detail_lines.append("错误信息:")
            detail_lines.extend(errors[:5])
        if detail_lines:
            msg += "\n\n" + "\n".join(detail_lines)
        QMessageBox.information(self, "导入结果", msg)

        self._log_info(f"[导入] Excel 文件 -> 新增 {success_count} 个，跳过重复 {skipped_count} 个，失败 {error_count} 个")
        self.logger.log_operation(f"从 Excel 导入设备: 新增={success_count}, 跳过重复={skipped_count}, 失败={error_count}")
        self._set_status(f"导入完成: 新增 {success_count} / 跳过 {skipped_count}")
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
        if self.ping_worker and self.ping_worker.isRunning():
            self._warn("批量 Ping 正在执行，请等待当前任务完成")
            return
        if self.maintenance_worker and self.maintenance_worker.isRunning():
            self._warn("另一项批量运维任务正在执行，请等待当前任务完成")
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

        self.ping_worker = PingWorker(ips)
        self.ping_worker.progress_signal.connect(self._record_ping_log)
        self.ping_worker.finished_signal.connect(self.batch_ping_finished)
        self.ping_worker.start()

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
        devices = self.device_manager.get_devices()
        if not devices:
            QMessageBox.warning(self, "常用运维工具", "设备列表为空，请先导入或添加设备")
            return []
        return devices

    def _select_maintenance_targets(self, mode: str) -> List:
        dialog = MaintenanceTargetDialog(
            mode,
            self.device_manager.get_devices(),
            self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return []
        return dialog.selected_devices()

    def _start_maintenance_task(self, mode: str, options=None, devices=None):
        if self.maintenance_worker and self.maintenance_worker.isRunning():
            self._warn("另一项批量运维任务正在执行，请等待当前任务完成")
            return
        if self.ping_worker and self.ping_worker.isRunning():
            self._warn("批量 Ping 正在执行，请等待当前任务完成")
            return

        devices = list(devices) if devices is not None else (
            self._maintenance_devices()
        )
        if not devices:
            return

        labels = {
            "port": "批量端口检测",
            "ssh_login": "批量 SSH 登录测试",
            "traceroute": "批量路由跟踪",
            "backup": "批量配置备份",
        }
        label = labels[mode]
        self._maintenance_log_lines = []
        self.log_text.clear()
        self._record_maintenance_log(f"[{label}] 开始，共 {len(devices)} 台设备")
        self._set_maintenance_running(True)
        self._show_progress()
        self.progress_bar.setRange(0, 0)
        self._set_status(f"{label}正在执行...")

        self.maintenance_worker = MaintenanceWorker(
            mode,
            devices,
            options=options,
            logger=self.logger,
        )
        self.maintenance_worker.progress_signal.connect(self._record_maintenance_log)
        self.maintenance_worker.finished_signal.connect(self._maintenance_task_finished)
        self.maintenance_worker.start()

    def _start_diagnostics_task(self, mode: str, devices, options=None):
        if self.diagnostics_worker and self.diagnostics_worker.isRunning():
            self._warn("另一项设备诊断正在执行，请等待当前任务完成")
            return
        if self.maintenance_worker and self.maintenance_worker.isRunning():
            self._warn("另一项批量运维任务正在执行，请等待当前任务完成")
            return
        if self.ping_worker and self.ping_worker.isRunning():
            self._warn("批量 Ping 正在执行，请等待当前任务完成")
            return

        labels = {
            "health_check": "一键设备巡检",
            "terminal_locate": "IP/MAC 终端定位",
            "interface_diagnosis": "接口综合诊断",
        }
        label = labels[mode]
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

        self.diagnostics_worker = DeviceDiagnosticsWorker(
            mode,
            devices,
            options=options,
            logger=self.logger,
        )
        self.diagnostics_worker.progress_signal.connect(
            self._record_maintenance_log
        )
        self.diagnostics_worker.finished_signal.connect(
            self._diagnostics_task_finished
        )
        self.diagnostics_worker.start()

    def _diagnostics_task_finished(self, mode: str, results):
        labels = {
            "health_check": ("一键设备巡检", "health_check"),
            "terminal_locate": ("IP_MAC终端定位", "terminal_locate"),
            "interface_diagnosis": ("接口综合诊断", "interface_diagnosis"),
        }
        label, prefix = labels.get(mode, ("设备诊断", "diagnostics"))
        results = list(results or [])
        success = sum(bool(item.get("task_success")) for item in results)
        failure = len(results) - success
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
        labels = {
            "port": ("端口检测", "port"),
            "ssh_login": ("SSH 登录测试", "ssh_login"),
            "traceroute": ("路由跟踪", "traceroute"),
            "backup": ("配置备份", "config_backup"),
        }
        label, prefix = labels.get(mode, ("运维任务", "maintenance"))
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
            log_dir = os.path.abspath(self.logger.log_dir)
            os.makedirs(log_dir, exist_ok=True)
            base_name = f"{prefix}{datetime.now().strftime('%Y%m%d%H%M')}"
            log_path = os.path.join(log_dir, f"{base_name}.log")
            counter = 1
            while os.path.exists(log_path):
                log_path = os.path.join(log_dir, f"{base_name}_{counter}.log")
                counter += 1
            write_lines(log_path, self._maintenance_log_lines)
            return log_path
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
        devices = self.device_manager.get_devices()
        if not devices:
            QMessageBox.warning(self, "配置备份", "设备列表为空，请先导入或添加设备")
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
        self._start_maintenance_task("backup", {"output_dir": output_dir})

    def show_config_diff(self):
        first_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择第一份配置",
            "",
            "配置文件 (*.txt *.cfg *.conf *.log);;所有文件 (*.*)",
        )
        if not first_path:
            return
        second_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择第二份配置",
            os.path.dirname(first_path),
            "配置文件 (*.txt *.cfg *.conf *.log);;所有文件 (*.*)",
        )
        if not second_path:
            return
        try:
            diff_text = unified_config_diff(first_path, second_path)
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self, "配置对比失败", str(exc))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("配置文件对比")
        dialog.resize(1100, 760)
        layout = QVBoxLayout(dialog)

        title = QLabel(
            f"第一份：{first_path}\n第二份：{second_path}\n"
            "“-”表示第一份独有，“+”表示第二份新增。"
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setFont(QFont("Consolas", 13))
        viewer.setPlainText(diff_text)
        layout.addWidget(viewer)

        button_row = QHBoxLayout()
        save_button = QPushButton("💾  保存差异")
        save_button.setObjectName("btn_outline")
        close_button = QPushButton("关闭")
        close_button.setObjectName("btn_neutral")
        button_row.addStretch()
        button_row.addWidget(save_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        def save_diff():
            path, _ = QFileDialog.getSaveFileName(
                dialog,
                "保存配置差异",
                "config_diff.txt",
                "文本文件 (*.txt)",
            )
            if path:
                try:
                    write_lines(path, diff_text.splitlines())
                    self._log_info(f"[配置对比] 差异文件已保存: {path}")
                except OSError as exc:
                    QMessageBox.critical(dialog, "保存失败", str(exc))

        save_button.clicked.connect(save_diff)
        close_button.clicked.connect(dialog.accept)
        self._log_info(
            f"[配置对比] 已比较 {os.path.basename(first_path)} 和 "
            f"{os.path.basename(second_path)}"
        )
        dialog.exec_()

    def show_subnet_calculator(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("IPv4 / IPv6 子网计算器")
        dialog.resize(720, 560)
        layout = QVBoxLayout(dialog)

        prompt = QLabel("输入带前缀长度的地址")
        layout.addWidget(prompt)
        address_input = QLineEdit()
        address_input.setPlaceholderText("例如：192.168.10.20/24 或 2001:db8::20/64")
        layout.addWidget(address_input)

        result_view = QTextEdit()
        result_view.setReadOnly(True)
        result_view.setFont(QFont("Microsoft YaHei", 13))
        layout.addWidget(result_view)

        button_row = QHBoxLayout()
        calculate_button = QPushButton("▦  计算")
        calculate_button.setObjectName("btn_primary")
        close_button = QPushButton("关闭")
        close_button.setObjectName("btn_neutral")
        button_row.addWidget(calculate_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        def calculate():
            try:
                rows = calculate_subnet(address_input.text())
            except ValueError as exc:
                QMessageBox.warning(dialog, "地址输入错误", str(exc))
                return
            width = max(len(label) for label, _ in rows)
            result_view.setPlainText(
                "\n".join(f"{label.ljust(width)} : {value}" for label, value in rows)
            )

        calculate_button.clicked.connect(calculate)
        address_input.returnPressed.connect(calculate)
        close_button.clicked.connect(dialog.accept)
        address_input.setFocus()
        dialog.exec_()

    def encrypt_excel_passwords(self):
        source_path, _ = QFileDialog.getOpenFileName(
            self, "选择需要加密的 Excel", "", "Excel Files (*.xlsx)"
        )
        if not source_path:
            return

        master_password, accepted = QInputDialog.getText(
            self, "设置主密码", "请输入主密码（至少 8 个字符）：", QLineEdit.Password
        )
        if not accepted:
            return
        confirm_password, accepted = QInputDialog.getText(
            self, "确认主密码", "请再次输入主密码：", QLineEdit.Password
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
            if os.path.exists(self._template_store_path):
                with open(self._template_store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._config_templates = [
                        item for item in data
                        if isinstance(item, dict) and item.get("path")
                    ]
        except Exception as exc:
            self._config_templates = []
            self._log_append(f"[模板] 配置模板加载失败: {exc}")
        self._refresh_config_template_list()

    def _save_config_templates(self):
        os.makedirs(os.path.dirname(self._template_store_path), exist_ok=True)
        with open(self._template_store_path, "w", encoding="utf-8") as f:
            json.dump(self._config_templates, f, ensure_ascii=False, indent=2)

    def _refresh_config_template_list(self):
        if not hasattr(self, "config_template_list"):
            return
        self.config_template_list.clear()
        all_templates = get_builtin_templates() + [
            {**item, "builtin": False}
            for item in self._config_templates
        ]
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

        existing = {
            os.path.abspath(item.get("path", ""))
            for item in self._config_templates
        }
        added = []
        skipped = []
        for file_path in file_paths:
            abs_path = os.path.abspath(file_path)
            if abs_path in existing:
                skipped.append(abs_path)
                continue
            self._config_templates.append({
                "name": os.path.basename(abs_path),
                "path": abs_path,
            })
            existing.add(abs_path)
            added.append(abs_path)

        if not added:
            self._warn("选择的模板都已存在")
            return
        self._save_config_templates()
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
        path = os.path.abspath(template.get("path", ""))
        self._config_templates = [
            saved for saved in self._config_templates
            if os.path.abspath(saved.get("path", "")) != path
        ]
        self._save_config_templates()
        self._refresh_config_template_list()
        self._update_left_content_min_height()
        self._log_info(f"[模板] 已移除配置模板: {name}")

    def open_config_template(self, item: QListWidgetItem):
        template = self._template_item_data(item)
        file_path = template.get("path", "")
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "模板不存在", "模板文件不存在，可能已被移动或删除")
            return

        content = None
        last_error = None
        for encoding in ("utf-8", "gbk", "gb18030"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except Exception as exc:
                last_error = exc

        if content is None:
            QMessageBox.critical(self, "打开失败", f"无法读取模板文件:\n{last_error}")
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
            QTimer.singleShot(3000, self._update_device_count)
            return

        if not self._confirm_action(
            "调用配置模板",
            f"确定将“{name}”设为当前业务命令吗？\n\n"
            "程序不会转换模板命令。调用后仍需点击“开始连接”才会执行，"
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
        QTimer.singleShot(3000, self._update_device_count)

    def start_connection(self):
        if self.connection_worker and self.connection_worker.isRunning():
            self.stop_connection()
            return

        devices = self._get_execution_devices()
        if not devices:
            QMessageBox.warning(
                self, "警告", "当前执行范围内没有设备，请检查筛选条件或表格选中项"
            )
            return

        self.ssh_manager = SSHManager(max_connections=5)
        self.ssh_manager.command_file = self._command_file
        self.ssh_manager.command_directory = self._command_directory
        self.ssh_manager.command_lines = (
            list(self._command_lines) if self._command_lines is not None else None
        )
        self.ssh_manager.command_label = self._active_template_name
        self.ssh_manager.required_brand = self._required_template_brand
        self.ssh_manager.sensitive_values = list(self._template_secret_values)

        if self._required_template_brand:
            mismatched = [
                device
                for device in devices
                if str(getattr(device, "brand", "") or "").lower()
                not in ("", "unknown", self._required_template_brand)
            ]
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

        if self.cmd_mode_combo.currentData() == "per_device":
            if not self._command_directory or not os.path.isdir(self._command_directory):
                QMessageBox.warning(self, "脚本目录", "请先选择有效的设备脚本目录")
                return
            preview_lines = []
            missing_count = 0
            for device in devices:
                script_path = self.ssh_manager.resolve_command_file(device)
                if script_path:
                    preview_lines.append(f"{device.name} ({device.ip})  →  {os.path.basename(script_path)}")
                else:
                    preview_lines.append(f"{device.name} ({device.ip})  →  未匹配，将跳过")
                    missing_count += 1
            preview = "\n".join(preview_lines[:30])
            if len(preview_lines) > 30:
                preview += f"\n... 其余 {len(preview_lines) - 30} 台设备未显示"
            if missing_count:
                preview += f"\n\n未匹配设备：{missing_count} 台"
            answer = QMessageBox.question(
                self, "确认脚本匹配", preview + "\n\n确认开始执行？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        self._total_count    = len(devices)
        self._connected_count = 0
        self.execution_results = []

        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("■  停止连接")
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
        execution_keys = {
            (device.ip, int(device.port)) for device in devices
        }
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

        self.ssh_manager.save_after_exec   = self.save_check.isChecked()
        self.ssh_manager.detect_l2_uplink  = self.l2_uplink_check.isChecked()
        self.connection_worker = ConnectionWorker(self.ssh_manager, devices)
        self.connection_worker.set_logger(self.logger)
        self.connection_worker.progress_signal.connect(self.update_progress)
        # 建议2：连接逐设备实时状态信号
        self.connection_worker.device_status_signal.connect(self.on_device_status)
        self.connection_worker.result_signal.connect(self.handle_result)
        self.connection_worker.finished_signal.connect(self.connection_finished)
        self.connection_worker.start()

    def stop_connection(self):
        if self.ssh_manager:
            self.ssh_manager.stop_connections()
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
        device_result = result.get("device_info", {}) or {}
        result_key = (
            device_result.get("ip", ""),
            int(device_result.get("port", 22) or 22),
        )
        self.execution_results = [
            existing for existing in self.execution_results
            if (
                (existing.get("device_info", {}) or {}).get("ip", ""),
                int((existing.get("device_info", {}) or {}).get("port", 22) or 22),
            ) != result_key
        ]
        self.execution_results.append(result)
        device_info    = result.get("device_info", {})
        is_connected   = result.get("is_connected", False)
        error_message  = result.get("error_message", "")
        ip             = device_info.get("ip", "")
        model_detected = result.get("model_detected", "") or ""
        brand_detected = result.get("brand_detected", "") or ""

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
                if is_connected:
                    text = f"✔ 成功  {brand_detected}" if brand_detected else "✔ 连接成功"
                else:
                    short_err = (error_message[:30] + "...") if len(error_message) > 30 else error_message
                    text = f"✘ {short_err}"
                badge.setText(text)

    def connection_finished(self):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("▶  开始连接")
        self.add_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        # 先跳到 100% 给用户一个"任务完成"的视觉确认，再收缩隐藏
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        QTimer.singleShot(800, self._hide_progress)   # 800ms 后收缩消失

        results = self.ssh_manager.get_results() if self.ssh_manager else []
        if self.ssh_manager and self._active_template_sensitive:
            self.ssh_manager.command_lines = None
            self.ssh_manager.sensitive_values = []
        total = len(results) or self._total_count
        success = sum(1 for result in results if result.get("is_connected"))
        failure = max(0, total - success)
        rate = (success / total * 100) if total else 0.0

        self._log_info(f"[完成] 成功: {success} 台，失败: {failure} 台，成功率: {rate:.1f}%")
        self._set_status(f"完成: {success} 成功 / {failure} 失败")
        self.logger.log_operation(f"连接任务完成: 成功={success}, 失败={failure}, 总数={total}")
        # 3 秒后右侧标签恢复为设备数显示
        QTimer.singleShot(3000, self._update_device_count)

        msg = (
            f"连接任务完成！\n\n"
            f"  总数: {total} 台\n"
            f"  成功: {success} 台\n"
            f"  失败: {failure} 台\n"
            f"  成功率: {rate:.1f}%"
        )
        QMessageBox.information(self, "连接完成", msg)
        if self._active_template_sensitive:
            self._clear_parameterized_template(
                "包含密码的参数模板已在任务结束后从内存清除"
            )
            self.cmd_file_label.setText("SSH_command.txt  (默认)")
            self.cmd_file_label.setToolTip("")

    def delete_selected_device(self):
        """移除设备列表中当前选中的行（借鉴 w-sw-ssh 思路，支持精细管理）"""
        selected_rows = sorted(
            {idx.row() for idx in self.device_table.selectedIndexes()},
            reverse=True
        )
        if not selected_rows:
            self._warn("请先在设备列表中选中要移除的设备")
            return
        if not self._confirm_action("确认移除", f"确定要移除选中的 {len(selected_rows)} 台设备吗？"):
            return
        for row in selected_rows:
            self.device_manager.remove_device(row)
        self.update_device_table()
        self._log_info(f"[移除]  已移除 {len(selected_rows)} 台设备")
        self._set_status(f"已移除 {len(selected_rows)} 台设备")
        self._update_device_count()

    def clear_devices(self):
        if not self._confirm_action("确认清空", "确定要清空所有设备吗？\n\n此操作会移除当前设备列表中的全部设备。"):
            return
        self.device_manager.clear_devices()
        self.update_device_table()
        self.log_text.clear()
        self._log_info("[清空]  设备列表已清空")
        self.logger.log_operation("清空设备列表")
        self._set_status("设备列表已清空")
        self._update_device_count()

    def view_logs(self):
        log_files = self.logger.get_log_files()
        log_dir   = os.path.abspath(self.logger.log_dir)
        msg = (
            f"日志文件位置\n\n"
            f"  ✅  成功日志: {len(log_files['success'])} 个文件\n"
            f"  ❌  失败日志: {len(log_files['failure'])} 个文件\n"
            f"  📋  操作日志: {len(log_files['operation'])} 个文件\n\n"
            f"  📁  日志目录:\n  {log_dir}"
        )
        QMessageBox.information(self, "日志信息", msg)

    def clear_connection_log(self):
        self.log_text.clear()
        self._set_status("连接日志已清空")
        QTimer.singleShot(3000, self._update_device_count)

    def browse_command_file(self):
        """选择自定义命令文件"""
        if self.cmd_mode_combo.currentData() == "per_device":
            directory = QFileDialog.getExistingDirectory(self, "选择设备脚本目录", "")
            if not directory:
                return
            self._command_directory = directory
            self._clear_parameterized_template()
            display = os.path.basename(os.path.normpath(directory)) or directory
            self.cmd_file_label.setText(display)
            self.cmd_file_label.setToolTip(directory)
            self._log_info(f"[命令]  已选择设备脚本目录: {directory}")
            self._set_status(f"设备脚本目录: {display}")
            QTimer.singleShot(3000, self._update_device_count)
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择命令文件", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if not file_path:
            return
        self._command_file = file_path
        self._clear_parameterized_template()
        # 只显示文件名，避免路径过长
        display = os.path.basename(file_path)
        self.cmd_file_label.setText(display)
        self.cmd_file_label.setToolTip(file_path)
        self._log_info(f"[命令]  已选择命令文件: {file_path}")
        self._set_status(f"命令文件: {display}")
        QTimer.singleShot(3000, self._update_device_count)

    def reset_command_file(self):
        """恢复使用默认命令文件"""
        self._command_file = None
        self._command_directory = None
        self._clear_parameterized_template()
        if self.cmd_mode_combo.currentData() == "per_device":
            self.cmd_file_label.setText("请选择设备脚本目录")
        else:
            self.cmd_file_label.setText("SSH_command.txt  (默认)")
        self.cmd_file_label.setToolTip("")
        self._log_info("[命令]  已恢复使用默认命令文件 SSH_command.txt")
        self._set_status("命令文件已恢复为默认")
        QTimer.singleShot(3000, self._update_device_count)

    def on_command_mode_changed(self):
        """Switch the existing command area between one file and per-device matching."""
        if self._command_lines is not None:
            self._clear_parameterized_template()
        per_device = self.cmd_mode_combo.currentData() == "per_device"
        if per_device:
            self._command_file = None
            self.cmd_browse_btn.setText("📁  选择脚本目录")
            self.cmd_file_label.setText(
                os.path.basename(os.path.normpath(self._command_directory))
                if self._command_directory else "请选择设备脚本目录"
            )
            self._cmd_tip_label.setText("仅按设备名称匹配：设备名 SW1 → SW1.txt")
        else:
            self._command_directory = None
            self.cmd_browse_btn.setText("📄  选择文件")
            self.cmd_file_label.setText(
                os.path.basename(self._command_file) if self._command_file else "SSH_command.txt  (默认)"
            )
            self._cmd_tip_label.setText("命令原样发送；每行一条，# 开头为注释")
        self.cmd_file_label.setToolTip("")

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
        return datetime.now().strftime('%H:%M:%S')

    def _log_info(self, text: str):
        text = html.escape(text)
        self.log_text.append(
            f'<span style="color:#58A6FF;">[{self._ts()}] {text}</span>'
        )

    def _log_append(self, text: str):
        # 建议5：将日志中 [raw_ip] 格式统一替换为与列表 IP 列一致的 display 格式
        import re as _re
        def _replace_ip(m):
            raw = m.group(1)
            from utils.ipv6_utils import IPv6Utils
            return f"[{IPv6Utils.format_ipv6_for_display(raw)}]"
        # 匹配 [192.168.x.x] 或 [2001:db8::1] 形式的 IP 前缀
        text = _re.sub(r'\[([0-9a-fA-F:.]+)\]', _replace_ip, text)

        # 根据关键词着色
        if "成功" in text or "success" in text.lower() or text.startswith("✔"):
            color = "#3FB950"
        elif "失败" in text or "fail" in text.lower() or "error" in text.lower() or text.startswith("✘"):
            color = "#F85149"
        elif "警告" in text or "warn" in text.lower() or "[L2探测]" in text:
            color = "#D29922"
        else:
            color = "#C9D1D9"
        ts = self._ts()
        safe_text = html.escape(text)
        self.log_text.append(f'<span style="color:{color};">[{ts}] {safe_text}</span>')

    def _warn(self, msg: str):
        QMessageBox.warning(self, "输入错误", msg)

    def _confirm_action(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes


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
