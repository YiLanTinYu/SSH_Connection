#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Reusable target selector for batch maintenance tools."""

import ipaddress
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from config.device_config import DeviceInfo
from utils.maintenance_tools import normalize_host


MODE_TITLES = {
    "ping": "批量 Ping 目标",
    "port": "端口检测目标",
    "ssh_login": "SSH 登录测试目标",
    "traceroute": "路由跟踪目标",
    "health_check": "一键设备巡检目标",
    "terminal_locate": "IP/MAC 终端定位目标",
    "interface_diagnosis": "接口综合诊断目标",
}

SSH_MODES = {
    "ssh_login",
    "health_check",
    "terminal_locate",
    "interface_diagnosis",
}

MAX_PING_NETWORK_TARGETS = 4096


def parse_manual_targets(
    text: str,
    *,
    allow_port: bool = False,
    default_port: int = 22,
) -> list[tuple[str, int]]:
    """Parse, validate and deduplicate manually entered hosts."""
    tokens = re.split(r"[\s,，;；]+", str(text or "").strip())
    targets = []
    seen = set()
    for token in tokens:
        value = token.strip()
        if not value:
            continue
        host, port = _split_host_port(value, default_port, allow_port)
        _validate_host(host)
        key = (host.lower(), port if allow_port else 0)
        if key in seen:
            continue
        seen.add(key)
        targets.append((host, port))
    return targets


def expand_ping_networks(
    text: str,
    *,
    max_targets: int = MAX_PING_NETWORK_TARGETS,
) -> list[str]:
    """Expand CIDR networks into deduplicated addresses suitable for Ping."""
    tokens = re.split(r"[\s,，;；]+", str(text or "").strip())
    targets = []
    seen = set()
    for token in tokens:
        value = token.strip()
        if not value:
            continue
        if "/" not in value:
            raise ValueError(f"网段必须包含前缀长度：{value}")
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise ValueError(f"网段格式无效：{value}") from exc

        if network.version == 4 and network.prefixlen <= 30:
            estimated_hosts = network.num_addresses - 2
        elif network.version == 6 and network.prefixlen <= 126:
            estimated_hosts = network.num_addresses - 1
        else:
            estimated_hosts = network.num_addresses
        if estimated_hosts > max_targets:
            raise ValueError(
                f"网段 {network.with_prefixlen} 包含约 "
                f"{estimated_hosts:,} 个可 Ping 地址，超过单次上限 "
                f"{max_targets:,} 个；请缩小前缀范围"
            )

        for address in network.hosts():
            host = str(address)
            if host in seen:
                continue
            seen.add(host)
            targets.append(host)
            if len(targets) > max_targets:
                raise ValueError(
                    f"合并后的网段目标超过单次上限 {max_targets:,} 个；"
                    "请减少网段数量或缩小前缀范围"
                )
    return targets


def _split_host_port(
    value: str,
    default_port: int,
    allow_port: bool,
) -> tuple[str, int]:
    if value.startswith("["):
        closing = value.find("]")
        if closing < 0:
            raise ValueError(f"IPv6 地址缺少右方括号：{value}")
        host = value[1:closing].strip()
        suffix = value[closing + 1:].strip()
        if suffix:
            if not allow_port or not suffix.startswith(":"):
                raise ValueError(f"目标格式无效：{value}")
            port_text = suffix[1:]
            if not port_text.isdigit():
                raise ValueError(f"SSH 端口无效：{value}")
            port = int(port_text)
        else:
            port = default_port
    elif allow_port and value.count(":") == 1:
        possible_host, possible_port = value.rsplit(":", 1)
        if possible_port.isdigit():
            host = possible_host.strip()
            port = int(possible_port)
        else:
            host = value
            port = default_port
    else:
        host = normalize_host(value)
        port = default_port

    if not host:
        raise ValueError("目标地址不能为空")
    if not 1 <= int(port) <= 65535:
        raise ValueError(f"SSH 端口超出 1-65535：{port}")
    return host, int(port)


def _validate_host(host: str) -> None:
    try:
        ipaddress.ip_address(host)
        return
    except ValueError:
        pass
    if (
        len(host) > 253
        or host.startswith((".", "-"))
        or host.endswith((".", "-"))
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", host)
    ):
        raise ValueError(f"IP 地址或主机名无效：{host}")


