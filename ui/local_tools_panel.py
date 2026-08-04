"""Local operations tool launcher panel."""

from functools import partial

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QGridLayout, QGroupBox, QPushButton


class LocalToolsPanel(QGroupBox):
    """Present tools that do not depend on the managed device inventory."""

    tool_requested = pyqtSignal(str)

    TOOL_DEFINITIONS = (
        (
            "serial_console",
            "serial_console_btn",
            "串口控制台",
            "通过 Windows COM 串口连接交换机 Console",
        ),
        (
            "file_transfer",
            "file_transfer_btn",
            "文件传输服务",
            "临时启动 FTP 或 TFTP 服务，与交换机上传、下载文件",
        ),
        (
            "packet_capture",
            "packet_capture_btn",
            "网络抓包",
            "调用 Wireshark Dumpcap 抓取本机网卡可见流量并保存为 pcapng",
        ),
        (
            "subnet_calculator",
            "subnet_calc_btn",
            "子网计算",
            "计算 IPv4/IPv6 网络范围和地址数量",
        ),
        (
            "config_diff",
            "config_diff_btn",
            "配置对比",
            "比较两份本地配置文件的差异",
        ),
    )

    def __init__(self, parent=None):
        super().__init__("无需设备库的本机工具", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.tools_layout = QGridLayout(self)
        self.tools_layout.setHorizontalSpacing(8)
        self.tools_layout.setVerticalSpacing(8)
        self.tool_buttons = []

        for row, (key, attribute, text, tooltip) in enumerate(
            self.TOOL_DEFINITIONS
        ):
            button = QPushButton(text)
            button.setObjectName("btn_outline")
            button.setToolTip(tooltip)
            button.clicked.connect(partial(self._emit_tool, key))
            setattr(self, attribute, button)
            self.tool_buttons.append(button)
            self.tools_layout.addWidget(button, row, 0)

        self.tools_layout.setColumnStretch(0, 1)
        self.tools_layout.setColumnStretch(1, 0)

    def _emit_tool(self, key: str, _checked: bool = False) -> None:
        self.tool_requested.emit(key)
