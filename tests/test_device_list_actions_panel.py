import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ui.device_list_actions_panel import DeviceListActionsPanel


def test_device_list_actions_panel_styles_and_signals():
    app = QApplication.instance() or QApplication([])
    panel = DeviceListActionsPanel()
    events = []
    panel.remove_selected_requested.connect(lambda: events.append("remove"))
    panel.clear_all_requested.connect(lambda: events.append("clear"))

    assert panel.delete_btn.text() == "移除选中"
    assert panel.delete_btn.objectName() == "btn_neutral"
    assert panel.clear_btn.text() == "清空列表"
    assert panel.clear_btn.objectName() == "btn_danger"

    panel.delete_btn.click()
    panel.clear_btn.click()
    assert events == ["remove", "clear"]
    assert app is not None
