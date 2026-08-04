import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QLabel

from ui.main_window_layout import MainWindowLayoutBuilder


def test_layout_builder_creates_sidebar_page_with_existing_groups():
    app = QApplication.instance() or QApplication([])
    first = QLabel("first")
    second = QLabel("second")
    page = MainWindowLayoutBuilder.build_sidebar_page((first, second))
    try:
        assert page.objectName() == "sidebar_page"
        assert page.layout().indexOf(first) == 0
        assert page.layout().indexOf(second) == 1
    finally:
        page.close()


def test_layout_builder_resolves_bundled_icon_families():
    assert MainWindowLayoutBuilder.sidebar_icon_directory().name == "phosphor"
    assert MainWindowLayoutBuilder.lucide_icon_directory().name == "lucide"
