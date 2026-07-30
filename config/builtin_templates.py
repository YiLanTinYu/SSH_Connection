#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Definitions for parameterized switch configuration templates."""

from pathlib import Path


def _field(name, label, kind="text", default="", *, sensitive=False, choices=()):
    return {
        "name": name,
        "label": label,
        "kind": kind,
        "default": default,
        "sensitive": sensitive,
        "choices": tuple(choices),
        "required": True,
    }


COMMON_IDENTITY = (
    _field("DEVICE_NAME", "设备名称", "identifier", "SW1"),
)
MANAGEMENT_NETWORK = (
    _field("MGMT_VLAN", "管理 VLAN", "vlan", "100"),
    _field("MGMT_IP", "管理 IPv4 地址", "ipv4", "192.168.100.2"),
    _field("MGMT_MASK", "子网掩码", "netmask", "255.255.255.0"),
    _field("DEFAULT_GATEWAY", "默认网关", "ipv4", "192.168.100.1"),
)
ADMIN_ACCOUNT = (
    _field("ADMIN_USER", "管理员账号", "identifier", "admin"),
    _field(
        "ADMIN_PASSWORD",
        "管理员密码",
        "password",
        "",
        sensitive=True,
    ),
    _field("IDLE_MINUTES", "空闲超时（分钟）", "minutes", "15"),
)
NTP_LOGGING = (
    _field("NTP_SERVER", "NTP 服务器", "host", "192.168.100.10"),
    _field("SYSLOG_SERVER", "Syslog 服务器", "ipv4", "192.168.100.20"),
)
SNMP_V3 = (
    _field("SNMP_GROUP", "SNMPv3 组名", "identifier", "aomt_group"),
    _field("SNMP_USER", "SNMPv3 用户名", "identifier", "aomt_snmp"),
    _field("NMS_IP", "网管服务器地址", "ipv4", "192.168.100.30"),
    _field("SNMP_AUTH_PASSWORD", "认证密码（SHA）", "password", "", sensitive=True),
    _field("SNMP_PRIV_PASSWORD", "加密密码（AES128）", "password", "", sensitive=True),
    _field("CONTACT", "管理员联系方式", "description", "network-admin"),
    _field("LOCATION", "设备位置", "description", "datacenter"),
)
ACCESS_PORT = (
    _field("INTERFACE", "接口名称", "interface", "GigabitEthernet1/0/1"),
    _field("ACCESS_VLAN", "Access VLAN", "vlan", "10"),
    _field("DESCRIPTION", "接口描述", "description", "USER-PORT"),
)
TRUNK_PORT = (
    _field("INTERFACE", "接口名称", "interface", "GigabitEthernet1/0/48"),
    _field("NATIVE_VLAN", "缺省 VLAN / PVID", "vlan", "1"),
    _field("ALLOWED_VLANS", "允许 VLAN", "vlan_list", "10 20 30"),
    _field("DESCRIPTION", "接口描述", "description", "UPLINK"),
)


