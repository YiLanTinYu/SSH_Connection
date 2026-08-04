"""Structured H3C/Comware and Huawei VRP read-only diagnostics."""

from __future__ import annotations

import ipaddress
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

import textfsm
from ntc_templates.parse import parse_output


HEALTH_COMMANDS = (
    "display cpu-usage summary",
    "display memory",
    "display environment",
    "display fan",
    "display power",
    "display interface brief",
    "display device manuinfo",
)

INTERFACE_COMMANDS = (
    "display interface {interface}",
    "display transceiver diagnosis interface {interface}",
    "display transceiver alarm interface {interface}",
)

HUAWEI_HEALTH_COMMANDS = (
    "display cpu-usage",
    "display memory-usage",
    "display temperature all",
    "display fan",
    "display power",
    "display interface brief",
    "display device",
)

HUAWEI_INTERFACE_COMMANDS = (
    "display interface {interface}",
    "display transceiver diagnosis interface {interface}",
    "display transceiver alarm interface {interface}",
)

SUPPORTED_DIAGNOSTIC_BRANDS = frozenset(("h3c", "huawei"))

HEALTH_CHECK_ITEMS = (
    {
        "id": "cpu",
        "label": "CPU 使用率",
        "commands": {
            "h3c": "display cpu-usage summary",
            "huawei": "display cpu-usage",
        },
    },
    {
        "id": "memory",
        "label": "内存使用率",
        "commands": {
            "h3c": "display memory",
            "huawei": "display memory-usage",
        },
    },
    {
        "id": "temperature",
        "label": "温度",
        "commands": {
            "h3c": "display environment",
            "huawei": "display temperature all",
        },
    },
    {
        "id": "fan",
        "label": "风扇",
        "commands": {
            "h3c": "display fan",
            "huawei": "display fan",
        },
    },
    {
        "id": "power",
        "label": "电源",
        "commands": {
            "h3c": "display power",
            "huawei": "display power",
        },
    },
    {
        "id": "interfaces",
        "label": "接口摘要",
        "commands": {
            "h3c": "display interface brief",
            "huawei": "display interface brief",
        },
    },
    {
        "id": "hardware",
        "label": "硬件信息",
        "commands": {
            "h3c": "display device manuinfo",
            "huawei": "display device",
        },
    },
)

HEALTH_CHECK_ITEM_IDS = tuple(item["id"] for item in HEALTH_CHECK_ITEMS)

_BRAND_PROFILES = {
    "h3c": {
        "label": "H3C/Comware",
        "health_commands": HEALTH_COMMANDS,
        "interface_commands": INTERFACE_COMMANDS,
        "arp_command": lambda target: f"display arp {target}",
        "arp_parse_command": "display arp",
        "mac_command": lambda mac: f"display mac-address {mac}",
        "mac_parse_command": "display mac-address",
    },
    "huawei": {
        "label": "Huawei VRP",
        "health_commands": HUAWEI_HEALTH_COMMANDS,
        "interface_commands": HUAWEI_INTERFACE_COMMANDS,
        # Query the complete tables and filter locally. This is compatible with
        # more VRP5/VRP8 releases than parameterized display variants.
        "arp_command": lambda _target: "display arp all",
        "arp_parse_command": "display arp all",
        "mac_command": lambda _mac: "display mac-address",
        "mac_parse_command": "display mac-address",
    },
}

_LOCAL_TEMPLATE_FILES = {
    "display cpu-usage summary": "display_cpu-usage_summary.tpl",
    "display memory": "display_memory.tpl",
    "display environment": "display_environment.tpl",
    "display fan": "display_fan.tpl",
    "display power": "display_power.tpl",
    "display interface": "display_interface.tpl",
}