class MaintenanceTargetDialog(QDialog):
    """Select imported devices and optionally add manual targets."""

    def __init__(self, mode: str, devices=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.devices = list(devices or [])
        self.setWindowTitle(MODE_TITLES.get(mode, "选择运维目标"))
        self.resize(820, 760)
        self.setMinimumSize(720, 640)
        self._build_ui()
        self._load_devices()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        hint_text = "可同时使用设备列表和手动输入目标；重复地址会自动合并。"
        if self.mode == "ping":
            hint_text = (
                "可同时使用设备列表、手动地址和 CIDR 网段；"
                "重复地址会自动合并。"
            )
        hint = QLabel(hint_text)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        imported_group = QGroupBox("已添加或 Excel 导入的设备")
        imported_layout = QVBoxLayout(imported_group)
        self.device_list = QListWidget()
        self.device_list.setMinimumHeight(180)
        imported_layout.addWidget(self.device_list, 1)

        selection_row = QHBoxLayout()
        select_all = QPushButton("全选")
        select_none = QPushButton("全不选")
        select_all.clicked.connect(lambda: self._set_all_checked(True))
        select_none.clicked.connect(lambda: self._set_all_checked(False))
        selection_row.addWidget(select_all)
        selection_row.addWidget(select_none)
        selection_row.addStretch(1)
        imported_layout.addLayout(selection_row)
        layout.addWidget(imported_group, 1)

        manual_group = QGroupBox("手动补充目标")
        manual_layout = QVBoxLayout(manual_group)
        self.manual_input = QPlainTextEdit()
        self.manual_input.setPlaceholderText(
            "每行一个，也可使用逗号分隔\n"
            "192.168.10.10\n"
            "2026:1000:120::23\n"
            "switch.example.com"
        )
        self.manual_input.setMaximumHeight(110)
        manual_layout.addWidget(self.manual_input)

        self.credentials_widget = QGroupBox("手工目标的 SSH 凭据")
        credentials_layout = QFormLayout(self.credentials_widget)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("SSH 用户名")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("SSH 密码")
        credentials_layout.addRow("默认端口", self.port_input)
        credentials_layout.addRow("用户名", self.username_input)
        credentials_layout.addRow("密码", self.password_input)
        self.credentials_widget.setVisible(self.mode in SSH_MODES)
        manual_layout.addWidget(self.credentials_widget)

        if self.mode in SSH_MODES:
            self.manual_input.setPlaceholderText(
                "每行一个，也可使用逗号分隔\n"
                "192.168.10.10\n"
                "[2026:1000:120::23]:2222\n"
                "switch.example.com:22"
            )
        layout.addWidget(manual_group)

        self.network_group = QGroupBox("按网段 Ping")
        network_layout = QVBoxLayout(self.network_group)
        self.network_input = QPlainTextEdit()
        self.network_input.setPlaceholderText(
            "每行一个 CIDR 网段，也可使用逗号分隔\n"
            "192.168.10.0/24\n"
            "2026:1000:120::/120"
        )
        self.network_input.setMaximumHeight(90)
        network_layout.addWidget(self.network_input)
        network_hint = QLabel(
            "IPv4 自动排除网络地址和广播地址；"
            f"合并后每次最多 {MAX_PING_NETWORK_TARGETS:,} 个目标。"
        )
        network_hint.setWordWrap(True)
        network_layout.addWidget(network_hint)
        self.network_group.setVisible(self.mode == "ping")
        layout.addWidget(self.network_group)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.button(QDialogButtonBox.Ok).setText("开始")
        self.buttons.button(QDialogButtonBox.Cancel).setText("取消")
        self.buttons.accepted.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _load_devices(self):
        for device in self.devices:
            name = str(getattr(device, "name", "") or "").strip()
            host = str(getattr(device, "ip", "") or "").strip()
            port = int(getattr(device, "port", 22) or 22)
            display_host = f"[{host}]" if ":" in host else host
            label = f"{name}  |  {display_host}:{port}" if name else (
                f"{display_host}:{port}"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, device)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.device_list.addItem(item)
        if not self.devices:
            item = QListWidgetItem("当前设备列表为空，可在下方手动输入目标")
            item.setFlags(Qt.NoItemFlags)
            self.device_list.addItem(item)
            self.manual_input.setFocus()

    def _set_all_checked(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for index in range(self.device_list.count()):
            item = self.device_list.item(index)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(state)

    def selected_devices(self) -> list:
        selected = []
        seen = set()
        include_port = self.mode in SSH_MODES
        for index in range(self.device_list.count()):
            item = self.device_list.item(index)
            device = item.data(Qt.UserRole)
            if device is None or item.checkState() != Qt.Checked:
                continue
            host = normalize_host(getattr(device, "ip", ""))
            port = int(getattr(device, "port", 22) or 22)
            key = (host.lower(), port if include_port else 0)
            if key not in seen:
                seen.add(key)
                selected.append(device)

        manual_targets = parse_manual_targets(
            self.manual_input.toPlainText(),
            allow_port=include_port,
            default_port=self.port_input.value(),
        )
        if manual_targets and self.mode in SSH_MODES:
            username = self.username_input.text().strip()
            password = self.password_input.text()
            if not username:
                raise ValueError("请输入手工目标使用的 SSH 用户名")
            if not password:
                raise ValueError("请输入手工目标使用的 SSH 密码")
        else:
            username = ""
            password = ""

        for host, port in manual_targets:
            key = (host.lower(), port if include_port else 0)
            if key in seen:
                continue
            seen.add(key)
            selected.append(
                DeviceInfo(
                    brand="",
                    ip=host,
                    port=port,
                    username=username,
                    password=password,
                    name=host,
                    auth_method="password",
                    host_key_policy="tofu",
                )
            )

        if self.mode == "ping":
            for host in expand_ping_networks(
                self.network_input.toPlainText(),
            ):
                key = (host.lower(), 0)
                if key in seen:
                    continue
                seen.add(key)
                selected.append(
                    DeviceInfo(
                        brand="",
                        ip=host,
                        port=22,
                        username="",
                        password="",
                        name=host,
                        auth_method="password",
                        host_key_policy="tofu",
                    )
                )
        return selected

    def _validate_and_accept(self):
        try:
            devices = self.selected_devices()
        except ValueError as exc:
            QMessageBox.warning(self, "目标输入错误", str(exc))
            return
        if not devices:
            QMessageBox.warning(
                self,
                "未选择目标",
                "请至少勾选一台设备或手动输入一个目标",
            )
            return
        self.accept()
