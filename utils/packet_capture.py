"""Wireshark-backed packet capture helpers for Windows."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


class PacketCaptureError(RuntimeError):
    pass


@dataclass(frozen=True)
class WiresharkTools:
    dumpcap: str
    tshark: str
    wireshark: str


@dataclass(frozen=True)
class CaptureInterface:
    index: int
    identifier: str
    description: str

    @property
    def label(self) -> str:
        return f"{self.description}  |  {self.identifier}"


@dataclass(frozen=True)
class PacketCaptureConfig:
    interface: str
    output_file: str
    capture_filter: str = ""
    duration_seconds: int = 60
    packet_limit: int = 0
    file_size_kb: int = 102400
    promiscuous: bool = True

    def validate(self) -> None:
        if not str(self.interface or "").strip():
            raise PacketCaptureError("请选择抓包网卡")
        output = Path(self.output_file)
        if output.suffix.lower() != ".pcapng":
            raise PacketCaptureError("抓包文件必须使用 .pcapng 扩展名")
        if any(
            value < 0
            for value in (
                self.duration_seconds,
                self.packet_limit,
                self.file_size_kb,
            )
        ):
            raise PacketCaptureError("停止条件不能为负数")
        if not any(
            (
                self.duration_seconds,
                self.packet_limit,
                self.file_size_kb,
            )
        ):
            raise PacketCaptureError(
                "为防止占满磁盘，请至少设置抓包时长、包数或文件大小限制"
            )


def find_wireshark_tools(extra_roots=None) -> Optional[WiresharkTools]:
    roots = []
    env_root = os.environ.get("WIRESHARK_INSTALL_DIR", "").strip()
    if env_root:
        roots.append(Path(env_root))
    for root in extra_roots or ():
        roots.append(Path(root))
    for variable in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variable, "").strip()
        if base:
            roots.append(Path(base) / "Wireshark")
    roots.append(Path(r"C:\Program Files\Wireshark"))

    seen = set()
    for root in roots:
        normalized = str(root).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        tools = _tools_from_root(root)
        if tools:
            return tools

    dumpcap = shutil.which("dumpcap")
    tshark = shutil.which("tshark")
    wireshark = shutil.which("wireshark")
    if dumpcap and tshark and wireshark:
        return WiresharkTools(dumpcap, tshark, wireshark)
    return None


def _tools_from_root(root: Path) -> Optional[WiresharkTools]:
    paths = {
        "dumpcap": root / "dumpcap.exe",
        "tshark": root / "tshark.exe",
        "wireshark": root / "Wireshark.exe",
    }
    if all(path.is_file() for path in paths.values()):
        return WiresharkTools(*(str(paths[name]) for name in paths))
    return None


def parse_dumpcap_interfaces(output: str) -> list[CaptureInterface]:
    interfaces = []
    for line in str(output or "").splitlines():
        match = re.match(r"^\s*(\d+)\.\s+(\S+)(?:\s+\((.*)\))?\s*$", line)
        if not match:
            continue
        index = int(match.group(1))
        identifier = match.group(2).strip()
        description = (match.group(3) or identifier).strip()
        interfaces.append(CaptureInterface(index, identifier, description))
    return interfaces


def list_capture_interfaces(
    tools: WiresharkTools,
    *,
    timeout: float = 8,
) -> list[CaptureInterface]:
    completed = subprocess.run(
        [tools.dumpcap, "-D"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=_no_window_flag(),
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    interfaces = parse_dumpcap_interfaces(output)
    if completed.returncode != 0 or not interfaces:
        detail = output.strip() or f"退出码 {completed.returncode}"
        raise PacketCaptureError(f"无法读取抓包网卡：{detail}")
    return interfaces


def default_capture_directory() -> str:
    return str(Path.home() / "Documents" / "AOMT_Captures")


def new_capture_path(
    output_directory: str,
    *,
    now: Optional[datetime] = None,
) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return str(Path(output_directory).expanduser() / f"capture_{timestamp}.pcapng")


def build_dumpcap_command(
    tools: WiresharkTools,
    config: PacketCaptureConfig,
) -> list[str]:
    config.validate()
    command = [
        tools.dumpcap,
        "-i",
        config.interface,
        "-F",
        "pcapng",
        "-w",
        config.output_file,
        "-q",
    ]
    capture_filter = str(config.capture_filter or "").strip()
    if capture_filter:
        command.extend(["-f", capture_filter])
    if config.duration_seconds:
        command.extend(["-a", f"duration:{int(config.duration_seconds)}"])
    if config.packet_limit:
        command.extend(["-a", f"packets:{int(config.packet_limit)}"])
    if config.file_size_kb:
        command.extend(["-a", f"filesize:{int(config.file_size_kb)}"])
    if not config.promiscuous:
        command.append("-p")
    return command


def capture_file_summary(
    tools: WiresharkTools,
    capture_file: str,
    *,
    timeout: float = 15,
) -> dict:
    path = Path(capture_file)
    if not path.is_file():
        return {"packets": 0, "bytes": 0, "duration": 0.0}
    completed = subprocess.run(
        [
            tools.tshark,
            "-r",
            str(path),
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "frame.time_relative",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=_no_window_flag(),
    )
    packets = 0
    duration = 0.0
    for line in completed.stdout.splitlines():
        fields = line.split("\t")
        if not fields or not fields[0].strip().isdigit():
            continue
        packets += 1
        if len(fields) > 1:
            try:
                duration = max(duration, float(fields[1].strip() or 0))
            except ValueError:
                pass
    return {
        "packets": packets,
        "bytes": path.stat().st_size,
        "duration": duration,
    }


_ANALYSIS_FIELDS = (
    "frame.number",
    "frame.time_relative",
    "frame.len",
    "_ws.col.Protocol",
    "eth.src",
    "eth.dst",
    "ip.src",
    "ip.dst",
    "ipv6.src",
    "ipv6.dst",
    "tcp.flags.syn",
    "tcp.flags.ack",
    "tcp.flags.reset",
    "tcp.analysis.retransmission",
    "tcp.analysis.fast_retransmission",
    "tcp.analysis.lost_segment",
    "icmp.type",
    "icmpv6.type",
    "arp.opcode",
    "arp.src.proto_ipv4",
    "arp.src.hw_mac",
    "dns.flags.response",
    "dns.flags.rcode",
    "dns.qry.name",
    "stp.root.hw",
    "stp.flags.tc",
    "dhcp.option.dhcp",
)


def capture_file_analysis(
    tools: WiresharkTools,
    capture_file: str,
    *,
    timeout: float = 60,
) -> dict:
    """Build a concise Chinese diagnostic summary from a pcapng file."""
    path = Path(capture_file)
    if not path.is_file():
        raise PacketCaptureError("抓包文件不存在")

    command = [
        tools.tshark,
        "-r",
        str(path),
        "-T",
        "fields",
        "-E",
        "separator=/t",
        "-E",
        "occurrence=f",
    ]
    for field in _ANALYSIS_FIELDS:
        command.extend(["-e", field])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=_no_window_flag(),
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"退出码 {completed.returncode}"
        raise PacketCaptureError(f"TShark 分析失败：{detail}")

    stats = _new_analysis_stats(path)
    for raw_line in completed.stdout.splitlines():
        values = raw_line.split("\t")
        if not values or not values[0].strip().isdigit():
            continue
        if len(values) < len(_ANALYSIS_FIELDS):
            values.extend([""] * (len(_ANALYSIS_FIELDS) - len(values)))
        row = dict(zip(_ANALYSIS_FIELDS, values))
        _accumulate_analysis_row(stats, row)

    stats["lines"] = _format_analysis_lines(stats)
    return stats


def _new_analysis_stats(path: Path) -> dict:
    return {
        "packets": 0,
        "bytes": path.stat().st_size,
        "wire_bytes": 0,
        "duration": 0.0,
        "protocols": Counter(),
        "endpoints": Counter(),
        "conversations": Counter(),
        "icmp_requests": 0,
        "icmp_replies": 0,
        "arp_mappings": {},
        "stp_packets": 0,
        "stp_roots": Counter(),
        "stp_topology_changes": 0,
        "tcp_packets": 0,
        "tcp_syn": 0,
        "tcp_syn_ack": 0,
        "tcp_resets": 0,
        "tcp_retransmissions": 0,
        "tcp_lost_segments": 0,
        "dns_packets": 0,
        "dns_errors": Counter(),
        "dhcp_packets": 0,
    }


def _accumulate_analysis_row(stats: dict, row: dict) -> None:
    stats["packets"] += 1
    stats["duration"] = max(
        stats["duration"],
        _as_float(row["frame.time_relative"]),
    )
    stats["wire_bytes"] += _as_int(row["frame.len"])

    protocol = row["_ws.col.Protocol"].strip() or "未知"
    stats["protocols"][protocol] += 1

    source = row["ip.src"].strip() or row["ipv6.src"].strip()
    destination = row["ip.dst"].strip() or row["ipv6.dst"].strip()
    if source:
        stats["endpoints"][source] += 1
    if destination:
        stats["endpoints"][destination] += 1
    if source and destination:
        stats["conversations"][tuple(sorted((source, destination)))] += 1

    icmp_type = _as_int(row["icmp.type"], default=-1)
    icmpv6_type = _as_int(row["icmpv6.type"], default=-1)
    if icmp_type == 8 or icmpv6_type == 128:
        stats["icmp_requests"] += 1
    elif icmp_type == 0 or icmpv6_type == 129:
        stats["icmp_replies"] += 1

    arp_ip = row["arp.src.proto_ipv4"].strip()
    arp_mac = row["arp.src.hw_mac"].strip()
    if arp_ip and arp_mac and arp_ip != "0.0.0.0":
        stats["arp_mappings"][arp_ip] = arp_mac

    stp_root = row["stp.root.hw"].strip()
    if protocol.upper() in {"STP", "MSTP", "RSTP"} or stp_root:
        stats["stp_packets"] += 1
    if stp_root:
        stats["stp_roots"][stp_root] += 1
    if _is_true(row["stp.flags.tc"]):
        stats["stp_topology_changes"] += 1

    has_tcp = any(
        row[field].strip()
        for field in (
            "tcp.flags.syn",
            "tcp.flags.ack",
            "tcp.flags.reset",
            "tcp.analysis.retransmission",
            "tcp.analysis.fast_retransmission",
            "tcp.analysis.lost_segment",
        )
    ) or protocol.upper() == "TCP"
    if has_tcp:
        stats["tcp_packets"] += 1
        syn = _is_true(row["tcp.flags.syn"])
        ack = _is_true(row["tcp.flags.ack"])
        stats["tcp_syn"] += int(syn and not ack)
        stats["tcp_syn_ack"] += int(syn and ack)
        stats["tcp_resets"] += int(_is_true(row["tcp.flags.reset"]))
        stats["tcp_retransmissions"] += int(
            bool(
                row["tcp.analysis.retransmission"].strip()
                or row["tcp.analysis.fast_retransmission"].strip()
            )
        )
        stats["tcp_lost_segments"] += int(
            bool(row["tcp.analysis.lost_segment"].strip())
        )

    dns_response = row["dns.flags.response"].strip()
    dns_rcode = _as_int(row["dns.flags.rcode"], default=0)
    if protocol.upper() == "DNS" or dns_response:
        stats["dns_packets"] += 1
    if _is_true(dns_response) and dns_rcode:
        stats["dns_errors"][dns_rcode] += 1

    if protocol.upper() in {"DHCP", "DHCPV6", "BOOTP"} or row[
        "dhcp.option.dhcp"
    ].strip():
        stats["dhcp_packets"] += 1


def _format_analysis_lines(stats: dict) -> list[str]:
    if not stats["packets"]:
        return [
            "没有捕获到可分析的数据包。",
            "请检查抓包网卡、过滤条件以及交换机端口镜像配置。",
        ]

    lines = [
        "自动分析结论",
        "协议分布：" + _format_counter(stats["protocols"], limit=8),
    ]
    if stats["conversations"]:
        conversations = []
        for (source, destination), count in stats["conversations"].most_common(5):
            conversations.append(f"{source} ↔ {destination}（{count} 包）")
        lines.append("主要通信：" + "；".join(conversations))
    elif stats["endpoints"]:
        lines.append("主要端点：" + _format_counter(stats["endpoints"], limit=5))

    requests = stats["icmp_requests"]
    replies = stats["icmp_replies"]
    if requests or replies:
        missing = max(0, requests - replies)
        result = "未发现应答缺失" if not missing else f"可能缺少 {missing} 个应答"
        lines.append(f"Ping：{requests} 个请求，{replies} 个应答，{result}。")

    if stats["arp_mappings"]:
        mappings = [
            f"{ip} → {mac}"
            for ip, mac in sorted(stats["arp_mappings"].items())[:8]
        ]
        lines.append("ARP 映射：" + "；".join(mappings))

    if stats["stp_packets"]:
        roots = "、".join(root for root, _count in stats["stp_roots"].most_common(3))
        root_text = roots or "未解析到根桥 MAC"
        lines.append(
            f"STP/MSTP：{stats['stp_packets']} 个报文，根桥 {root_text}，"
            f"拓扑变化标志 {stats['stp_topology_changes']} 次。"
        )

    if stats["tcp_packets"]:
        lines.append(
            f"TCP：{stats['tcp_packets']} 个报文，"
            f"重传 {stats['tcp_retransmissions']}，"
            f"疑似缺失段 {stats['tcp_lost_segments']}，"
            f"连接复位 {stats['tcp_resets']}。"
        )

    if stats["dns_packets"]:
        errors = sum(stats["dns_errors"].values())
        lines.append(f"DNS：{stats['dns_packets']} 个报文，错误响应 {errors}。")

    alerts = []
    if requests > replies:
        alerts.append("Ping 应答不完整")
    if stats["tcp_retransmissions"]:
        alerts.append("存在 TCP 重传")
    if stats["tcp_lost_segments"]:
        alerts.append("存在疑似未捕获或丢失的 TCP 段")
    if stats["tcp_resets"]:
        alerts.append("存在 TCP 连接复位")
    if stats["dns_errors"]:
        alerts.append("存在 DNS 错误响应")
    if stats["stp_topology_changes"]:
        alerts.append("出现 STP 拓扑变化标志")
    if alerts:
        lines.append("需要关注：" + "；".join(alerts) + "。")
    else:
        lines.append(
            "综合判断：在本次捕获范围内，未发现明显的 Ping 应答缺失、"
            "TCP 重传/复位、DNS 错误或 STP 拓扑变化。"
        )
    lines.append("说明：自动分析仅针对已捕获流量，不能替代完整的 Wireshark 人工诊断。")
    return lines


def _format_counter(counter: Counter, *, limit: int) -> str:
    return "，".join(f"{name} {count}" for name, count in counter.most_common(limit))


def _as_int(value: str, *, default: int = 0) -> int:
    try:
        return int(str(value or "").strip(), 0)
    except (TypeError, ValueError):
        return default


def _as_float(value: str, *, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return default


def _is_true(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "set"}


class PacketCaptureSession:
    """Run Dumpcap in the background and expose explicit stop semantics."""

    def __init__(
        self,
        tools: WiresharkTools,
        config: PacketCaptureConfig,
        on_message: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[int], None]] = None,
    ):
        self.tools = tools
        self.config = config
        self.on_message = on_message or (lambda _message: None)
        self.on_finished = on_finished or (lambda _code: None)
        self._process = None
        self._monitor_thread = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        command = build_dumpcap_command(self.tools, self.config)
        output_path = Path(self.config.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                raise PacketCaptureError("抓包任务已经在运行")
            try:
                self._process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=_no_window_flag(),
                )
            except OSError as exc:
                raise PacketCaptureError(f"无法启动 Dumpcap：{exc}") from exc
        self._monitor_thread = threading.Thread(
            target=self._monitor,
            name="AOMT-PacketCapture",
            daemon=True,
        )
        self._monitor_thread.start()

    def _monitor(self):
        process = self._process
        if process is None:
            return
        if process.stdout is not None:
            for line in process.stdout:
                message = line.strip()
                if message:
                    self.on_message(message)
        return_code = process.wait()
        self.on_finished(return_code)

    def stop(self, timeout: float = 3) -> None:
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
        except OSError:
            return
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)

    def wait(self, timeout: Optional[float] = None) -> None:
        thread = self._monitor_thread
        if thread is not None:
            thread.join(timeout=timeout)


def open_capture_in_wireshark(tools: WiresharkTools, capture_file: str) -> None:
    path = Path(capture_file)
    if not path.is_file():
        raise PacketCaptureError("抓包文件不存在")
    try:
        subprocess.Popen(
            [tools.wireshark, str(path)],
            creationflags=_no_window_flag(),
        )
    except OSError as exc:
        raise PacketCaptureError(f"无法打开 Wireshark：{exc}") from exc


def _no_window_flag() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)
