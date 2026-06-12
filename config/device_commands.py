#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
设备命令配置模块
支持多品牌交换机命令映射

优化说明（借鉴 w-sw-ssh 的数据驱动设计）：
- 将厂商差异集中到单一配置字典，新增品牌只需添加一个 dict 条目
- 新增 nomore/save/logout/l2_uplink 运维操作命令
- 提供二层上联口探测命令模板（_GW_IP_ / _GW_MAC_ 占位符）
"""

# ──────────────────────────────────────────────
# 品牌识别关键字
# ──────────────────────────────────────────────
BRAND_KEYWORDS = {
    'h3c':       ['h3c', 'comware'],
    'huawei':    ['huawei', 'vrp'],
    'ruijie':    ['ruijie', 'rg-os'],
    'cisco':     ['cisco', 'ios', 'nx-os'],
    'tplink':    ['tp-link', 'tplink', 't2600', 't1600', 'tl-sg', 'tl-st', 'jetstream'],
    'h3c_s':     ['h3c s', 's5560', 's5120', 's5130'],
    'huawei_ce': ['ce', 's127', 's6730'],
}

# ──────────────────────────────────────────────
# 各品牌完整命令映射（数据驱动，避免分散 if-else）
#
# l2_uplink_xxx：二层上联口探测命令（借鉴 w-sw-ssh uf_get_l2_uplink）
#   _GW_IP_  → 运行时替换为实际网关 IP
#   _GW_MAC_ → 运行时替换为实际网关 MAC
# l2_uplink_mac_col：MAC 地址表输出中接口字段的列索引（0起始）
# ──────────────────────────────────────────────
DEVICE_COMMANDS = {
    'h3c': {
        # 查询类
        'display_version':   'display version',
        'display_manuinfo':  'display device manuinfo',
        'display_cpu':       'display cpu-usage',
        'display_memory':    'display memory',
        'display_interface': 'display interface brief',
        'display_vlan':      'display vlan',
        'display_mac':       'display mac-address',
        'display_arp':       'display arp',
        'display_route':     'display ip routing-table',
        'display_config':    'display current-configuration',
        'display_log':       'display logbuffer',
        # 运维操作（借鉴 w-sw-ssh）
        'nomore':            'screen-length disable',
        'save_config':       'save force',
        'logout':            'quit\rquit\r',
        # 二层上联口探测（借鉴 w-sw-ssh uf_get_l2_uplink）
        'l2_gw_ip_cmd':      'display ip routing-table 0.0.0.0 0',
        'l2_gw_mac_cmd':     'disp arp _GW_IP_',
        'l2_uplink_cmd':     'display mac-address _GW_MAC_',
        'l2_uplink_mac_col': 2,   # H3C 第3列（0起始=2）
    },
    'huawei': {
        'display_version':   'display version',
        'display_manuinfo':  'display device manuinfo',
        'display_cpu':       'display cpu-usage',
        'display_memory':    'display memory-usage',
        'display_interface': 'display interface brief',
        'display_vlan':      'display vlan',
        'display_mac':       'display mac-address',
        'display_arp':       'display arp all',
        'display_route':     'display ip routing-table',
        'display_config':    'display current-configuration',
        'display_log':       'display logbuffer',
        'nomore':            'screen-length 0 temp',
        'save_config':       'return\rsave\r\ny\r',
        'logout':            'quit\rquit\r',
        'l2_gw_ip_cmd':      'display ip routing-table 0.0.0.0 0',
        'l2_gw_mac_cmd':     'disp arp dynamic | include _GW_IP_',
        'l2_uplink_cmd':     'display mac-address _GW_MAC_',
        'l2_uplink_mac_col': 1,   # Huawei 第2列（0起始=1）
    },
    'ruijie': {
        'display_version':   'show version',
        'display_manuinfo':  'show inventory',
        'display_cpu':       'show cpu',
        'display_memory':    'show memory',
        'display_interface': 'show interface brief',
        'display_vlan':      'show vlan',
        'display_mac':       'show mac-address-table',
        'display_arp':       'show arp',
        'display_route':     'show ip route',
        'display_config':    'show running-config',
        'display_log':       'show logging',
        'nomore':            'terminal length 0',
        'save_config':       'write',
        'logout':            'end\rexit',
        'l2_gw_ip_cmd':      'show ip route 0.0.0.0',
        'l2_gw_mac_cmd':     'show arp _GW_IP_',
        'l2_uplink_cmd':     'show mac-address-table address _GW_MAC_',
        'l2_uplink_mac_col': 1,
    },
    'cisco': {
        'display_version':   'show version',
        'display_manuinfo':  'show inventory',
        'display_cpu':       'show processes cpu',
        'display_memory':    'show processes memory',
        'display_interface': 'show ip interface brief',
        'display_vlan':      'show vlan brief',
        'display_mac':       'show mac address-table',
        'display_arp':       'show arp',
        'display_route':     'show ip route',
        'display_config':    'show running-config',
        'display_log':       'show logging',
        'nomore':            'terminal length 0',
        'save_config':       'end\rcopy run start\r',
        'logout':            'end\rexit',
        'l2_gw_ip_cmd':      'show ip default-gateway',
        'l2_gw_mac_cmd':     'show ip arp _GW_IP_',
        'l2_uplink_cmd':     'show mac address-table address _GW_MAC_',
        'l2_uplink_mac_col': 1,
    },
    # TP-Link 企业交换机（JetStream T/TL 系列，类 Cisco CLI）
    'tplink': {
        'display_version':   'show version',
        'display_manuinfo':  'show system-info',
        'display_cpu':       'show cpu-usage',
        'display_memory':    'show memory-usage',
        'display_interface': 'show interfaces status',
        'display_vlan':      'show vlan',
        'display_mac':       'show mac-address-table',
        'display_arp':       'show arp',
        'display_route':     'show ip route',
        'display_config':    'show running-config',
        'display_log':       'show log',
        'nomore':            'terminal length 0',
        'save_config':       'copy running-config startup-config',
        'logout':            'end\rexit',
        'l2_gw_ip_cmd':      'show ip route 0.0.0.0',
        'l2_gw_mac_cmd':     'show arp _GW_IP_',
        'l2_uplink_cmd':     'show mac-address-table address _GW_MAC_',
        'l2_uplink_mac_col': 1,
    },
}

# 设备版本识别命令（按厂商语法，用于自动识别品牌）
VERSION_CMDS = {
    'h3c_huawei': 'display version',
    'cisco_style': 'show version',
}

# 设备类型默认版本查询命令
DEFAULT_COMMANDS = {
    'h3c':     'display version',
    'huawei':  'display version',
    'ruijie':  'show version',
    'cisco':   'show version',
    'tplink':  'show version',
}


def get_device_commands(brand: str) -> dict:
    """
    获取指定品牌的命令映射

    Args:
        brand: 设备品牌

    Returns:
        dict: 命令映射字典
    """
    brand_lower = brand.lower()

    # 尝试直接匹配
    if brand_lower in DEVICE_COMMANDS:
        return DEVICE_COMMANDS[brand_lower]

    # 尝试关键字匹配
    for known_brand, keywords in BRAND_KEYWORDS.items():
        if any(keyword in brand_lower for keyword in keywords):
            base = known_brand.split('_')[0]
            return DEVICE_COMMANDS.get(base, DEVICE_COMMANDS['h3c'])

    # 默认返回 H3C 命令
    return DEVICE_COMMANDS['h3c']


def get_command(brand: str, command_key: str) -> str:
    """
    获取指定品牌的具体命令

    Args:
        brand: 设备品牌
        command_key: 命令关键字（如 'nomore', 'save_config', 'display_version'）

    Returns:
        str: 具体命令字符串
    """
    commands = get_device_commands(brand)
    return commands.get(command_key, commands.get('display_version', 'display version'))


def detect_brand(version_output: str) -> str:
    """
    根据版本输出自动识别设备品牌（借鉴 w-sw-ssh uf_get_vendor_model 逻辑）

    识别优先级：
    1. H3C / Huawei（display version 有效）
    2. Cisco Nexus / Cisco（show version 有效）
    3. Ruijie / TP-Link（关键字匹配）

    Args:
        version_output: display version 或 show version 的输出

    Returns:
        str: 识别出的品牌（'h3c'/'huawei'/'cisco'/'ruijie'/'tplink'）
    """
    if not version_output:
        return 'unknown'

    version_lower = version_output.lower()

    # 精确优先匹配（避免 cisco 关键字误触发 h3c 设备）
    priority_checks = [
        ('h3c',    ['h3c', 'comware']),
        ('huawei', ['huawei', 'vrp']),
        ('ruijie', ['ruijie', 'rg-os']),
        ('tplink', ['tp-link', 'tplink', 'jetstream', 't2600']),
        ('cisco',  ['cisco', 'ios', 'nx-os']),
    ]
    for brand, keywords in priority_checks:
        if any(kw in version_lower for kw in keywords):
            return brand

    # 回退：逐 BRAND_KEYWORDS 匹配
    for brand, keywords in BRAND_KEYWORDS.items():
        if any(keyword in version_lower for keyword in keywords):
            return brand.split('_')[0]

    return 'unknown'


def translate_command_for_brand(command: str, brand: str) -> str:
    """
    将命令文件中的 H3C/华为风格命令自动转换为目标品牌的等价命令。

    这是 w-sw-ssh cmd_prefix 机制的 GUI 版实现：
    不再要求用户准备多份 .cmd.h3c / .cmd.cisco 文件，
    而是在运行时根据识别的品牌自动翻译。

    Args:
        command: 原始命令（通常为 H3C/Huawei 格式）
        brand:   目标品牌

    Returns:
        str: 翻译后的命令
    """
    if not command or not brand:
        return command

    brand_cmds = get_device_commands(brand)

    # 构建反向查找表：将每个品牌的命令值映射到命令键
    # 再用目标品牌的命令键查对应命令值
    # 遍历所有品牌，建立 "命令字符串 → 命令键" 的全局映射
    cmd_to_key: dict = {}
    for cmds in DEVICE_COMMANDS.values():
        for key, cmd_str in cmds.items():
            if key.startswith('l2_') or key in ('nomore', 'save_config', 'logout'):
                continue   # 运维操作不做翻译
            # 保留最后写入（避免同一命令被不同品牌覆盖导致混乱）
            cmd_to_key[cmd_str.lower()] = key

    cmd_lower = command.strip().lower()
    key = cmd_to_key.get(cmd_lower)
    if key and key in brand_cmds:
        return brand_cmds[key]

    return command


# ──────────────────────────────────────────────
# 可扩展的命令模块接口
# ──────────────────────────────────────────────
class CommandModule:
    """命令模块：支持品牌感知与自定义命令扩展"""

    def __init__(self, brand: str = 'h3c'):
        self.brand    = brand
        self.commands = dict(get_device_commands(brand))

    def get_command(self, command_key: str) -> str:
        """获取命令"""
        return self.commands.get(command_key, 'display version')

    def add_command(self, command_key: str, command: str):
        """添加自定义命令"""
        self.commands[command_key] = command

    def set_brand(self, brand: str):
        """切换品牌，重新加载命令表"""
        self.brand    = brand
        self.commands = dict(get_device_commands(brand))

    def get_nomore_cmd(self) -> str:
        """获取禁用分页命令"""
        return self.commands.get('nomore', 'terminal length 0')

    def get_save_cmd(self) -> str:
        """获取保存配置命令"""
        return self.commands.get('save_config', '')

    def get_logout_cmd(self) -> str:
        """获取退出命令"""
        return self.commands.get('logout', 'quit')
