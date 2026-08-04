from PyQt5.QtWidgets import QLabel

from ui.status_badge import StatusBadge


def test_status_badge_is_reusable_and_keeps_known_states():
    assert issubclass(StatusBadge, QLabel)
    assert {"待连接", "连接成功", "连接中"} <= set(StatusBadge._STYLES)
