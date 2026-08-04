import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QListWidgetItem

from ui.config_templates_panel import ConfigTemplatesPanel


def test_config_templates_panel_controls_and_signals():
    app = QApplication.instance() or QApplication([])
    panel = ConfigTemplatesPanel()
    events = []
    panel.open_requested.connect(lambda item: events.append(("open", item.text())))
    panel.use_requested.connect(lambda: events.append(("use", None)))
    panel.add_requested.connect(lambda: events.append(("add", None)))
    panel.remove_requested.connect(lambda: events.append(("remove", None)))

    assert panel.config_template_list.minimumHeight() == 118
    assert panel.config_template_list.maximumHeight() == 180
    assert panel.use_template_btn.objectName() == "btn_primary"
    assert panel.add_template_btn.objectName() == "btn_outline"
    assert panel.remove_template_btn.objectName() == "btn_neutral"

    item = QListWidgetItem("开局配置")
    panel.config_template_list.addItem(item)
    panel.config_template_list.itemDoubleClicked.emit(item)
    panel.use_template_btn.click()
    panel.add_template_btn.click()
    panel.remove_template_btn.click()

    assert events == [
        ("open", "开局配置"),
        ("use", None),
        ("add", None),
        ("remove", None),
    ]
    assert app is not None