_COMMAND_ERROR = re.compile(
    r"%\s*(?:Unrecognized|Invalid)|Unrecognized command|"
    r"Wrong parameter|Incomplete command|Error:",
    re.IGNORECASE,
)
_MAC_TOKEN = re.compile(
    r"(?i)(?<![0-9a-f])(?:[0-9a-f]{4}[-.:]){2}[0-9a-f]{4}(?![0-9a-f])|"
    r"(?<![0-9a-f])(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}(?![0-9a-f])"
)
_INTERFACE_NAME = re.compile(
    r"^[A-Za-z][A-Za-z0-9-]*(?:\s*)\d+(?:/\d+){0,3}(?:\.\d+)?$"
)


def _template_dir() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "open_source"
        / "napalm_h3c_textfsm"
    )


def _parse_comware_health_fallback(command: str, text: str) -> list[dict]:
    """Parse stable Comware health tables not covered by bundled templates."""
    if command == "display power":
        return [
            {"device_id": match.group(1), "status": match.group(2)}
            for match in re.finditer(
                r"(?im)^\s*(\d+)\s+"
                r"(Normal|Absent|Fault|Abnormal|Offline)\s*$",
                text,
            )
        ]
    if command == "display interface brief":
        records = []
        for match in re.finditer(
            r"(?im)^\s*(\S+)\s+"
            r"(UP|DOWN|ADM|Stby)\s+(\S+)(?:\s+.*)?$",
            text,
        ):
            records.append({
                "interface": match.group(1),
                "link": match.group(2).upper(),
                "protocol": match.group(3),
            })
        return records
    if command == "display device manuinfo":
        records = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized_key = key.strip().lower()
            if normalized_key == "device_id" and current:
                records.append(current)
                current = {}
            if normalized_key.startswith("device_") or normalized_key in {
                "mac_address",
                "manufacturing_date",
                "vendor_name",
            }:
                current[normalized_key] = value.strip()
        if current:
            records.append(current)
        return records
    return []


def _parse_huawei_health_fallback(command: str, text: str) -> list[dict]:
    """Parse conservative VRP5/VRP8 health rows when NTC has no template."""
    if command == "display cpu-usage":
        match = re.search(
            r"CPU utilization for five seconds:\s*(\d+)%:\s*"
            r"one minute:\s*(\d+)%:\s*five minutes:\s*(\d+)%",
            text,
            re.IGNORECASE,
        )
        return [{
            "five_sec": match.group(1),
            "one_min": match.group(2),
            "five_min": match.group(3),
        }] if match else []
    if command == "display memory-usage":
        total = re.search(r"System Total Memory Is:\s*(\d+)", text, re.I)
        used = re.search(r"Total Memory Used Is:\s*(\d+)", text, re.I)
        percent = re.search(r"Memory Using Percentage Is:\s*(\d+)%", text, re.I)
        if not percent:
            return []
        return [{
            "total_bytes": total.group(1) if total else "",
            "used_bytes": used.group(1) if used else "",
            "used_percent": percent.group(1),
        }]
    if command == "display temperature all":
        return [
            {
                "slot": match.group(1),
                "card": match.group(2),
                "sensor": match.group(3),
                "status": match.group(4),
                "temperature": match.group(5),
            }
            for match in re.finditer(
                r"(?im)^\s*(\d+)\s+(\S+)\s+(\S+)\s+"
                r"(Normal|Abnormal)\s+(-?\d+)(?:\s+-?\d+){4}\s*$",
                text,
            )
        ]
    if command == "display fan":
        return [
            {
                "slot": match.group(1),
                "fan_id": match.group(2),
                "online": match.group(3),
                "status": match.group(4),
                "speed": match.group(5),
            }
            for match in re.finditer(
                r"(?im)^\s*(\d+)\s+(\d+)\s+(Present|Absent)\s+"
                r"(\S+)\s+(\S+)(?:\s+.*)?$",
                text,
            )
        ]
    if command == "display power":
        return [
            {
                "slot": match.group(1),
                "power_id": match.group(2),
                "online": match.group(3),
                "mode": match.group(4),
                "state": match.group(5),
                "power": match.group(6),
            }
            for match in re.finditer(
                r"(?im)^\s*(\d+)\s+(\S+)\s+(Present|Absent)\s+"
                r"(\S+)\s+(\S+)\s+(\S+)\s*$",
                text,
            )
        ]
    if command == "display interface brief":
        return [
            {
                "interface": match.group(1),
                "phy": match.group(2),
                "link": match.group(2),
                "protocol": match.group(3),
            }
            for match in re.finditer(
                r"(?im)^\s*(\S+)\s+"
                r"(?:\*|#)?(up|down)\s+(\S+)\s+"
                r"(?:\d+%|--)\s+(?:\d+%|--)\s+\d+\s+\d+\s*$",
                text,
            )
        ]
    if command == "display device":
        records = []
        row_pattern = re.compile(
            r"^\s*(?:(\d+)\s+)?(\S+)\s+(\S+)\s+"
            r"(Present|Absent)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$",
            re.IGNORECASE,
        )
        for line in text.splitlines():
            match = row_pattern.match(line)
            if not match:
                continue
            records.append({
                "slot": match.group(1) or "",
                "sub": match.group(2),
                "type": match.group(3),
                "online": match.group(4),
                "power": match.group(5),
                "register": match.group(6),
                "status": match.group(7),
                "alarm_status": match.group(7),
                "role": match.group(8),
            })
        return records
    return []


