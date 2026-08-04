import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ui.device_workspace import DeviceWorkspace


def test_device_workspace_builds_expected_controls_and_table():
    app = QApplication.instance() or QApplication([])
    workspace = DeviceWorkspace()

    headers = [
        workspace.device_table.horizontalHeaderItem(column).text()
        for column in range(workspace.device_table.columnCount())
    ]
    assert headers == [
        "设备名称",
        "分组",
        "标签",
        "品牌",
        "型号",
        "IP 地址",
        "IP 版本",
        "端口",
        "用户名",
        "状态",
    ]
    assert workspace.group_filter_combo.currentData() == ""
    assert [
        workspace.execution_scope_combo.itemData(index)
        for index in range(workspace.execution_scope_combo.count())
    ] == ["all", "filtered", "selected"]
    assert workspace.log_text.isReadOnly() is True
    assert workspace.log_text.font().pointSize() == 16
    assert app is not None


def test_device_workspace_forwards_interaction_signals():
    app = QApplication.instance() or QApplication([])
    workspace = DeviceWorkspace()
    events = []

    workspace.search_changed.connect(lambda: events.append("search"))
    workspace.group_filter_changed.connect(lambda: events.append("group"))
    workspace.execution_scope_changed.connect(lambda: events.append("scope"))
    workspace.view_logs_requested.connect(lambda: events.append("logs"))
    workspace.clear_log_requested.connect(lambda: events.append("clear"))
    workspace.result_center_requested.connect(lambda: events.append("results"))

    workspace.device_search_input.setText("SW1")
    workspace.group_filter_combo.addItem("核心", "核心")
    workspace.group_filter_combo.setCurrentIndex(1)
    workspace.execution_scope_combo.setCurrentIndex(1)
    workspace.log_btn.click()
    workspace.clear_log_btn.click()
    workspace.result_center_btn.click()

    assert events == [
        "search",
        "group",
        "scope",
        "logs",
        "clear",
        "results",
    ]
    assert app is not None
