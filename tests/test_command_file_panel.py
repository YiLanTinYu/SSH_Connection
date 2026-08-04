import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QLabel

from ui.command_file_panel import CommandFilePanel


def test_command_file_panel_builds_modes_and_default_source():
    app = QApplication.instance() or QApplication([])
    labels = []

    def create_label(text):
        label = QLabel(f"form:{text}")
        labels.append(label)
        return label

    panel = CommandFilePanel(create_label)

    assert [
        panel.cmd_mode_combo.itemData(index)
        for index in range(panel.cmd_mode_combo.count())
    ] == ["single", "per_device"]
    assert panel.cmd_file_label.text() == "SSH_command.txt  (默认)"
    assert panel.cmd_file_label.wordWrap() is True
    assert [label.text() for label in labels] == ["form:模式:", "form:文件:"]
    assert "每行一条" in panel._cmd_tip_label.text()
    assert app is not None


def test_command_file_panel_forwards_actions():
    app = QApplication.instance() or QApplication([])
    panel = CommandFilePanel()
    events = []
    panel.mode_changed.connect(lambda: events.append("mode"))
    panel.browse_requested.connect(lambda: events.append("browse"))
    panel.reset_requested.connect(lambda: events.append("reset"))

    panel.cmd_mode_combo.setCurrentIndex(1)
    panel.cmd_browse_btn.click()
    panel.cmd_reset_btn.click()

    assert events == ["mode", "browse", "reset"]
    assert app is not None
