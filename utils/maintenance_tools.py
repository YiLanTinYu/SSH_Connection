#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Low-risk network maintenance helpers used by the desktop UI."""

from __future__ import annotations

import difflib
import hashlib
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Iterable


_BACKUP_WRITE_LOCK = threading.Lock()
_ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:\][^\x07]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~]|[@-_])"
)
_PAGING_LINE_RE = re.compile(
    r"^(?:-{2,}\s*more\s*-{2,}|----\s*more\s*----|"
    r"press\s+(?:any\s+key|space|enter).*)$",
    re.IGNORECASE,
)
_PROMPT_LINE_RE = re.compile(
    r"^(?:<[^>\r\n]+>|\[[^\]\r\n]+\]|[A-Za-z0-9_.():/-]+[>#])$"
)


def normalize_host(value: str) -> str:
    """Remove display-only brackets from an IPv4 or IPv6 address."""
    host = str(value or "").strip()
    if host.startswith("[") and host.endswith("]"):
        return host[1:-1].strip()
    return host


def parse_tcp_ports(value: str) -> list[int]:
    """Parse comma/space separated TCP ports and remove duplicates."""
    tokens = re.split(r"[\s,，;；]+", str(value or "").strip())
    ports: list[int] = []
    seen = set()
    for token in tokens:
        if not token:
            continue
        if not token.isdigit():
            raise ValueError(f"端口“{token}”不是有效数字")
        port = int(token)
        if not 1 <= port <= 65535:
            raise ValueError(f"端口 {port} 超出 1-65535 范围")
        if port not in seen:
            seen.add(port)
            ports.append(port)
    if not ports:
        raise ValueError("请至少输入一个 TCP 端口")
    return ports


def check_tcp_port(host: str, port: int, timeout: float = 1.5) -> tuple[bool, str]:
    """Try a TCP connection without sending application data."""
    try:
        with socket.create_connection((normalize_host(host), int(port)), timeout=timeout):
            return True, "端口开放"
    except socket.timeout:
        return False, "连接超时"
    except ConnectionRefusedError:
        return False, "连接被拒绝"
    except OSError as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        return False, detail


def run_traceroute(host: str, timeout: int = 45) -> tuple[bool, str]:
    """Run the operating system traceroute command and return its raw output."""
    target = normalize_host(host)
    if sys.platform.startswith("win"):
        command = ["tracert", "-d", "-h", "20", "-w", "1200", target]
        creation_flags = subprocess.CREATE_NO_WINDOW
    else:
        command = ["traceroute", "-n", "-m", "20", "-w", "2", target]
        creation_flags = 0

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            creationflags=creation_flags,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or exc.stderr or ""
        return False, f"路由跟踪超时\n{partial}".strip()
    except OSError as exc:
        return False, f"无法启动路由跟踪命令: {exc}"

    output = (result.stdout or result.stderr or "").strip()
    if not output:
        output = "系统未返回路由跟踪结果"
    return result.returncode == 0, output


def read_text_file(path: str) -> str:
    """Read common network configuration encodings."""
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return Path(path).read_text(encoding=encoding)
        except UnicodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return Path(path).read_text()


def unified_config_diff(first_path: str, second_path: str) -> str:
    """Return a line-oriented unified diff for two configuration files."""
    first = read_text_file(first_path).splitlines()
    second = read_text_file(second_path).splitlines()
    diff = difflib.unified_diff(
        first,
        second,
        fromfile=os.path.basename(first_path),
        tofile=os.path.basename(second_path),
        lineterm="",
    )
    return "\n".join(diff) or "两个配置文件内容一致。"


def normalize_device_config(output: str, command: str = "") -> str:
    """Remove terminal-only artifacts while preserving configuration lines."""
    text = _ANSI_ESCAPE_RE.sub("", str(output or ""))
    while "\b" in text:
        cleaned = re.sub(r"[^\r\n]\x08", "", text)
        if cleaned == text:
            break
        text = cleaned
    text = text.replace("\x08", "").replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    command_text = str(command or "").strip()
    command_pattern = None
    if command_text:
        command_pattern = re.compile(
            rf"^(?:(?:<[^>]+>|\[[^\]]+\]|"
            rf"[A-Za-z0-9_.():/-]+[>#])\s*)?"
            rf"{re.escape(command_text)}$",
            re.IGNORECASE,
        )

    lines = []
    command_echo_removed = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if _PAGING_LINE_RE.fullmatch(stripped):
            continue
        if (
            command_pattern is not None
            and not command_echo_removed
            and command_pattern.fullmatch(stripped)
        ):
            command_echo_removed = True
            continue
        if _PROMPT_LINE_RE.fullmatch(stripped):
            continue
        lines.append(line)

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def write_config_backup(
    output_dir: str,
    *,
    device_name: str,
    device_ip: str,
    device_port: int,
    brand: str,
    command: str,
    config_text: str,
    backup_time: datetime | None = None,
) -> tuple[str, str]:
    """Write a versioned .cfg plus a non-sensitive JSON sidecar."""
    content = str(config_text or "").rstrip() + "\n"
    if not content.strip():
        raise ValueError("配置内容为空")

    created_at = backup_time or datetime.now()
    safe_device_name = safe_filename(device_name or device_ip)
    device_dir = Path(output_dir) / safe_device_name
    timestamp = created_at.strftime("%Y%m%d_%H%M%S")

    with _BACKUP_WRITE_LOCK:
        device_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{safe_device_name}_{timestamp}"
        suffix = 1
        while (
            (device_dir / f"{stem}.cfg").exists()
            or (device_dir / f"{stem}.json").exists()
        ):
            suffix += 1
            stem = f"{safe_device_name}_{timestamp}_{suffix}"

        config_path = device_dir / f"{stem}.cfg"
        metadata_path = device_dir / f"{stem}.json"
        content_bytes = content.encode("utf-8")
        config_path.write_bytes(content_bytes)

        metadata = {
            "schema": "aomt.config-backup.v1",
            "device": {
                "name": str(device_name or ""),
                "ip": str(device_ip or ""),
                "port": int(device_port or 22),
            },
            "backup": {
                "created_at": created_at.isoformat(timespec="seconds"),
                "brand": str(brand or ""),
                "query_command": str(command or ""),
                "config_file": config_path.name,
                "content_type": "text/plain",
                "encoding": "utf-8",
                "line_count": len(content.splitlines()),
                "sha256": hashlib.sha256(content_bytes).hexdigest(),
            },
        }
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return str(config_path), str(metadata_path)