def parse_comware_output(command: str, output: str) -> list[dict]:
    """Parse Comware output with NTC Templates or the attributed NAPALM templates."""
    text = str(output or "")
    normalized_command = " ".join(str(command or "").strip().lower().split())
    template_key = normalized_command
    if (
        normalized_command.startswith("display interface ")
        and normalized_command != "display interface brief"
    ):
        template_key = "display interface"
    local_name = _LOCAL_TEMPLATE_FILES.get(template_key)
    if local_name:
        path = _template_dir() / local_name
        records = []
        if path.is_file():
            with path.open("r", encoding="utf-8") as template_file:
                parser = textfsm.TextFSM(template_file)
                rows = parser.ParseText(text)
                headers = [name.lower() for name in parser.header]
            records = [dict(zip(headers, row)) for row in rows]
            if template_key == "display interface":
                records = [
                    record for record in records
                    if str(record.get("link_status") or "").strip()
                ]
        return records or _parse_comware_health_fallback(
            normalized_command, text
        )
    try:
        parsed = parse_output(
            platform="hp_comware",
            command=normalized_command,
            data=text,
        )
    except Exception:
        parsed = []
    return list(parsed or []) or _parse_comware_health_fallback(
        normalized_command, text
    )


def normalize_brand(value: str) -> str:
    brand = str(value or "").strip().lower()
    aliases = {
        "hp_comware": "h3c",
        "comware": "h3c",
        "huawei_vrp": "huawei",
        "vrp": "huawei",
    }
    return aliases.get(brand, brand)


def get_diagnostic_profile(brand: str) -> dict:
    normalized = normalize_brand(brand)
    if normalized not in _BRAND_PROFILES:
        raise ValueError(f"当前诊断工具不支持品牌：{brand or '未知'}")
    return _BRAND_PROFILES[normalized]


def parse_device_output(brand: str, command: str, output: str) -> list[dict]:
    """Parse command output with the explicitly selected vendor parser."""
    normalized_brand = normalize_brand(brand)
    if normalized_brand == "h3c":
        return parse_comware_output(command, output)
    if normalized_brand != "huawei":
        return []

    normalized_command = " ".join(str(command or "").strip().lower().split())
    if (
        normalized_command.startswith("display interface ")
        and normalized_command != "display interface brief"
    ):
        normalized_command = "display interface"
    try:
        parsed = parse_output(
            platform="huawei_vrp",
            command=normalized_command,
            data=str(output or ""),
        )
    except Exception:
        parsed = []
    records = list(parsed or [])
    if not records:
        records = _parse_huawei_health_fallback(
            normalized_command, str(output or "")
        )
    if normalized_command == "display mac-address":
        for record in records:
            record.setdefault(
                "mac_address", record.get("destination_address", "")
            )
            record.setdefault(
                "interface", record.get("destination_port", "")
            )
            record.setdefault("state", record.get("type", ""))
    elif normalized_command == "display interface brief":
        for record in records:
            record.setdefault("link", record.get("phy", ""))
    return records


