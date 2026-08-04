"""Device-dependent maintenance tool launcher panel."""

from functools import partial

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QGridLayout, QGroupBox, QPushButton


class DeviceToolsPanel(QGroupBox):
    """Present device tool actions while leaving all work to the main controller."""

    tool_requested = pyqtSignal(str)

    TOOL_DEFINITIONS = (
        (
            "ssh_console",
            "ssh_console_btn",
            "SSH 交互终端",
            "使用共享目标范围选择设备并打开交互式 SSH 会话",
            False,
        ),
        (
            "batch_ping",
            "ping_excel_btn",
            "批量 Ping",
            "使用共享目标范围或临时 CIDR 网段执行批量 Ping，"
            "结果显示在右侧日志窗口",
            False,
        ),
        (
            "port_check",
            "port_check_btn",
            "端口检测",
            "批量检测指定 TCP 端口，不发送应用数据",
            True,
        ),
        (
            "ssh_login_test",
            "ssh_test_btn",
            "SSH 登录测试",
            "仅验证 SSH 认证，不执行任何设备命令",
            True,
        ),
        (
            "traceroute",
            "traceroute_btn",
            "路由跟踪",
            "批量执行系统 Traceroute/Tracert",
            True,
        ),
        (
            "health_check",
            "health_check_btn",
            "一键设备巡检",
            "只读采集 H3C/Comware、Huawei VRP 的 CPU、内存、温度、"
            "风扇、电源和接口摘要",
            True,
        ),
        (
            "terminal_locate",
            "terminal_locate_btn",
            "IP/MAC 终端定位",
            "通过 H3C/Comware、Huawei VRP 的 ARP 表和 MAC 地址表"
            "定位终端接口",
            True,
        ),
        (
            "interface_diagnosis",
            "interface_diag_btn",
            "接口综合诊断",
            "只读检查 H3C/Comware、Huawei VRP 接口状态、速率、双工、"
            "VLAN 和光模块信息",
            True,
        ),
        (
            "config_backup",
            "config_backup_btn",
            "配置备份",
            "按设备建立目录，保存版本化 CFG 配置和 JSON 元数据",
            True,
        ),
    )

    def __init__(self, parent=None):
        super().__init__("设备检测与配置", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.tools_layout = QGridLayout(self)
        self.tools_layout.setHorizontalSpacing(8)
        self.tools_layout.setVerticalSpacing(8)
        self.tool_buttons = []
        self.maintenance_buttons = []

        for row, (key, attribute, text, tooltip, is_maintenance) in enumerate(
            self.TOOL_DEFINITIONS
        ):
            button = QPushButton(text)
            button.setObjectName("btn_outline")
            button.setToolTip(tooltip)
            button.clicked.connect(partial(self._emit_tool, key))
            setattr(self, attribute, button)
            self.tool_buttons.append(button)
            if is_maintenance:
                self.maintenance_buttons.append(button)
            self.tools_layout.addWidget(button, row, 0)

        self.tools_layout.setColumnStretch(0, 1)
        self.tools_layout.setColumnStretch(1, 0)

    def _emit_tool(self, key: str, _checked: bool = False) -> None:
        self.tool_requested.emit(key)
