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
                             QProgressBar, QSplitter, QHeaderView, QFrame,
                             QStatusBar, QToolBar, QAction, QSizePolicy,
                             QAbstractItemView, QApplication, QCheckBox,
                             QScrollArea, QListWidget, QListWidgetItem,
                             QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QFontMetrics, QColor, QPalette, QIcon, QPixmap, QPainter, QBrush, QPen, QLinearGradient
from typing import List, Dict
from datetime import datetime
import os
import sys
import json
import subprocess
import html

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.device_config import DeviceConfigManager, DeviceInfo
from config.device_commands import CommandModule
from core.ssh_manager_simple import SSHManager
from utils.logger import ConnectionLogger
from utils.ipv6_utils import IPv6Utils, IPv6AddressValidator


# ─────────────────────── 主题配色 ───────────────────────
class Theme:
    """现代深色/浅色主题配色方案"""
    # 主色
    PRIMARY        = "#1565C0"   # 深蓝
    PRIMARY_LIGHT  = "#1E88E5"   # 亮蓝
    PRIMARY_DARK   = "#0D47A1"   # 更深蓝
    ACCENT         = "#00BCD4"   # 青色强调
    
    # 背景
    BG_MAIN        = "#F0F4F8"   # 主背景（浅灰蓝）
    BG_PANEL       = "#FFFFFF"   # 面板背景
    BG_CARD        = "#FAFAFA"   # 卡片背景
    BG_HEADER      = "#1565C0"   # 表头背景
    BG_INPUT       = "#FFFFFF"
    
    # 文字
    TEXT_PRIMARY   = "#1A202C"   # 主文字
    TEXT_SECONDARY = "#4A5568"   # 次要文字
    TEXT_HINT      = "#A0AEC0"   # 提示文字
    TEXT_WHITE     = "#FFFFFF"
    TEXT_HEADER    = "#FFFFFF"   # 表头文字
    
    # 状态
    SUCCESS        = "#2E7D32"
    SUCCESS_BG     = "#E8F5E9"
    WARNING        = "#F57F17"
    WARNING_BG     = "#FFFDE7"
    ERROR          = "#C62828"
    ERROR_BG       = "#FFEBEE"
    INFO           = "#1565C0"
    INFO_BG        = "#E3F2FD"
    
    # 边框
    BORDER         = "#E2E8F0"
    BORDER_FOCUS   = "#1E88E5"
    
    # 按钮
    BTN_PRIMARY    = "#1565C0"
    BTN_PRIMARY_H  = "#1E88E5"
    BTN_SUCCESS    = "#2E7D32"
    BTN_SUCCESS_H  = "#388E3C"
    BTN_DANGER     = "#C62828"
    BTN_DANGER_H   = "#D32F2F"
    BTN_NEUTRAL    = "#546E7A"
    BTN_NEUTRAL_H  = "#607D8B"
    
    # 阴影/分割
    SHADOW         = "rgba(0,0,0,0.08)"
    DIVIDER        = "#E2E8F0"
    
    # 进度条
    PROGRESS_BG    = "#E3F2FD"
    PROGRESS_CHUNK = "#1E88E5"

    # 表格行
    ROW_ALT        = "#F7F9FC"
    ROW_HOVER      = "#EBF4FF"
    ROW_SELECT     = "#BBDEFB"


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

/* GroupBox */
QGroupBox {{
    background-color: {Theme.BG_PANEL};
    border: 1px solid {Theme.BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    font-size: 13px;
    font-weight: 600;
    color: {Theme.TEXT_PRIMARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
    color: {Theme.PRIMARY};
    font-size: 13px;
    font-weight: 700;
}}

/* 输入框 */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {Theme.BG_INPUT};
    border: 1.5px solid {Theme.BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 13px;
    color: {Theme.TEXT_PRIMARY};
    min-height: 26px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {Theme.BORDER_FOCUS};
    background-color: #EBF4FF;
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
    background: white;
    selection-background-color: {Theme.ROW_SELECT};
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
    border-radius: 5px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
    min-height: 28px;
    cursor: pointer;
}}
QPushButton:disabled {{
    background-color: #CFD8DC;
    color: #90A4AE;
}}

/* 主操作按钮 */
QPushButton#btn_primary {{
    background-color: {Theme.BTN_PRIMARY};
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
    background-color: {Theme.BTN_SUCCESS};
    color: white;
    font-size: 13px;
    min-height: 34px;
    border-radius: 6px;
    letter-spacing: 1px;
}}
QPushButton#btn_success:hover {{
    background-color: {Theme.BTN_SUCCESS_H};
}}
QPushButton#btn_success:pressed {{
    background-color: #1B5E20;
}}

