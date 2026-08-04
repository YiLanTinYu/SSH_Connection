import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ui.local_tools_panel import LocalToolsPanel


def test_local_tools_panel_builds_expected_tools_and_tips():
    app = QApplication.instance() or QApplication([])
    panel = LocalToolsPanel()

    assert [button.text() for button in panel.tool_buttons] == [
        "串口控制台",
        "文件传输服务",
        "网络抓包",
        "子网计算",
        "配置对比",
    ]
    assert all(button.objectName() == "btn_outline" for button in panel.tool_buttons)
    assert "COM" in panel.serial_console_btn.toolTip()
    assert "pcapng" in panel.packet_capture_btn.toolTip()
    assert "IPv4/IPv6" in panel.subnet_calc_btn.toolTip()
    assert app is not None


def test_local_tools_panel_emits_every_tool_key():
    app = QApplication.instance() or QApplication([])
    panel = LocalToolsPanel()
    requested = []
    panel.tool_requested.connect(requested.append)

    for button in panel.tool_buttons:
        button.click()

    assert requested == [definition[0] for definition in panel.TOOL_DEFINITIONS]
    assert app is not None