def _ipv6_address_type(address: ipaddress.IPv6Address) -> str:
    if address.is_unspecified:
        return "未指定地址"
    if address.is_loopback:
        return "环回地址"
    if address.is_multicast:
        return "组播地址"
    if address.is_link_local:
        return "链路本地地址"
    if address.is_global:
        return "全局单播地址"
    if address.is_private:
        return "唯一本地或非公网地址"
    if address.is_reserved:
        return "保留地址"
    return "特殊用途地址"


def _power_count(exponent: int) -> str:
    count = 1 << exponent
    return f"2^{exponent} = {count:,}"


def calculate_subnet(value: str) -> list[tuple[str, str]]:
    """Calculate human-readable IPv4 or IPv6 subnet information."""
    text = str(value or "").strip()
    if "/" not in text:
        raise ValueError("请输入带前缀长度的地址，例如 192.168.1.10/24")
    try:
        interface = ipaddress.ip_interface(text)
    except ValueError as exc:
        raise ValueError(f"地址或前缀无效: {exc}") from exc

    network = interface.network
    rows = [
        ("IP 版本", f"IPv{interface.version}"),
        ("输入地址", str(interface.ip)),
        ("前缀长度", f"/{network.prefixlen}"),
        ("网络地址", str(network.network_address)),
        ("地址总数", str(network.num_addresses)),
    ]

    if interface.version == 4:
        rows.extend([
            ("子网掩码", str(network.netmask)),
            ("反掩码", str(network.hostmask)),
            ("广播地址", str(network.broadcast_address)),
        ])
        if network.num_addresses > 2:
            first_host = network.network_address + 1
            last_host = network.broadcast_address - 1
            usable = network.num_addresses - 2
        else:
            first_host = network.network_address
            last_host = network.broadcast_address
            usable = network.num_addresses
        rows.extend([
            ("首个可用地址", str(first_host)),
            ("最后可用地址", str(last_host)),
            ("可用地址数", str(usable)),
        ])
    else:
        host_bits = 128 - network.prefixlen
        host_value = int(interface.ip) - int(network.network_address)
        host_hex_width = max(1, (host_bits + 3) // 4)
        containing_64 = ipaddress.ip_network(f"{interface.ip}/64", strict=False)
        if network.prefixlen < 64:
            relation_64 = (
                f"可划分 {_power_count(64 - network.prefixlen)} 个 /64 子网"
            )
        elif network.prefixlen == 64:
            relation_64 = "当前网络就是一个 /64 子网"
        else:
            relation_64 = (
                f"所在 /64 可划分 {_power_count(network.prefixlen - 64)} "
                f"个 /{network.prefixlen} 子网"
            )
        solicited_node = ipaddress.IPv6Address(
            int(ipaddress.IPv6Address("ff02::1:ff00:0"))
            | (int(interface.ip) & 0xFFFFFF)
        )
        rows.extend([
            ("压缩地址", interface.ip.compressed),
            ("完整地址", interface.ip.exploded),
            ("地址类型", _ipv6_address_type(interface.ip)),
            ("IPv6 掩码", str(network.netmask)),
            ("主机位数", str(host_bits)),
            ("主机标识", f"0x{host_value:0{host_hex_width}x}"),
            ("首个地址", str(network.network_address)),
            ("最后地址", str(network[-1])),
            ("地址范围", f"{network.network_address} - {network[-1]}"),
            ("精确地址数", _power_count(host_bits)),
            ("所在 /64", containing_64.with_prefixlen),
            ("/64 划分关系", relation_64),
            ("请求节点组播", str(solicited_node)),
            ("反向解析域名", interface.ip.reverse_pointer),
            ("完整网络", network.with_prefixlen),
        ])
    return rows


def safe_filename(value: str, fallback: str = "device") -> str:
    """Create a Windows-safe file-name component."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "").strip())
    cleaned = cleaned.rstrip(" .")
    return cleaned or fallback


def write_lines(path: str, lines: Iterable[str]) -> None:
    Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