/* 危险按钮（清空） */
QPushButton#btn_danger {{
    background-color: {Theme.BTN_DANGER};
    color: white;
}}
QPushButton#btn_danger:hover {{
    background-color: {Theme.BTN_DANGER_H};
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
    background-color: transparent;
    color: {Theme.PRIMARY};
    border: 1.5px solid {Theme.PRIMARY};
}}
QPushButton#btn_outline:hover {{
    background-color: {Theme.INFO_BG};
}}

/* 表格 */
QTableWidget {{
    background-color: {Theme.BG_PANEL};
    border: 1px solid {Theme.BORDER};
    border-radius: 8px;
    gridline-color: {Theme.DIVIDER};
    alternate-background-color: {Theme.ROW_ALT};
    selection-background-color: {Theme.ROW_SELECT};
    selection-color: {Theme.TEXT_PRIMARY};
    font-size: 13px;
    outline: none;
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget::item:hover {{
    background-color: {Theme.ROW_HOVER};
}}
QHeaderView::section {{
    background-color: {Theme.BG_HEADER};
    color: {Theme.TEXT_HEADER};
    font-weight: 700;
    font-size: 13px;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid rgba(255,255,255,0.15);
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
    background-color: #0D1117;
    color: #C9D1D9;
    border: 1px solid {Theme.BORDER};
    border-radius: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 6px;
    selection-background-color: #264F78;
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
    background-color: {Theme.PRIMARY_DARK};
    color: rgba(255,255,255,0.85);
    font-size: 12px;
    padding: 2px 8px;
}}
QStatusBar::item {{
    border: none;
}}

/* 标签 */
QLabel#section_title {{
    color: {Theme.PRIMARY};
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
    background: {Theme.BG_CARD};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #B0BEC5;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #78909C;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {Theme.BG_CARD};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #B0BEC5;
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #78909C;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {Theme.DIVIDER};
    width: 4px;
}}
QSplitter::handle:hover {{
    background-color: {Theme.ACCENT};
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


# ─────────────────────── 状态标签组件 ───────────────────────
class StatusBadge(QLabel):
    """彩色状态徽章（建议4：作为 cell widget 嵌入表格状态列）

    支持状态：待连接 / 连接中 / 连接成功(✔) / 连接失败(✘)
    """
    _STYLES = {
        "待连接":  (Theme.TEXT_SECONDARY, "#E2E8F0"),
        "连接成功": (Theme.SUCCESS,        Theme.SUCCESS_BG),
        "✔":      (Theme.SUCCESS,        Theme.SUCCESS_BG),
        "连接中":  (Theme.WARNING,         Theme.WARNING_BG),
        "⏳":     (Theme.WARNING,         Theme.WARNING_BG),
    }

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setContentsMargins(4, 2, 4, 2)
        self._set_style(text)

    def setText(self, text: str):
        super().setText(text)
        self._set_style(text)

    def _set_style(self, text: str):
        color, bg = Theme.TEXT_SECONDARY, "#E2E8F0"
        for key, (c, b) in self._STYLES.items():
            if text.startswith(key):
                color, bg = c, b
                break
        if "✘" in text or "失败" in text or "错误" in text:
            color, bg = Theme.ERROR, Theme.ERROR_BG
        self.setStyleSheet(
            f"color: {color}; background-color: {bg}; border-radius: 4px;"
            f"padding: 3px 10px; font-size: 16px; font-weight: 600;"
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
        # 全量结果仍然发出（用于型号/品牌更新兜底）
        results = self.ssh_manager.get_results()
        for result in results:
            self.result_signal.emit(result)
        self.finished_signal.emit()

    def _on_device_done(self, result: dict):
        """SSHManager 每台设备完成时的回调（在工作线程中执行，通过信号转发到主线程）"""
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

        for index, ip in enumerate(self.ips, start=1):
            ok, detail = self._ping(ip)
            if ok:
                success += 1
                self.progress_signal.emit(f"[Ping] ({index}/{total}) {ip} 可达，响应正常")
            else:
                failure += 1
                self.progress_signal.emit(f"[Ping] ({index}/{total}) {ip} 不可达，{detail}")

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


# ─────────────────────── 主窗口 ───────────────────────
class MainWindow(QMainWindow):
    """主窗口 - 现代化 UI"""

    # 字体缩放锚点：(窗口宽度, pt字号)
    _FONT_ANCHORS = [(1024, 13), (1280, 14), (1600, 16), (1920, 17)]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AOMT")
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
        self._connected_count  = 0
        self._total_count      = 0
        self._ping_log_lines   = []
        self._command_file     = None   # None = 使用默认 SSH_command.txt
        self._current_font_pt  = 14     # 当前字号，防止重复刷新
        self._form_labels      = []
        self._template_store_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "operation_templates.json",
        )
        self._config_templates = []

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
        """将字号 pt 转换为 px 并重新应用到 QSS 和全局字体"""
        # 96 dpi 标准：px = pt * 96 / 72
        px      = max(14, round(pt * 96 / 72))   # 正文像素
        px_sm   = max(13, px - 1)                 # 小号（标签/状态栏）
        px_log  = 21                          # 日志保持约 16pt

        new_style = APP_STYLE
        # 替换各 font-size 占位值（全局/输入/按钮/表格 → px，日志/状态 → px_sm）
        import re
        # 全局通用 font-size（13px）
        new_style = re.sub(r'(QMainWindow, QWidget \{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px}px', new_style)
        new_style = re.sub(r'(QGroupBox\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px}px', new_style)
        new_style = re.sub(r'(QGroupBox::title\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px}px', new_style)
        new_style = re.sub(r'(QLineEdit, QSpinBox, QComboBox\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px}px', new_style)
        new_style = re.sub(r'(QPushButton\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px}px', new_style)
        new_style = re.sub(r'(QPushButton#btn_success\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px}px', new_style)
        new_style = re.sub(r'(QTableWidget\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px}px', new_style)
        new_style = re.sub(r'(QHeaderView::section\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px}px', new_style)
        # 小号：日志/状态/标签
        new_style = re.sub(r'(QTextEdit\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px_log}px', new_style)
        new_style = re.sub(r'(QStatusBar\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px_sm}px', new_style)
        new_style = re.sub(r'(QLabel#field_label\s*\{[^}]*font-size:\s*)\d+px',
                           lambda m: m.group(1) + f'{px_sm}px', new_style)

        self.setStyleSheet(new_style)

        # 全局字体
        app = QApplication.instance()
        if app:
            app.setFont(QFont("Microsoft YaHei", pt))
        # 日志区等宽字体单独设置
        if hasattr(self, 'log_text'):
            self.log_text.setFont(QFont("Consolas", 16))
        if hasattr(self, '_title_lbl'):
            self._title_lbl.setStyleSheet(
                f"color: white; font-size: {pt + 10}px; font-weight: 700; "
                "letter-spacing: 1px; background: transparent;"
            )
        if hasattr(self, '_ver_lbl'):
            self._ver_lbl.setStyleSheet(
                f"color: rgba(255,255,255,0.6); font-size: {pt + 2}px; background: transparent;"
            )
        if hasattr(self, 'cmd_file_label'):
            self.cmd_file_label.setStyleSheet(
                f"color: {Theme.TEXT_SECONDARY}; font-size: {pt + 2}px; "
                f"background: {Theme.BG_CARD}; border: 1px solid {Theme.BORDER}; "
                f"border-radius: 4px; padding: 4px 6px;"
            )
        if hasattr(self, '_cmd_tip_label'):
            self._cmd_tip_label.setStyleSheet(f"color: {Theme.TEXT_HINT}; font-size: {pt + 2}px;")
        if hasattr(self, 'save_check'):
            self.save_check.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: {pt + 2}px;")
        if hasattr(self, 'l2_uplink_check'):
            self.l2_uplink_check.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: {pt + 2}px;")
        if hasattr(self, '_log_title_label'):
            self._log_title_label.setStyleSheet(f"color: {Theme.TEXT_HINT}; font-size: {pt + 1}px;")
        self._update_form_labels(pt)
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
        if not hasattr(self, '_left_content'):
            return
        self._left_content.setMinimumHeight(self._left_content_minimum_height())

    def _left_content_minimum_height(self) -> int:
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
        if hasattr(self, '_left_panel'):
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
        max_width = max(360, self.width() // 2)
        self._left_panel.setMaximumWidth(max_width)
        sizes = self._main_splitter.sizes()
        if sizes and sizes[0] > max_width:
            total = sum(sizes)
            self._main_splitter.setSizes([max_width, max(1, total - max_width)])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_left_panel_limit()
        pt = self._calc_font_pt(self.width())
        if pt != self._current_font_pt:
            self._current_font_pt = pt
            self._apply_font_pt(pt)

    # ── 状态栏 ──────────────────────────────────────────
    def _init_statusbar(self):
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.setStatusBar(sb)

        # 左侧固定标题（永不改变）
        self._status_label = QLabel("就绪  |  交换机自动化运维工具 v1.0")
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
        self.setCentralWidget(central)

        # 顶部标题栏
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        header = self._build_header()
        root_layout.addWidget(header)

        # 主体内容
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)

        left_panel  = self.create_left_panel()
        right_panel = self.create_right_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([360, 840])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self._main_splitter = splitter
        self._left_panel = left_panel
        self._update_left_panel_limit()

        body_layout.addWidget(splitter)
        root_layout.addWidget(body)

    def _build_header(self) -> QWidget:
        """顶部渐变标题栏"""
        header = QWidget()
        header.setFixedHeight(76)
        header.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {Theme.PRIMARY_DARK}, stop:1 {Theme.ACCENT});"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        # 图标
        """
        icon_lbl = QLabel()
        icon_pix = build_app_icon().pixmap(36, 36)
        icon_lbl.setPixmap(icon_pix)
        hl.addWidget(icon_lbl)
        """

        # 标题
        self._title_lbl = QLabel("交换机自动化运维工具")
        self._title_lbl.setStyleSheet(
            "color: white; font-size: 24px; font-weight: 700; "
            "letter-spacing: 1px; background: transparent;"
        )
        hl.addWidget(self._title_lbl)
        hl.addStretch()

        # 版本号
        self._ver_lbl = QLabel("by YiLanTinYu")
        self._ver_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 16px; background: transparent;"
        )
        hl.addWidget(self._ver_lbl)
        return header

    # ── 左侧面板 ─────────────────────────────────────────
    def create_left_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumWidth(360)
        scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._left_content = panel
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        for group in (
            self._build_input_group(),
            self._build_excel_group(),
            self._build_command_group(),
            self._build_action_group(),
            self._build_ops_tools_group(),
            self._build_config_templates_group(),
        ):
            group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            layout.addWidget(group, 0)
        layout.addStretch()
        self._update_left_content_min_height()
        scroll.setWidget(panel)
        return scroll

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

        # IP
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.1  或  2001:db8::1")
        add_form_row(2, "IP 地址:", self.ip_input)

        # 端口
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        add_form_row(3, "端 口:", self.port_spin)

        # 用户名
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("admin")
        add_form_row(4, "用户名:", self.username_input)

        # 密码
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        add_form_row(5, "密 码:", self.password_input)

        layout.addLayout(form)

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
        self._cmd_tip_label = QLabel("每行一条命令，# 开头为注释")
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

        return group

    def _build_ops_tools_group(self) -> QGroupBox:
        group = QGroupBox("常用运维工具")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.ping_excel_btn = QPushButton("📡  批量 Ping")
        self.ping_excel_btn.setObjectName("btn_outline")
        self.ping_excel_btn.setToolTip("使用上方已导入到设备列表的 IP 执行批量 Ping，结果显示在右侧日志窗口")
        self.ping_excel_btn.clicked.connect(self.batch_ping_devices)
        layout.addWidget(self.ping_excel_btn)

        return group

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

        btn_row = QHBoxLayout()
        self.add_template_btn = QPushButton("＋  添加模板")
        self.add_template_btn.setObjectName("btn_outline")
        self.add_template_btn.clicked.connect(self.add_config_template)

        self.remove_template_btn = QPushButton("✂  移除选中")
        self.remove_template_btn.setObjectName("btn_neutral")
        self.remove_template_btn.clicked.connect(self.remove_config_template)

        btn_row.addWidget(self.add_template_btn)
        btn_row.addWidget(self.remove_template_btn)
        layout.addLayout(btn_row)

        return group

    # ── 右侧面板 ─────────────────────────────────────────
    def create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 设备列表
        list_group = QGroupBox("设备列表")
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(8, 16, 8, 8)

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(8)
        self.device_table.setHorizontalHeaderLabels(
            ["设备名称", "品牌", "型号", "IP 地址", "IP 版本", "端口", "用户名", "状态"]
        )
        self.device_table.setAlternatingRowColors(True)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.device_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.device_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.device_table.verticalHeader().setDefaultSectionSize(38)
        self.device_table.setShowGrid(False)
        list_layout.addWidget(self.device_table)
        layout.addWidget(list_group, stretch=5)

        # 日志
        log_group = QGroupBox("连接日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 16, 8, 8)

        # 日志工具栏
        log_toolbar = QHBoxLayout()
        self._log_title_label = QLabel("实时输出")
        self._log_title_label.setStyleSheet(f"color: {Theme.TEXT_HINT}; font-size: 15px;")
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
    def add_device(self):
        brand    = self.brand_combo.currentText()
        ip       = self.ip_input.text().strip()
        port     = self.port_spin.value()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        name     = self.name_input.text().strip()

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
        if not password:
            self._warn("请输入密码")
            return

        device = DeviceInfo(brand, ip, port, username, password, name)
        if not self.device_manager.add_device(device):
            self._warn(f"设备已存在，已跳过: {ip}:{port}")
            return
        self.update_device_table()

        self.ip_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.name_input.clear()

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
            self.device_table.setItem(i, 1, QTableWidgetItem(device.brand))
            self.device_table.setItem(i, 2, QTableWidgetItem(""))          # 型号列，连接后更新
            self.device_table.setItem(i, 3, QTableWidgetItem(display_ip))
            self.device_table.setItem(i, 4, QTableWidgetItem(version_text))
            self.device_table.setItem(i, 5, QTableWidgetItem(str(device.port)))
            self.device_table.setItem(i, 6, QTableWidgetItem(device.username))

            # 建议4：状态列使用 StatusBadge cell widget，充分利用颜色语义
            badge = StatusBadge("待连接")
            self.device_table.setCellWidget(i, 7, badge)

        self._update_device_count()

    def import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "", "Excel Files (*.xlsx *.xls)"
        )
        if not file_path:
            return

        success_count, error_count, errors = self.device_manager.import_from_excel(file_path)
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

    def _current_device_ips(self) -> List[str]:
        ips = []
        seen = set()
        for device in self.device_manager.get_devices():
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

        ips = self._current_device_ips()
        if not ips:
            QMessageBox.warning(self, "批量 Ping", "设备列表为空，请先使用上方“导入 Excel 文件”导入设备")
            return

        self.log_text.clear()
        self._ping_log_lines = []
        self._record_ping_log(f"[批量 Ping] 使用当前设备列表，共 {len(ips)} 个 IP")

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
        for item in self._config_templates:
            path = item.get("path", "")
            name = item.get("name") or os.path.basename(path)
            list_item = QListWidgetItem(name)
            list_item.setToolTip(path)
            list_item.setData(Qt.UserRole, path)
            self.config_template_list.addItem(list_item)

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
        name = item.text() if item else "模板"
        if not self._confirm_action("确认移除", f"确定要移除配置模板“{name}”吗？\n\n此操作只会从列表移除，不会删除原文件。"):
            return
        self._config_templates.pop(row)
        self._save_config_templates()
        self._refresh_config_template_list()
        self._update_left_content_min_height()
        self._log_info(f"[模板] 已移除配置模板: {name}")

    def open_config_template(self, item: QListWidgetItem):
        file_path = item.data(Qt.UserRole)
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

    def start_connection(self):
        devices = self.device_manager.get_devices()
        if not devices:
            QMessageBox.warning(self, "警告", "请先添加设备")
            return

        self._total_count    = len(devices)
        self._connected_count = 0

        self.connect_btn.setEnabled(False)
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
        for i in range(self.device_table.rowCount()):
            badge = self.device_table.cellWidget(i, 7)
            if isinstance(badge, StatusBadge):
                badge.setText("⏳ 连接中")
            else:
                b = StatusBadge("⏳ 连接中")
                self.device_table.setCellWidget(i, 7, b)

        self.ssh_manager = SSHManager(max_connections=5)
        self.ssh_manager.command_file      = self._command_file
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
            cell = self.device_table.item(i, 3)
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
        badge = self.device_table.cellWidget(row, 7)
        if isinstance(badge, StatusBadge):
            badge.setText(status_text)
        else:
            badge = StatusBadge(status_text)
            self.device_table.setCellWidget(row, 7, badge)

        # 型号列同步更新
        if model:
            self.device_table.setItem(row, 2, QTableWidgetItem(model))

    def handle_result(self, result: dict):
        """全量结果兜底：补充型号列、更新连接计数（逐设备信号已处理状态列）"""
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
            self.device_table.setItem(row, 2, QTableWidgetItem(model_detected))

        # 状态列兜底（处理 on_device_status 可能未触发的极端情况）
        badge = self.device_table.cellWidget(row, 7)
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
        self.add_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        # 先跳到 100% 给用户一个"任务完成"的视觉确认，再收缩隐藏
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        QTimer.singleShot(800, self._hide_progress)   # 800ms 后收缩消失

        results = self.ssh_manager.get_results() if self.ssh_manager else []
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
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择命令文件", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if not file_path:
            return
        self._command_file = file_path
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
        self.cmd_file_label.setText("SSH_command.txt  (默认)")
        self.cmd_file_label.setToolTip("")
        self._log_info("[命令]  已恢复使用默认命令文件 SSH_command.txt")
        self._set_status("命令文件已恢复为默认")
        QTimer.singleShot(3000, self._update_device_count)

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
