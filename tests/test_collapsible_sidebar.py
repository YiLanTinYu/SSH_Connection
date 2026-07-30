import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from ui.collapsible_sidebar import CollapsibleSidebar


def _page(text):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel(text))
    return page


def test_sidebar_expands_switches_and_collapses_without_recreating_pages():
    app = QApplication.instance() or QApplication([])
    icon_dir = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "icons"
        / "phosphor"
    )
    sidebar = CollapsibleSidebar(icon_dir)
    devices_page = _page("devices")
    tools_page = _page("tools")
    sidebar.add_page("devices", "设备管理", "devices.svg", devices_page)
    sidebar.add_page("tools", "运维工具", "toolbox.svg", tools_page)

    assert sidebar.width() == CollapsibleSidebar.COLLAPSED_WIDTH
    assert not sidebar.is_expanded()
    assert not sidebar.button("devices").icon().isNull()

    sidebar.button("devices").click()
    app.processEvents()
    assert sidebar.is_expanded()
    assert sidebar.current_page_key() == "devices"
    assert sidebar.current_page_content() is devices_page
    assert sidebar.button("devices").isChecked()

    sidebar.button("tools").click()
    app.processEvents()
    assert sidebar.is_expanded()
    assert sidebar.current_page_key() == "tools"
    assert sidebar.current_page_content() is tools_page
    assert not sidebar.button("devices").isChecked()
    assert sidebar.button("tools").isChecked()

    sidebar.button("tools").click()
    app.processEvents()
    assert not sidebar.is_expanded()
    assert sidebar.width() == CollapsibleSidebar.COLLAPSED_WIDTH
    assert not sidebar.button("tools").isChecked()
