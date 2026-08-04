"""Application icon helpers shared by AOMT windows."""

import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)


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
