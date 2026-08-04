from PyQt5.QtWidgets import QWidget

from ui.aurora_header import AuroraHeader


def test_aurora_header_is_a_reusable_widget():
    assert issubclass(AuroraHeader, QWidget)