def get_health_commands(
    brand: str, selected_items: Iterable[str] | None = None
) -> tuple[str, ...]:
    normalized_brand = normalize_brand(brand)
    get_diagnostic_profile(normalized_brand)
    selected = (
        set(HEALTH_CHECK_ITEM_IDS)
        if selected_items is None
        else set(selected_items)
    )
    return tuple(
        item["commands"][normalized_brand]
        for item in HEALTH_CHECK_ITEMS
        if item["id"] in selected
    )


def get_interface_commands(brand: str) -> tuple[str, ...]:
    return tuple(get_diagnostic_profile(brand)["interface_commands"])


def get_lookup_command(brand: str, lookup_type: str, value: str) -> tuple[str, str]:
    profile = get_diagnostic_profile(brand)
    if lookup_type not in ("arp", "mac"):
        raise ValueError(f"未知查询类型：{lookup_type}")
    return (
        profile[f"{lookup_type}_command"](value),
        profile[f"{lookup_type}_parse_command"],
    )


def command_is_supported(output: str) -> bool:
    text = str(output or "").strip()
    return bool(text) and not _COMMAND_ERROR.search(text)


def normalize_mac(value: str) -> str:
    compact = re.sub(r"[^0-9a-fA-F]", "", str(value or ""))
    if len(compact) != 12 or not re.fullmatch(r"[0-9a-fA-F]{12}", compact):
        raise ValueError("请输入有效的 MAC 地址，例如 0011-2233-4455")
    compact = compact.lower()
    return "-".join(compact[index:index + 4] for index in range(0, 12, 4))


def normalize_lookup_target(value: str) -> tuple[str, str]:
    text = str(value or "").strip()
    if not text:
        raise ValueError("请输入需要定位的 IPv4 地址或 MAC 地址")
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return "mac", normalize_mac(text)
    if address.version != 4:
        raise ValueError("当前 H3C ARP/MAC 定位仅支持 IPv4 地址或 MAC 地址")
    return "ip", str(address)


def validate_interface_name(value: str) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text or not _INTERFACE_NAME.fullmatch(text):
        raise ValueError(
            "接口名称格式无效，例如 GigabitEthernet1/0/1、"
            "Ten-GigabitEthernet1/0/1 或 Bridge-Aggregation1"
        )
    return text


def extract_mac_addresses(records: Iterable[dict]) -> list[str]:
    values = []
    for record in records:
        raw = record.get("mac_address", "")
        try:
            mac = normalize_mac(raw)
        except ValueError:
            continue
        if mac not in values:
            values.append(mac)
    return values


def choose_discovered_mac(mac_addresses: Iterable[str]) -> str:
    values = [normalize_mac(value) for value in mac_addresses]
    if not values:
        return ""
    return Counter(values).most_common(1)[0][0]


