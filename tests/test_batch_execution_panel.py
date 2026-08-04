import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ui.batch_execution_panel import BatchExecutionPanel


def test_batch_execution_panel_defaults_and_start_signal():
    app = QApplication.instance() or QApplication([])
    panel = BatchExecutionPanel()
    events = []
    panel.start_requested.connect(lambda: events.append("start"))

    assert panel.title() == "批量执行"
    assert panel.save_check.isChecked() is False
    assert panel.l2_uplink_check.isChecked() is False
    assert "自动发送设备保存配置命令" in panel.save_check.toolTip()
    assert "ARP" in panel.l2_uplink_check.toolTip()
    assert panel.connect_btn.objectName() == "btn_success"

    panel.save_check.setChecked(True)
    panel.l2_uplink_check.setChecked(True)
    panel.connect_btn.click()

    assert panel.save_check.isChecked() is True
    assert panel.l2_uplink_check.isChecked() is True
    assert events == ["start"]
    assert app is not None