BUILTIN_TEMPLATE_DEFINITIONS = (
    {
        "id": "h3c_initial",
        "name": "H3C · 开局基础配置",
        "filename": "h3c_initial.txt",
        "brand": "h3c",
        "category": "开局配置",
        "description": "设备名称、管理 VLAN/IP、默认路由和时区",
        "parameters": COMMON_IDENTITY + MANAGEMENT_NETWORK,
    },
    {
        "id": "h3c_ssh",
        "name": "H3C · 账号与 SSH",
        "filename": "h3c_ssh.txt",
        "brand": "h3c",
        "category": "账号与登录",
        "description": "本地管理员、SSH Server 和 VTY 安全设置",
        "parameters": ADMIN_ACCOUNT,
        "manual_first": True,
    },
    {
        "id": "h3c_console",
        "name": "H3C · Console 安全",
        "filename": "h3c_console.txt",
        "brand": "h3c",
        "category": "账号与登录",
        "description": "Console 使用 Scheme 认证；依赖已存在的 Terminal 用户",
        "parameters": (_field("IDLE_MINUTES", "空闲超时（分钟）", "minutes", "15"),),
    },
    {
        "id": "h3c_ntp_logging",
        "name": "H3C · NTP 与日志",
        "filename": "h3c_ntp_logging.txt",
        "brand": "h3c",
        "category": "基础运维",
        "description": "北京时间、NTP 单播服务器和远程 Syslog",
        "parameters": NTP_LOGGING,
    },
    {
        "id": "h3c_snmpv3",
        "name": "H3C · SNMPv3 安全监控",
        "filename": "h3c_snmpv3.txt",
        "brand": "h3c",
        "category": "监控",
        "description": "SNMPv3 SHA/AES128 用户、Trap 主机和设备信息",
        "parameters": SNMP_V3,
    },
    {
        "id": "h3c_access_port",
        "name": "H3C · Access 端口",
        "filename": "h3c_access_port.txt",
        "brand": "h3c",
        "category": "二层端口",
        "description": "配置 Access 端口、VLAN 和描述",
        "parameters": ACCESS_PORT,
    },
    {
        "id": "h3c_trunk_port",
        "name": "H3C · Trunk 端口",
        "filename": "h3c_trunk_port.txt",
        "brand": "h3c",
        "category": "二层端口",
        "description": "配置 Trunk、PVID、允许 VLAN 和描述",
        "parameters": TRUNK_PORT,
    },
    {
        "id": "huawei_initial",
        "name": "Huawei · 开局基础配置",
        "filename": "huawei_initial.txt",
        "brand": "huawei",
        "category": "开局配置",
        "description": "VRP V200：设备名称、管理 VLANIF/IP、默认路由和时区",
        "parameters": COMMON_IDENTITY + MANAGEMENT_NETWORK,
    },
    {
        "id": "huawei_ssh",
        "name": "Huawei · 账号与 STelnet",
        "filename": "huawei_ssh.txt",
        "brand": "huawei",
        "category": "账号与登录",
        "description": "VRP V200：AAA 管理员、STelnet 和 VTY 安全设置",
        "parameters": ADMIN_ACCOUNT,
        "manual_first": True,
    },
    {
        "id": "huawei_console",
        "name": "Huawei · Console 安全",
        "filename": "huawei_console.txt",
        "brand": "huawei",
        "category": "账号与登录",
        "description": "VRP V200：Console 使用 AAA；依赖已存在的 Terminal 用户",
        "parameters": (_field("IDLE_MINUTES", "空闲超时（分钟）", "minutes", "15"),),
    },
    {
        "id": "huawei_ntp_logging",
        "name": "Huawei · NTP 与日志",
        "filename": "huawei_ntp_logging.txt",
        "brand": "huawei",
        "category": "基础运维",
        "description": "VRP V200：北京时间、NTP 和远程 Syslog",
        "parameters": NTP_LOGGING,
    },
    {
        "id": "huawei_snmpv3",
        "name": "Huawei · SNMPv3 安全监控",
        "filename": "huawei_snmpv3.txt",
        "brand": "huawei",
        "category": "监控",
        "description": "VRP V200：SNMPv3 SHA/AES128 用户、Trap 和设备信息",
        "parameters": SNMP_V3,
    },
    {
        "id": "huawei_access_port",
        "name": "Huawei · Access 端口",
        "filename": "huawei_access_port.txt",
        "brand": "huawei",
        "category": "二层端口",
        "description": "VRP V200：配置 Access 端口、VLAN 和描述",
        "parameters": ACCESS_PORT,
    },
    {
        "id": "huawei_trunk_port",
        "name": "Huawei · Trunk 端口",
        "filename": "huawei_trunk_port.txt",
        "brand": "huawei",
        "category": "二层端口",
        "description": "VRP V200：配置 Trunk、PVID、允许 VLAN 和描述",
        "parameters": TRUNK_PORT,
    },
)


def get_builtin_templates(base_dir=None):
    template_dir = (
        Path(base_dir)
        if base_dir is not None
        else Path(__file__).resolve().parent / "builtin_templates"
    )
    return [
        {
            **definition,
            "path": str(template_dir / definition["filename"]),
            "builtin": True,
            "parameterized": True,
        }
        for definition in BUILTIN_TEMPLATE_DEFINITIONS
    ]
