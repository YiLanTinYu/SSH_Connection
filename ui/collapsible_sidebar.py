"""Compact icon rail with one expandable workspace page."""

from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtCore import QByteArray, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def _render_svg_icon(path: Path, color: str, size: int = 28) -> QPixmap:
    """Render a currentColor SVG without modifying the source asset."""
    svg = path.read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


class SidebarToolButton(QToolButton):
    """Icon-only rail button with a restrained active rail."""

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.isChecked():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#E6644F"))
        painter.drawRoundedRect(1, 10, 3, self.height() - 20, 2, 2)


class CollapsibleSidebar(QWidget):
    """A fixed icon rail and a single click-to-expand content panel."""

    expansionChanged = pyqtSignal(bool)
    pageChanged = pyqtSignal(str)

    COLLAPSED_WIDTH = 68
    MIN_EXPANDED_WIDTH = 420

    def __init__(self, icon_dir: Path, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("collapsible_sidebar")
        self._icon_dir = Path(icon_dir)
        self._buttons: Dict[str, SidebarToolButton] = {}
        self._page_indexes: Dict[str, int] = {}
        self._page_contents: Dict[str, QWidget] = {}
        self._current_key: Optional[str] = None
        self._expanded = False
        self._expanded_maximum = 16777215

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._rail = QFrame()
        self._rail.setObjectName("sidebar_rail")
        self._rail.setFixedWidth(self.COLLAPSED_WIDTH)
        rail_layout = QVBoxLayout(self._rail)
        rail_layout.setContentsMargins(10, 14, 10, 14)
        rail_layout.setSpacing(10)
        self._rail_layout = rail_layout
        rail_layout.addStretch()
        root.addWidget(self._rail)

        self._content_frame = QFrame()
        self._content_frame.setObjectName("sidebar_content")
        content_layout = QVBoxLayout(self._content_frame)
        content_layout.setContentsMargins(16, 14, 12, 12)
        content_layout.setSpacing(9)

        self._title = QLabel()
        self._title.setObjectName("sidebar_page_title")
        self._title.setMinimumHeight(38)
        content_layout.addWidget(self._title)

        self._stack = QStackedWidget()
        self._stack.setObjectName("sidebar_stack")
        content_layout.addWidget(self._stack, 1)
        root.addWidget(self._content_frame, 1)

        self._content_frame.hide()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._apply_style()
        self._apply_width_constraints()

    def _apply_style(self):
        self.setStyleSheet(
            """
            QFrame#sidebar_rail {
                background: #073B49;
                border: none;
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
            }
            QToolButton#sidebar_nav_button {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 0;
            }
            QToolButton#sidebar_nav_button:hover {
                background: #0D5261;
                border-color: #236B78;
            }
            QToolButton#sidebar_nav_button:checked {
                background: #0B718A;
                border-color: #46AEB9;
            }
            QFrame#sidebar_content {
                background: #F5F8F8;
                border: 1px solid #CFDDE0;
                border-left: none;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QLabel#sidebar_page_title {
                color: #0B4A5A;
                background: transparent;
                font-size: 18px;
                font-weight: 700;
                padding: 2px 4px;
            }
            QStackedWidget#sidebar_stack {
                background: transparent;
                border: none;
            }
            QScrollArea#sidebar_page_scroll,
            QScrollArea#sidebar_page_scroll > QWidget > QWidget {
                background: transparent;
                border: none;
            }
            """
        )

    def add_page(self, key: str, title: str, icon_filename: str, content: QWidget):
        if key in self._buttons:
            raise ValueError(f"Duplicate sidebar page: {key}")

        button = SidebarToolButton()
        button.setObjectName("sidebar_nav_button")
        button.setCheckable(True)
        button.setAutoExclusive(False)
        button.setFixedSize(48, 46)
        button.setIconSize(QSize(25, 25))
        button.setToolTip(title)
        button.setAccessibleName(title)

        icon_path = self._icon_dir / icon_filename
        icon = QIcon()
        icon.addPixmap(_render_svg_icon(icon_path, "#A7C0C5"), QIcon.Normal, QIcon.Off)
        icon.addPixmap(_render_svg_icon(icon_path, "#F8FFFD"), QIcon.Normal, QIcon.On)
        icon.addPixmap(_render_svg_icon(icon_path, "#64818A"), QIcon.Disabled, QIcon.Off)
        button.setIcon(icon)
        button.clicked.connect(lambda checked=False, page_key=key: self._activate(page_key))

        self._rail_layout.insertWidget(self._rail_layout.count() - 1, button)
        self._buttons[key] = button

        scroll = QScrollArea()
        scroll.setObjectName("sidebar_page_scroll")
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        scroll.setWidget(content)

        self._page_indexes[key] = self._stack.addWidget(scroll)
        self._page_contents[key] = content
        if self._current_key is None:
            self._current_key = key
            self._title.setText(title)
            self._stack.setCurrentIndex(self._page_indexes[key])

    def _activate(self, key: str):
        if self._expanded and key == self._current_key:
            self.set_expanded(False)
            return

        self._current_key = key
        self._stack.setCurrentIndex(self._page_indexes[key])
        self._title.setText(self._buttons[key].toolTip())
        for page_key, button in self._buttons.items():
            button.setChecked(page_key == key)
        self.set_expanded(True)
        self.refresh_current_page_geometry()
        self.pageChanged.emit(key)

    def set_expanded(self, expanded: bool):
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self._content_frame.setVisible(expanded)
        if not expanded:
            for button in self._buttons.values():
                button.setChecked(False)
        elif self._current_key:
            self._buttons[self._current_key].setChecked(True)
        self._apply_width_constraints()
        self.updateGeometry()
        self.expansionChanged.emit(expanded)

    def _apply_width_constraints(self):
        if self._expanded:
            self.setMinimumWidth(self.MIN_EXPANDED_WIDTH)
            self.setMaximumWidth(max(self.MIN_EXPANDED_WIDTH, self._expanded_maximum))
        else:
            self.setFixedWidth(self.COLLAPSED_WIDTH)

    def set_expanded_maximum_width(self, width: int):
        self._expanded_maximum = max(self.MIN_EXPANDED_WIDTH, int(width))
        self._apply_width_constraints()

    def is_expanded(self) -> bool:
        return self._expanded

    def current_page_key(self) -> Optional[str]:
        return self._current_key

    def current_page_content(self) -> Optional[QWidget]:
        return self._page_contents.get(self._current_key or "")

    def current_page_minimum_height(self) -> int:
        content = self.current_page_content()
        return content.minimumSizeHint().height() if content else 0

    def refresh_current_page_geometry(self):
        content = self.current_page_content()
        if content is not None:
            content.setMinimumHeight(content.minimumSizeHint().height())
            content.updateGeometry()
        self._stack.updateGeometry()

    def set_page_title_font_size(self, pixel_size: int):
        self._title.setStyleSheet(
            "color: #0B4A5A; background: transparent; "
            f"font-size: {max(18, int(pixel_size))}px; font-weight: 700; "
            "padding: 2px 4px;"
        )

    def button(self, key: str) -> SidebarToolButton:
        return self._buttons[key]

    def sizeHint(self) -> QSize:
        width = self.MIN_EXPANDED_WIDTH if self._expanded else self.COLLAPSED_WIDTH
        return QSize(width, super().sizeHint().height())
