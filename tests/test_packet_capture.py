import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import utils.packet_capture as packet_capture
from ui.packet_capture_dialog import PacketCaptureDialog
from utils.packet_capture import (
    CaptureInterface,
    PacketCaptureConfig,
    PacketCaptureError,
    WiresharkTools,
    build_dumpcap_command,
    capture_file_analysis,
    find_wireshark_tools,
    new_capture_path,
    parse_dumpcap_interfaces,
)


def _fake_tools(root):
    root.mkdir()
    for name in ("dumpcap.exe", "tshark.exe", "Wireshark.exe"):
        (root / name).write_bytes(b"fake")
    return WiresharkTools(
        str(root / "dumpcap.exe"),
        str(root / "tshark.exe"),
        str(root / "Wireshark.exe"),
    )


def test_find_wireshark_tools_and_parse_windows_interfaces(tmp_path):
    expected = _fake_tools(tmp_path / "Wireshark")
    assert find_wireshark_tools([tmp_path / "Wireshark"]) == expected

    interfaces = parse_dumpcap_interfaces(
        "1. \\Device\\NPF_{ABC} (以太网)\n"
        "2. \\Device\\NPF_Loopback (Adapter for loopback traffic capture)\n"
    )
    assert interfaces == [
        CaptureInterface(1, r"\Device\NPF_{ABC}", "以太网"),
        CaptureInterface(
            2,
            r"\Device\NPF_Loopback",
            "Adapter for loopback traffic capture",
        ),
    ]


def test_build_dumpcap_command_uses_argument_list_and_safety_limits(tmp_path):
    tools = WiresharkTools("dumpcap", "tshark", "wireshark")
    output = tmp_path / "capture.pcapng"
    config = PacketCaptureConfig(
        interface=r"\Device\NPF_{ABC}",
        output_file=str(output),
        capture_filter="host 192.168.10.10 and tcp port 22",
        duration_seconds=30,
        packet_limit=500,
        file_size_kb=2048,
        promiscuous=False,
    )
    command = build_dumpcap_command(tools, config)

    assert command[:3] == ["dumpcap", "-i", r"\Device\NPF_{ABC}"]
    assert command[command.index("-f") + 1] == config.capture_filter
    assert "duration:30" in command
    assert "packets:500" in command
    assert "filesize:2048" in command
    assert command[-1] == "-p"

    with pytest.raises(PacketCaptureError, match="至少设置"):
        PacketCaptureConfig(
            interface="1",
            output_file=str(output),
            duration_seconds=0,
            packet_limit=0,
            file_size_kb=0,
        ).validate()


def test_capture_filename_is_pcapng_and_timestamped(tmp_path):
    path = new_capture_path(
        str(tmp_path),
        now=datetime(2026, 7, 30, 12, 34, 56),
    )
    assert Path(path).name == "capture_20260730_123456.pcapng"


def test_capture_analysis_builds_chinese_network_findings(monkeypatch, tmp_path):
    capture_file = tmp_path / "sample.pcapng"
    capture_file.write_bytes(b"pcapng-data")

    def row(**fields):
        return "\t".join(
            str(fields.get(field, ""))
            for field in packet_capture._ANALYSIS_FIELDS
        )

    output = "\n".join(
        (
            row(
                **{
                    "frame.number": 1,
                    "frame.time_relative": "0.1",
                    "frame.len": 74,
                    "_ws.col.Protocol": "ICMP",
                    "ip.src": "192.168.10.10",
                    "ip.dst": "192.168.10.20",
                    "icmp.type": 8,
                }
            ),
            row(
                **{
                    "frame.number": 2,
                    "frame.time_relative": "0.2",
                    "frame.len": 74,
                    "_ws.col.Protocol": "ICMP",
                    "ip.src": "192.168.10.20",
                    "ip.dst": "192.168.10.10",
                    "icmp.type": 0,
                }
            ),
            row(
                **{
                    "frame.number": 3,
                    "frame.time_relative": "0.3",
                    "frame.len": 60,
                    "_ws.col.Protocol": "ARP",
                    "arp.opcode": 2,
                    "arp.src.proto_ipv4": "192.168.10.20",
                    "arp.src.hw_mac": "00:11:22:33:44:55",
                }
            ),
            row(
                **{
                    "frame.number": 4,
                    "frame.time_relative": "0.4",
                    "frame.len": 120,
                    "_ws.col.Protocol": "STP",
                    "stp.root.hw": "00:aa:bb:cc:dd:ee",
                    "stp.flags.tc": "False",
                }
            ),
        )
    )
    monkeypatch.setattr(
        packet_capture.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=output,
            stderr="",
        ),
    )

    analysis = capture_file_analysis(
        WiresharkTools("dumpcap", "tshark", "wireshark"),
        str(capture_file),
    )
    report = "\n".join(analysis["lines"])

    assert analysis["packets"] == 4
    assert analysis["icmp_requests"] == 1
    assert analysis["icmp_replies"] == 1
    assert analysis["arp_mappings"]["192.168.10.20"] == "00:11:22:33:44:55"
    assert "ICMP 2" in report
    assert "未发现应答缺失" in report
    assert "根桥 00:aa:bb:cc:dd:ee" in report
    assert "未发现明显" in report


def test_packet_capture_dialog_loads_interfaces_and_builds_session(
    monkeypatch,
    tmp_path,
):
    app = QApplication.instance() or QApplication([])
    tools = WiresharkTools("dumpcap", "tshark", "wireshark")
    interfaces = [
        CaptureInterface(1, r"\Device\NPF_{ABC}", "以太网"),
        CaptureInterface(2, r"\Device\NPF_Loopback", "回环接口"),
    ]
    created = {}

    class FakeSession:
        def __init__(self, received_tools, config, on_message, on_finished):
            created["tools"] = received_tools
            created["config"] = config
            self.is_running = False

        def start(self):
            self.is_running = True

        def stop(self, timeout=3):
            self.is_running = False

        def wait(self, timeout=None):
            return None

    monkeypatch.setattr(
        "ui.packet_capture_dialog.find_wireshark_tools",
        lambda: tools,
    )
    monkeypatch.setattr(
        "ui.packet_capture_dialog.list_capture_interfaces",
        lambda _tools: interfaces,
    )
    monkeypatch.setattr(
        "ui.packet_capture_dialog.PacketCaptureSession",
        FakeSession,
    )

    dialog = PacketCaptureDialog()
    try:
        dialog.output_input.setText(str(tmp_path))
        dialog.duration_spin.setValue(15)
        dialog.file_size_spin.setValue(10)
        dialog.preset_combo.setCurrentIndex(3)
        app.processEvents()

        assert dialog.windowFlags() & Qt.WindowMaximizeButtonHint
        assert dialog.interface_combo.count() == 2
        assert dialog.filter_input.text() == "tcp port 22"

        dialog.start_capture()
        config = created["config"]
        assert created["tools"] == tools
        assert config.interface == r"\Device\NPF_{ABC}"
        assert config.duration_seconds == 15
        assert config.file_size_kb == 10 * 1024
        assert config.output_file.endswith(".pcapng")
        assert dialog.stop_button.isEnabled()
        dialog.session.is_running = False
        dialog._summary_completed(
            {
                "packets": 4,
                "bytes": 512,
                "duration": 1.2,
                "lines": ["自动分析结论", "综合判断：未发现明显异常。"],
            }
        )
        assert dialog.result_tabs.currentWidget() is dialog.analysis_output
        assert "自动分析结论" in dialog.analysis_output.toPlainText()
    finally:
        dialog.close()
