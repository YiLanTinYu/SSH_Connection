"""AOMT brand header widget."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt5.QtWidgets import QWidget


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
