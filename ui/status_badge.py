"""Status badge used by device tables."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel

from ui.theme import Theme


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