def _extract_huawei_percent(output: str, patterns: tuple[str, ...]) -> int | None:
    text = str(output or "")
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _summarize_huawei_health(outputs: dict[str, str]) -> tuple[str, bool]:
    lines = ["Huawei VRP 一键巡检摘要"]
    warnings = []
    available = 0

    cpu = _extract_huawei_percent(
        outputs.get("display cpu-usage", ""),
        (
            r"five seconds:\s*(\d+)%",
            r"CPU Usage\s*:\s*(\d+)%",
        ),
    )
    if cpu is None:
        lines.append("CPU：该型号未返回可解析数据")
    else:
        available += 1
        lines.append(f"CPU 使用率：{cpu}%")
        if cpu >= 80:
            warnings.append(f"CPU 使用率较高（{cpu}%）")

    memory = _extract_huawei_percent(
        outputs.get("display memory-usage", ""),
        (
            r"Memory Using Percentage Is:\s*(\d+)%",
            r"Memory Using Percentage\s*:\s*(\d+)%",
        ),
    )
    if memory is None:
        lines.append("内存：该型号未返回可解析数据")
    else:
        available += 1
        lines.append(f"内存使用率：{memory}%")
        if memory >= 80:
            warnings.append(f"内存使用率较高（{memory}%）")

    temperatures = parse_device_output(
        "huawei",
        "display temperature all",
        outputs.get("display temperature all", ""),
    )
    if temperatures:
        available += 1
        highest = max(
            float(row.get("temperature") or 0) for row in temperatures
        )
        lines.append(f"最高温度：{highest:.0f} °C")
        abnormal = [
            row for row in temperatures
            if str(row.get("status") or "").lower() not in ("normal", "ok")
        ]
        if abnormal:
            warnings.append(f"温度传感器存在 {len(abnormal)} 项异常")
    else:
        lines.append("温度：该型号未返回可解析数据")

    fan_text = outputs.get("display fan", "")
    fan_states = re.findall(
        r"^\s*\d+\s+\d+\s+\S+\s+(Normal|Abnormal)\b",
        fan_text,
        re.IGNORECASE | re.MULTILINE,
    )
    if fan_states:
        available += 1
        abnormal_fans = [
            state for state in fan_states if state.lower() != "normal"
        ]
        lines.append(
            f"风扇：{len(fan_states)} 项，异常 {len(abnormal_fans)} 项"
        )
        if abnormal_fans:
            warnings.append(f"风扇存在 {len(abnormal_fans)} 项非正常状态")
    elif command_is_supported(fan_text):
        lines.append("风扇：已返回数据，详见原始命令输出")
    else:
        lines.append("风扇：该型号未返回有效数据")

    power_text = outputs.get("display power", "")
    power_states = re.findall(
        r"^\s*\d+\s+\S+\s+\S+\s+\S+\s+(\S+)\s+\d+(?:\.\d+)?\s*$",
        power_text,
        re.IGNORECASE | re.MULTILINE,
    )
    if power_states:
        available += 1
        abnormal_power = [
            state for state in power_states if state.lower() != "supply"
        ]
        lines.append(
            f"电源：{len(power_states)} 项，异常 {len(abnormal_power)} 项"
        )
        if abnormal_power:
            warnings.append(f"电源存在 {len(abnormal_power)} 项非正常状态")
    elif command_is_supported(power_text):
        lines.append("电源：已返回数据，详见原始命令输出")
    else:
        lines.append("电源：该型号未返回有效数据")

    interfaces = parse_device_output(
        "huawei",
        "display interface brief",
        outputs.get("display interface brief", ""),
    )
    if interfaces:
        available += 1
        up_count = sum(
            str(row.get("phy") or row.get("link") or "").lower().startswith("up")
            for row in interfaces
        )
        lines.append(
            f"接口摘要：共 {len(interfaces)} 个，UP {up_count} 个，"
            f"非 UP {len(interfaces) - up_count} 个"
        )
    else:
        lines.append("接口摘要：未获得可解析数据")

    hardware = parse_device_output(
        "huawei", "display device", outputs.get("display device", "")
    )
    if hardware:
        available += 1
        abnormal = [
            row for row in hardware
            if str(row.get("alarm_status") or "").lower()
            not in ("", "normal", "none")
        ]
        lines.append(f"设备硬件：{len(hardware)} 项，告警 {len(abnormal)} 项")
        if abnormal:
            warnings.append(f"设备硬件存在 {len(abnormal)} 项告警")

    lines.append("")
    if warnings:
        lines.append("需要关注：")
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("未从已成功解析的指标中发现明显异常。")
    lines.append(f"成功结构化的指标类别：{available} 项")
    return "\n".join(lines), available > 0


