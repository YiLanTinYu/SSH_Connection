#!/usr/bin/env python3
"""AOMT visual design tokens and application stylesheet."""


class Theme:
    """AOMT operations-console design tokens."""

    PRIMARY = "#0369A1"
    PRIMARY_LIGHT = "#E7F2F8"
    PRIMARY_DARK = "#0B4A5A"
    ACCENT = "#0F9F8F"
    CORAL = "#E6644F"

    BG_MAIN = "#EEF3F4"
    BG_PANEL = "#FFFFFF"
    BG_CARD = "#F6F9F9"
    BG_HEADER = "#E8EFF1"
    BG_INPUT = "#FFFFFF"
    BG_DEEP = "#073B49"
    BG_DEEP_ALT = "#082F3B"

    TEXT_PRIMARY = "#18343C"
    TEXT_SECONDARY = "#49656D"
    TEXT_HINT = "#71888E"
    TEXT_WHITE = "#F8FFFD"
    TEXT_HEADER = "#DDF7F4"

    SUCCESS = "#0F8F80"
    SUCCESS_BG = "#DFF4EF"
    WARNING = "#D18A24"
    WARNING_BG = "#FFF4D9"
    ERROR = "#D95445"
    ERROR_BG = "#FDE9E5"
    INFO = "#0369A1"
    INFO_BG = "#E7F2F8"

    BORDER = "#CFDDE0"
    BORDER_FOCUS = "#168EA5"

    BTN_PRIMARY = "#0369A1"
    BTN_PRIMARY_H = "#075985"
    BTN_SUCCESS = "#0F8F80"
    BTN_SUCCESS_H = "#0B7469"
    BTN_DANGER = "#D95445"
    BTN_DANGER_H = "#BF4136"
    BTN_NEUTRAL = "#45656D"
    BTN_NEUTRAL_H = "#34515A"

    SHADOW = "rgba(6,56,71,0.10)"
    DIVIDER = "#DCE6E8"

    PROGRESS_BG = "#164B58"
    PROGRESS_CHUNK = "#16C7B7"

    ROW_ALT = "#F5F8F8"
    ROW_HOVER = "#EAF5F4"
    ROW_SELECT = "#D9EFEC"

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
    border: 1px solid #2B6875;
    border-radius: 5px;
    padding: 6px 9px;
    font-size: 13px;
    font-weight: 400;
}}
QMenuBar {{
    background: #F6FAFA;
    color: {Theme.TEXT_PRIMARY};
    border-bottom: 1px solid {Theme.BORDER};
    padding: 4px 8px;
    font-size: 18px;
}}
QMenuBar::item {{
    background: transparent;
    border-radius: 4px;
    padding: 6px 11px;
}}
QMenuBar::item:selected {{
    background: #DDEFF0;
    color: {Theme.PRIMARY_DARK};
}}
QMenu {{
    background: #FFFFFF;
    color: {Theme.TEXT_PRIMARY};
    border: 1px solid {Theme.BORDER};
    padding: 5px;
    font-size: 18px;
}}
QMenu::item {{
    border-radius: 4px;
    padding: 8px 30px 8px 13px;
}}
QMenu::item:selected {{
    background: #DDEFF0;
    color: {Theme.PRIMARY_DARK};
}}
QMenu::separator {{
    height: 1px;
    background: {Theme.BORDER};
    margin: 5px 8px;
}}

/* GroupBox */
QGroupBox {{
    background-color: {Theme.BG_PANEL};
    border: 1px solid {Theme.BORDER};
    border-radius: 6px;
    margin-top: 14px;
    padding: 13px 11px 11px 11px;
    font-size: 13px;
    font-weight: 600;
    color: {Theme.TEXT_PRIMARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 1px 7px;
    left: 9px;
    color: {Theme.PRIMARY_DARK};
    background-color: {Theme.BG_PANEL};
    font-size: 13px;
    font-weight: 700;
}}
QGroupBox#device_list_group,
QGroupBox#connection_log_group {{
    background: {Theme.BG_PANEL};
    border: 1px solid {Theme.BORDER};
}}
QGroupBox#device_list_group {{
    border-top: 3px solid {Theme.PRIMARY};
}}
QGroupBox#connection_log_group {{
    border-top: 3px solid {Theme.ACCENT};
}}
QGroupBox#device_list_group::title,
QGroupBox#connection_log_group::title {{
    background-color: {Theme.BG_PANEL};
}}

