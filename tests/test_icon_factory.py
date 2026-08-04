import os

from PyQt5.QtWidgets import QApplication

from ui.icon_factory import build_app_icon, make_icon


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_icon_factory_builds_non_null_icons():
    app = QApplication.instance() or QApplication([])

    assert not make_icon("#0F9F8F").isNull()
    assert not make_icon("#0369A1", "rect").isNull()
    assert not build_app_icon().isNull()
    assert app is not None
