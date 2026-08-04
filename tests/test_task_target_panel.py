import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ui.task_target_panel import TaskTargetPanel


def test_task_target_panel_builds_scope_and_default_state():
    app = QApplication.instance() or QApplication([])
    panel = TaskTargetPanel()

    assert [
        panel.task_scope_combo.itemData(index)
        for index in range(panel.task_scope_combo.count())
    ] == ["all", "filtered", "selected"]
    assert panel.task_target_summary.text() == "当前设备列表为空"
    assert panel.task_target_summary.wordWrap() is True
    assert panel.clear_task_targets_btn.isEnabled() is False
    assert "共享此目标范围" in panel.hint_label.text()
    assert app is not None


def test_task_target_panel_forwards_actions():
    app = QApplication.instance() or QApplication([])
    panel = TaskTargetPanel()
    events = []
    panel.scope_changed.connect(lambda: events.append("scope"))
    panel.manage_targets_requested.connect(lambda: events.append("manage"))
    panel.clear_targets_requested.connect(lambda: events.append("clear"))

    panel.task_scope_combo.setCurrentIndex(1)
    panel.manage_task_targets_btn.click()
    panel.clear_task_targets_btn.setEnabled(True)
    panel.clear_task_targets_btn.click()

    assert events == ["scope", "manage", "clear"]
    assert app is not None
