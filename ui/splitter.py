"""Custom splitter used by the main workspace."""

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QSplitter, QSplitterHandle

from ui.theme import Theme


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