/* 输入框 */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {Theme.BG_INPUT};
    border: 1px solid {Theme.BORDER};
    border-radius: 5px;
    padding: 6px 9px;
    font-size: 13px;
    color: {Theme.TEXT_PRIMARY};
    min-height: 28px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {Theme.BORDER_FOCUS};
    background-color: #FFFFFF;
    selection-background-color: {Theme.PRIMARY};
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
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 7px 13px;
    font-size: 13px;
    font-weight: 600;
    min-height: 30px;
}}
QPushButton:disabled {{
    background-color: #DDE7E7;
    color: #8AA0A4;
}}

/* 主操作按钮 */
QPushButton#btn_primary {{
    background-color: {Theme.BTN_PRIMARY};
    color: white;
}}
QPushButton#btn_primary:hover {{
    background-color: {Theme.BTN_PRIMARY_H};
    border-color: #59A7C5;
}}
QPushButton#btn_primary:pressed {{
    background-color: {Theme.PRIMARY_DARK};
}}

/* 成功按钮（开始连接） */
QPushButton#btn_success {{
    background-color: {Theme.BTN_SUCCESS};
    color: white;
    font-size: 13px;
    min-height: 36px;
    border-radius: 6px;
    letter-spacing: 0px;
}}
QPushButton#btn_success:hover {{
    background-color: {Theme.BTN_SUCCESS_H};
    border-color: #64B9AE;
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
    border: 1px solid #9CBCC3;
}}
QPushButton#btn_outline:hover {{
    background-color: {Theme.INFO_BG};
    border-color: #4F9DB6;
}}

QPushButton#tool_button {{
    background-color: {Theme.BG_PANEL};
    color: {Theme.TEXT_PRIMARY};
    border: 1px solid {Theme.BORDER};
    text-align: left;
    padding: 9px 13px;
    min-height: 34px;
}}
QPushButton#tool_button:hover {{
    background-color: #F0F7F7;
    color: {Theme.PRIMARY_DARK};
    border-color: #7CAEB8;
}}
QPushButton#toolbar_button {{
    background-color: transparent;
    color: {Theme.TEXT_SECONDARY};
    border: 1px solid {Theme.BORDER};
    padding: 5px 10px;
    min-height: 26px;
}}
QPushButton#toolbar_button:hover {{
    background-color: {Theme.BG_CARD};
    color: {Theme.PRIMARY_DARK};
    border-color: #91B4BC;
}}
QPushButton:focus {{
    border: 1px solid {Theme.BORDER_FOCUS};
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
    border-radius: 5px;
    gridline-color: {Theme.DIVIDER};
    alternate-background-color: {Theme.ROW_ALT};
    selection-background-color: {Theme.ROW_SELECT};
    selection-color: {Theme.PRIMARY_DARK};
    font-size: 13px;
    outline: none;
}}
QTableWidget::item {{
    padding: 6px 9px;
    border-bottom: 1px solid {Theme.DIVIDER};
}}
QTableWidget::item:hover {{
    background-color: {Theme.ROW_HOVER};
}}
QHeaderView::section {{
    background-color: #0B4A5A;
    color: {Theme.TEXT_HEADER};
    font-weight: 700;
    font-size: 13px;
    padding: 8px 9px;
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
    border-radius: 5px;
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
    padding: 5px 12px;
    min-height: 34px;
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
    background: rgba(126,157,163,0.12);
    width: 8px;
    margin: 2px 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: #9EB8BD;
    border-radius: 4px;
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
    background: rgba(126,157,163,0.12);
    height: 8px;
    margin: 0 2px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: #9EB8BD;
    border-radius: 4px;
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