_HEALTH_SUMMARY_PREFIXES = {
    "CPU": "cpu",
    "内存": "memory",
    "最高温度": "temperature",
    "温度": "temperature",
    "风扇": "fan",
    "电源": "power",
    "接口摘要": "interfaces",
    "硬件制造信息": "hardware",
    "设备硬件": "hardware",
}


def _filter_health_summary(summary: str, selected_items: set[str]) -> str:
    lines = []
    for line in str(summary or "").splitlines():
        item_id = next(
            (
                value for prefix, value in _HEALTH_SUMMARY_PREFIXES.items()
                if line.startswith(prefix)
            ),
            "",
        )
        if item_id and item_id not in selected_items:
            continue
        lines.append(line)
    if not selected_items:
        insert_at = 1 if lines else 0
        lines.insert(insert_at, "未选择内置结构化指标。")
    return "\n".join(lines)


def summarize_health(
    outputs: dict[str, str],
    brand: str = "h3c",
    selected_items: Iterable[str] | None = None,
) -> tuple[str, bool]:
    selected = (
        set(HEALTH_CHECK_ITEM_IDS)
        if selected_items is None
        else set(selected_items)
    )
    if normalize_brand(brand) == "huawei":
        summary, usable = _summarize_huawei_health(outputs)
        return _filter_health_summary(summary, selected), usable
    lines = ["H3C/Comware 一键巡检摘要"]
    warnings = []
    available = 0

    cpu_rows = parse_comware_output(
        "display cpu-usage summary",
        outputs.get("display cpu-usage summary", ""),
    )
    if cpu_rows:
        available += 1
        peak = max(
            int(row.get(field) or 0)
            for row in cpu_rows
            for field in ("five_sec", "one_min", "five_min")
        )
        lines.append(f"CPU 峰值：{peak}%")
        if peak >= 80:
            warnings.append(f"CPU 使用率较高（峰值 {peak}%）")
    else:
        lines.append("CPU：该型号未返回可解析数据")

    memory_rows = parse_comware_output(
        "display memory", outputs.get("display memory", "")
    )
    if memory_rows:
        available += 1
        used_rates = []
        for row in memory_rows:
            free_ratio = float(row.get("free_ratio") or 0)
            used_rates.append(max(0.0, 100.0 - free_ratio))
        peak_memory = max(used_rates)
        lines.append(f"内存最高使用率：{peak_memory:.1f}%")
        if peak_memory >= 80:
            warnings.append(f"内存使用率较高（{peak_memory:.1f}%）")
    else:
        lines.append("内存：该型号未返回可解析数据")

    environment_rows = parse_comware_output(
        "display environment", outputs.get("display environment", "")
    )
    if environment_rows:
        available += 1
        highest = max(float(row.get("temperature") or 0) for row in environment_rows)
        lines.append(f"最高温度：{highest:.0f} °C")
        for row in environment_rows:
            current = float(row.get("temperature") or 0)
            alert = float(row.get("alert") or 0)
            if alert and current >= alert:
                warnings.append(
                    f"温度达到告警阈值：{row.get('sensor') or '传感器'} {current:.0f} °C"
                )
    else:
        lines.append("温度：该型号未返回可解析数据")

    for command, label in (
        ("display fan", "风扇"),
        ("display power", "电源"),
    ):
        rows = parse_comware_output(command, outputs.get(command, ""))
        if rows:
            available += 1
            abnormal = [
                row for row in rows
                if str(row.get("status") or "").lower() not in ("normal", "ok")
            ]
            lines.append(f"{label}：{len(rows)} 项，异常 {len(abnormal)} 项")
            if abnormal:
                warnings.append(f"{label}存在 {len(abnormal)} 项非正常状态")
        else:
            lines.append(f"{label}：该型号未返回可解析数据")

    interfaces = parse_comware_output(
        "display interface brief", outputs.get("display interface brief", "")
    )
    if interfaces:
        available += 1
        up_count = sum(
            str(row.get("link") or "").upper() == "UP"
            for row in interfaces
        )
        down_count = len(interfaces) - up_count
        lines.append(
            f"接口摘要：共 {len(interfaces)} 个，UP {up_count} 个，"
            f"非 UP {down_count} 个"
        )
    else:
        lines.append("接口摘要：未获得可解析数据")

    hardware = parse_comware_output(
        "display device manuinfo", outputs.get("display device manuinfo", "")
    )
    if hardware:
        available += 1
        lines.append(f"硬件制造信息：{len(hardware)} 项")

    lines.append("")
    if warnings:
        lines.append("需要关注：")
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("未从已成功解析的指标中发现明显异常。")
    lines.append(f"成功结构化的指标类别：{available} 项")
    summary = _filter_health_summary("\n".join(lines), selected)
    return summary, available > 0


