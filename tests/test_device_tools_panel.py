import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ui.device_tools_panel import DeviceToolsPanel


def test_device_tools_panel_builds_expected_order_and_busy_set():
    app = QApplication.instance() or QApplication([])
    panel = DeviceToolsPanel()

    assert [button.text() for button in panel.tool_buttons] == [
        "SSH 交互终端",
        "批量 Ping",
        "端口检测",
        "SSH 登录测试",
        "路由跟踪",
        "一键设备巡检",
        "IP/MAC 终端定位",
        "接口综合诊断",
        "配置备份",
    ]
    assert panel.maintenance_buttons == panel.tool_buttons[2:]
    assert all(button.objectName() == "btn_outline" for button in panel.tool_buttons)
    assert "CIDR" in panel.ping_excel_btn.toolTip()
    assert "JSON" in panel.config_backup_btn.toolTip()
    assert app is not None


def test_device_tools_panel_emits_tool_keys_for_every_button():
    app = QApplication.instance() or QApplication([])
    panel = DeviceToolsPanel()
    requested = []
    panel.tool_requested.connect(requested.append)

    for button in panel.tool_buttons:
        button.click()

    assert requested == [definition[0] for definition in panel.TOOL_DEFINITIONS]
    assert app is not None