def summarize_mac_locations(mac: str, device_records: dict[str, list[dict]]) -> str:
    lines = [f"终端 MAC：{normalize_mac(mac)}", "定位结果："]
    found = 0
    for label, records in device_records.items():
        for row in records:
            try:
                row_mac = normalize_mac(row.get("mac_address", ""))
            except ValueError:
                continue
            if row_mac != normalize_mac(mac):
                continue
            found += 1
            lines.append(
                f"- {label}：接口 {row.get('interface') or '未知'}，"
                f"VLAN {row.get('vlan_id') or '未知'}，"
                f"状态 {row.get('state') or '未知'}"
            )
    if not found:
        lines.append("- 未在已选设备的 MAC 地址表中找到该终端")
    lines.append("")
    lines.append(
        "说明：聚合口或上联口学到的 MAC 可能只是转发路径，"
        "应优先确认最靠近终端的物理接入口。"
    )
    return "\n".join(lines)


def summarize_interface(
    interface: str,
    interface_output: str,
    transceiver_output: str = "",
    alarm_output: str = "",
    brand: str = "h3c",
) -> tuple[str, bool]:
    records = parse_device_output(brand, "display interface", interface_output)
    lines = [f"接口：{interface}"]
    warnings = []
    if records:
        record = records[0]
        link = (
            record.get("link_status")
            or record.get("line_status")
            or "未知"
        )
        protocol = record.get("protocol_status") or "未知"
        lines.extend([
            f"物理状态：{link}",
            f"协议状态：{protocol}",
            f"速率：{record.get('speed_mode') or record.get('speed') or '未识别'}",
            f"双工：{record.get('duplex_mode') or record.get('duplex') or '未识别'}",
            f"链路类型：{record.get('link_type') or record.get('port_link_type') or '未识别'}",
            f"PVID：{record.get('pvid') or record.get('vlan_id') or record.get('vlan_native') or record.get('untagged_vlan_id') or '未识别'}",
            f"描述：{record.get('description') or record.get('interface_description') or '无'}",
        ])
        if str(link).upper() != "UP":
            warnings.append(f"物理状态为 {link}")
        if str(protocol).upper() not in ("UP", "UP(SPOOFING)"):
            warnings.append(f"协议状态为 {protocol}")
    else:
        lines.append("接口详情：该型号未返回可解析数据")

    if command_is_supported(transceiver_output):
        lines.append("光模块诊断：已返回数据，详见原始命令输出")
    else:
        lines.append("光模块诊断：未返回数据或该接口不支持")
    if command_is_supported(alarm_output):
        lower = alarm_output.lower()
        if re.search(r"\b(?:alarm|fault|abnormal)\b", lower) and not re.search(
            r"\bno\s+(?:alarm|fault)\b", lower
        ):
            warnings.append("光模块告警输出中检测到异常关键词")
        lines.append("光模块告警：已返回数据，详见原始命令输出")
    else:
        lines.append("光模块告警：未返回数据或该接口不支持")

    lines.append("")
    if warnings:
        lines.append("需要关注：")
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("未从已成功解析的指标中发现明显异常。")
    return "\n".join(lines), bool(records)
