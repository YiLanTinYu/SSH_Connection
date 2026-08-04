import pytest

from config.device_config import DeviceInfo
from ui import device_diagnostics_worker
from ui.device_diagnostics_worker import DeviceDiagnosticsWorker
from utils.device_diagnostics import (
    choose_discovered_mac,
    extract_mac_addresses,
    get_health_commands,
    get_lookup_command,
    normalize_lookup_target,
    normalize_mac,
    parse_comware_output,
    parse_device_output,
    summarize_health,
    summarize_interface,
    summarize_mac_locations,
    validate_interface_name,
)


CPU_OUTPUT = """\
CPU Usage:
 CPU        Last 5 sec        Last 1 min        Last 5 min
 0          12%               18%               15%
"""

MEMORY_OUTPUT = """\
Memory statistics are measured in KB:
 Slot 1:
             total       used       free     shared    buffers     cached   free_ratio
Mem:       1000000     400000     600000          0          0          0        60.0%
"""

ENVIRONMENT_OUTPUT = """\
Slot  Sensor       Temperature  Lower  Warning  Alarm
1     hotspot 1    45           0      70       90
"""

FAN_OUTPUT = """\
Slot 1
 Fan 1
 State : Normal
"""

POWER_OUTPUT = """\
Slot 1
1 Normal AC 1.0 220.0 200.0
"""

INTERFACE_BRIEF_OUTPUT = """\
Brief information on interfaces in bridge mode:
Link: ADM - administratively down; Stby - standby
Speed or Duplex: (a)/A - auto; H - half; F - full
Type: A - access; T - trunk; H - hybrid
Interface            Link Speed   Duplex Type PVID Description
GE1/0/1              UP   1G(a)   F(a)   A    10   Office
GE1/0/2              DOWN auto    A      A    20   Spare
"""

INTERFACE_OUTPUT = """\
GigabitEthernet1/0/1
Current state: UP
Line protocol state: UP
Description: Office
1Gbps-speed mode, full-duplex mode
Port link-type: Access
PVID: 10
"""

HUAWEI_CPU_OUTPUT = """\
CPU Usage Stat. Cycle: 60 (Second)
CPU Usage            : 28% Max: 87%
CPU utilization for five seconds: 28%: one minute: 25%: five minutes: 20%
"""

HUAWEI_MEMORY_OUTPUT = """\
System Total Memory Is: 536870912 bytes
Total Memory Used Is: 134217728 bytes
Memory Using Percentage Is: 25%
"""

HUAWEI_TEMPERATURE_OUTPUT = """\
0 :
Base 0 0 0 Normal 0 0 0 0 0 45
"""

HUAWEI_INTERFACE_BRIEF_OUTPUT = """\
GE1/0/1 up up 1% 2% 0 0
GE1/0/2 down down 0% 0% 0 0
"""

HUAWEI_INTERFACE_OUTPUT = """\
GigabitEthernet1/0/1 current state : UP
Line protocol current state : UP
Description:Office
Switch Port, Link-type : access,
PVID : 10, The Maximum Frame Length is 9216
Speed : 1000, Loopback: NONE
Duplex: FULL, Negotiation: ENABLE
"""

COMWARE_S6850_POWER_OUTPUT = """\
Device Info on Slot 1:
Device ID.  Status
 1          Normal
 2          Normal
<H3C>
"""

COMWARE_S6850_MANUINFO_OUTPUT = """\
Slot 1 CPU 0:
DEVICE_ID:Slot ID:1
DEVICE_NAME:Simware
DEVICE_SERIAL_NUMBER:REDACTED
VENDOR_NAME:H3C
Fan 1:
DEVICE_ID:Fan ID:1
DEVICE_NAME:Simware
DEVICE_SERIAL_NUMBER:REDACTED
VENDOR_NAME:H3C
<H3C>
"""

HUAWEI_S5720_TEMPERATURE_OUTPUT = """\
Slot  Card  Sensor Status    Current(C) Lower(C) Lower Resume(C) Upper(C) Upper Resume(C)
0     NA    NA     Normal            44        0         4       61        57
<HUAWEI>
"""

HUAWEI_S5720_FAN_OUTPUT = """\
Slot  FanID   Online    Status    Speed     Mode     Airflow         Auto Min-Speed
0         1   Present   Normal      30%     Auto     Side-to-Side                0%
<HUAWEI>
"""

HUAWEI_S5720_POWER_OUTPUT = """\
Slot    PowerID  Online   Mode   State      Power(W)
0       PWR1     Present  AC     Supply        60.00
0       PWR2     Absent   -      -                 -
<HUAWEI>
"""

HUAWEI_S5720_DEVICE_OUTPUT = """\
Slot Sub  Type                   Online    Power    Register     Status   Role
0    -    S5720-28X-SI           Present   PowerOn  Registered   Normal   Master
     PWR1 POWER                  Present   PowerOn  Registered   Normal   NA
<HUAWEI>
"""


def test_ntc_templates_parse_comware_arp_mac_and_interfaces():
    arp = parse_comware_output(
        "display arp",
        "192.168.10.20 0011-2233-4455 10 GE1/0/1 20 D\n",
    )
    mac = parse_comware_output(
        "display mac-address",
        "0011-2233-4455 10 Learned GE1/0/1 Y\n",
    )
    brief = parse_comware_output(
        "display interface brief", INTERFACE_BRIEF_OUTPUT
    )

    assert arp[0]["ip_address"] == "192.168.10.20"
    assert extract_mac_addresses(arp) == ["0011-2233-4455"]
    assert mac[0]["interface"] == "GE1/0/1"
    assert brief[0]["link"] == "UP"
    assert brief[0]["vlan_id"] == "10"


def test_napalm_h3c_templates_parse_health_outputs():
    assert parse_comware_output(
        "display cpu-usage summary", CPU_OUTPUT
    )[0]["one_min"] == "18"
    assert parse_comware_output(
        "display memory", MEMORY_OUTPUT
    )[0]["free_ratio"] == "60.0"
    assert parse_comware_output(
        "display environment", ENVIRONMENT_OUTPUT
    )[0]["temperature"] == "45"
    assert parse_comware_output("display fan", FAN_OUTPUT)[0]["status"] == "Normal"
    assert parse_comware_output("display power", POWER_OUTPUT)[0]["status"] == "Normal"


def test_huawei_vrp_ntc_templates_and_profile_commands():
    arp = parse_device_output(
        "huawei",
        "display arp all",
        "192.168.10.20 0011-2233-4455 20 D-0 GE1/0/1\n",
    )
    mac = parse_device_output(
        "huawei",
        "display mac-address",
        "0011-2233-4455 10/-/- GE1/0/1 dynamic\n",
    )
    interface = parse_device_output(
        "huawei", "display interface", HUAWEI_INTERFACE_OUTPUT
    )

    assert arp[0]["mac_address"] == "0011-2233-4455"
    assert mac[0]["interface"] == "GE1/0/1"
    assert interface[0]["link_status"] == "UP"
    assert interface[0]["vlan_id"] == "10"
    assert get_lookup_command("huawei", "arp", "192.168.10.20") == (
        "display arp all", "display arp all"
    )
    assert get_lookup_command("huawei", "mac", "0011-2233-4455") == (
        "display mac-address", "display mac-address"
    )


def test_real_device_health_formats_use_conservative_fallback_parsers():
    power = parse_comware_output(
        "display power", COMWARE_S6850_POWER_OUTPUT
    )
    manuinfo = parse_comware_output(
        "display device manuinfo", COMWARE_S6850_MANUINFO_OUTPUT
    )
    huawei_cpu = parse_device_output(
        "huawei", "display cpu-usage", HUAWEI_CPU_OUTPUT
    )
    huawei_memory = parse_device_output(
        "huawei", "display memory-usage", HUAWEI_MEMORY_OUTPUT
    )
    temperatures = parse_device_output(
        "huawei", "display temperature all", HUAWEI_S5720_TEMPERATURE_OUTPUT
    )
    fans = parse_device_output(
        "huawei", "display fan", HUAWEI_S5720_FAN_OUTPUT
    )
    powers = parse_device_output(
        "huawei", "display power", HUAWEI_S5720_POWER_OUTPUT
    )
    interfaces = parse_device_output(
        "huawei", "display interface brief", HUAWEI_INTERFACE_BRIEF_OUTPUT
    )
    hardware = parse_device_output(
        "huawei", "display device", HUAWEI_S5720_DEVICE_OUTPUT
    )

    assert [row["status"] for row in power] == ["Normal", "Normal"]
    assert len(manuinfo) == 2
    assert huawei_cpu[0]["five_sec"] == "28"
    assert huawei_memory[0]["used_percent"] == "25"
    assert temperatures[0]["temperature"] == "44"
    assert fans[0]["status"] == "Normal"
    assert powers[0]["state"] == "Supply"
    assert len(interfaces) == 2
    assert interfaces[0]["link"] == "up"
    assert len(hardware) == 2
    assert hardware[0]["alarm_status"] == "Normal"

    summary, usable = summarize_health(
        {"display temperature all": HUAWEI_S5720_TEMPERATURE_OUTPUT},
        brand="huawei",
    )
    assert usable is True
    assert "最高温度：44 °C" in summary


def test_health_summary_uses_structured_open_source_parsers():
    summary, usable = summarize_health({
        "display cpu-usage summary": CPU_OUTPUT,
        "display memory": MEMORY_OUTPUT,
        "display environment": ENVIRONMENT_OUTPUT,
        "display fan": FAN_OUTPUT,
        "display power": POWER_OUTPUT,
        "display interface brief": INTERFACE_BRIEF_OUTPUT,
        "display device manuinfo": "",
    })

    assert usable is True
    assert "CPU 峰值：18%" in summary
    assert "内存最高使用率：40.0%" in summary
    assert "最高温度：45 °C" in summary
    assert "UP 1 个" in summary


def test_huawei_health_and_interface_summaries_are_structured():
    summary, usable = summarize_health({
        "display cpu-usage": HUAWEI_CPU_OUTPUT,
        "display memory-usage": HUAWEI_MEMORY_OUTPUT,
        "display temperature all": HUAWEI_TEMPERATURE_OUTPUT,
        "display fan": "0 1 Present Normal 55% Auto Side-to-Back\n",
        "display power": "0 PWR1 Present AC Supply 600.00\n",
        "display interface brief": HUAWEI_INTERFACE_BRIEF_OUTPUT,
        "display device": "",
    }, brand="huawei")
    interface_summary, interface_usable = summarize_interface(
        "GigabitEthernet1/0/1",
        HUAWEI_INTERFACE_OUTPUT,
        brand="huawei",
    )

    assert usable is True
    assert "CPU 使用率：28%" in summary
    assert "内存使用率：25%" in summary
    assert "最高温度：45 °C" in summary
    assert "风扇：1 项，异常 0 项" in summary
    assert "电源：1 项，异常 0 项" in summary
    assert "UP 1 个" in summary
    assert interface_usable is True
    assert "物理状态：UP" in interface_summary
    assert "PVID：10" in interface_summary


def test_lookup_target_mac_normalization_and_location_summary():
    assert normalize_mac("00:11:22:33:44:55") == "0011-2233-4455"
    assert normalize_lookup_target("192.168.10.20") == (
        "ip", "192.168.10.20"
    )
    assert normalize_lookup_target("0011.2233.4455") == (
        "mac", "0011-2233-4455"
    )
    assert choose_discovered_mac([
        "0011-2233-4455",
        "00:11:22:33:44:55",
        "aabb-ccdd-eeff",
    ]) == "0011-2233-4455"

    summary = summarize_mac_locations("0011-2233-4455", {
        "SW1 [192.0.2.10]": [{
            "mac_address": "0011-2233-4455",
            "interface": "GE1/0/1",
            "vlan_id": "10",
            "state": "Learned",
        }]
    })
    assert "SW1 [192.0.2.10]" in summary
    assert "接口 GE1/0/1" in summary


def test_interface_validation_blocks_command_injection_and_summarizes():
    assert validate_interface_name(
        "GigabitEthernet1/0/1"
    ) == "GigabitEthernet1/0/1"
    assert validate_interface_name(
        "Bridge-Aggregation1"
    ) == "Bridge-Aggregation1"
    with pytest.raises(ValueError):
        validate_interface_name("GE1/0/1 ; reboot")

    summary, usable = summarize_interface(
        "GigabitEthernet1/0/1",
        INTERFACE_OUTPUT,
        "Transceiver diagnostic information",
        "No alarm information",
    )
    assert usable is True
    assert "物理状态：UP" in summary
    assert "链路类型：Access" in summary


def test_health_worker_uses_existing_ssh_layer_and_returns_structured_result(
    monkeypatch,
):
    outputs = {
        "display cpu-usage summary": CPU_OUTPUT,
        "display memory": MEMORY_OUTPUT,
        "display environment": ENVIRONMENT_OUTPUT,
        "display fan": FAN_OUTPUT,
        "display power": POWER_OUTPUT,
        "display interface brief": INTERFACE_BRIEF_OUTPUT,
        "display device manuinfo": "",
    }

    class FakeConnection:
        def __init__(self, device, _logger):
            self.device_info = device
            self.brand_detected = "h3c"
            self.model_detected = "S5560X"
            self.error_message = ""
            self.task_success = True
            self.command_results = []
            self.disconnected = False

        @staticmethod
        def connect():
            return True

        def execute_command(self, command, sleep_time=0.3):
            self.command_results.append({
                "command": command,
                "output": outputs[command],
                "timestamp": "2026-07-29T10:00:00",
                "duration_seconds": sleep_time,
            })
            return outputs[command]

        @staticmethod
        def mark_finished():
            return None

        def get_connection_info(self):
            return {
                "device_info": self.device_info.to_dict(include_secrets=False),
                "task_success": self.task_success,
                "brand_detected": self.brand_detected,
                "model_detected": self.model_detected,
                "error_message": self.error_message,
                "command_results": list(self.command_results),
                "duration_seconds": 1.0,
            }

        def disconnect(self):
            self.disconnected = True

    monkeypatch.setattr(
        device_diagnostics_worker, "SSHConnection", FakeConnection
    )
    device = DeviceInfo(
        "h3c", "192.0.2.10", 22, "admin", "secret", "SW1"
    )
    worker = DeviceDiagnosticsWorker("health_check", [device])

    result = worker._health_device(device)

    assert result["task_success"] is True
    assert result["command_results"][0]["command"] == "诊断摘要"
    assert "CPU 峰值：18%" in result["command_results"][0]["output"]


def test_terminal_locator_follows_ip_to_arp_to_mac_workflow(monkeypatch):
    class FakeConnection:
        def __init__(self, device, _logger):
            self.device_info = device
            self.brand_detected = "h3c"
            self.model_detected = "S5560X"
            self.error_message = ""
            self.task_success = True
            self.command_results = []

        @staticmethod
        def connect():
            return True

        def execute_command(self, command, sleep_time=0.3):
            if command.startswith("display arp"):
                output = (
                    "192.168.10.20 0011-2233-4455 10 "
                    "GE1/0/1 20 D\n"
                )
            elif self.device_info.name == "SW1":
                output = "0011-2233-4455 10 Learned GE1/0/1 Y\n"
            else:
                output = "MAC ADDR table is empty\n"
            self.command_results.append({
                "command": command,
                "output": output,
                "timestamp": "2026-07-29T10:00:00",
                "duration_seconds": sleep_time,
            })
            return output

        @staticmethod
        def mark_finished():
            return None

        def get_connection_info(self):
            return {
                "device_info": self.device_info.to_dict(include_secrets=False),
                "task_success": self.task_success,
                "brand_detected": self.brand_detected,
                "model_detected": self.model_detected,
                "error_message": self.error_message,
                "command_results": list(self.command_results),
                "duration_seconds": 1.0,
            }

        @staticmethod
        def disconnect():
            return None

    monkeypatch.setattr(
        device_diagnostics_worker, "SSHConnection", FakeConnection
    )
    devices = [
        DeviceInfo("h3c", "192.0.2.10", 22, "admin", "secret", "SW1"),
        DeviceInfo("h3c", "192.0.2.20", 22, "admin", "secret", "SW2"),
    ]
    worker = DeviceDiagnosticsWorker(
        "terminal_locate",
        devices,
        options={"target_type": "ip", "target": "192.168.10.20"},
    )

    results = worker._locate_terminal()

    assert len(results) == 2
    sw1 = next(
        item for item in results if item["device_info"]["name"] == "SW1"
    )
    assert sw1["task_success"] is True
    assert "接口 GE1/0/1" in sw1["command_results"][0]["output"]


def test_huawei_worker_uses_vrp_commands_and_filters_target(monkeypatch):
    outputs = {
        "display cpu-usage": HUAWEI_CPU_OUTPUT,
        "display memory-usage": HUAWEI_MEMORY_OUTPUT,
        "display temperature all": HUAWEI_TEMPERATURE_OUTPUT,
        "display fan": "0 1 Present Normal 55% Auto Side-to-Back\n",
        "display power": "0 PWR1 Present AC Supply 600.00\n",
        "display interface brief": HUAWEI_INTERFACE_BRIEF_OUTPUT,
        "display device": "",
    }

    class FakeHuaweiConnection:
        def __init__(self, device, _logger):
            self.device_info = device
            self.brand_detected = "huawei"
            self.model_detected = "S5720-28X-SI-AC"
            self.error_message = ""
            self.task_success = True
            self.command_results = []

        @staticmethod
        def connect():
            return True

        def execute_command(self, command, sleep_time=0.3):
            output = outputs[command]
            self.command_results.append({
                "command": command,
                "output": output,
                "timestamp": "2026-07-30T10:00:00",
                "duration_seconds": sleep_time,
            })
            return output

        @staticmethod
        def mark_finished():
            return None

        def get_connection_info(self):
            return {
                "device_info": self.device_info.to_dict(include_secrets=False),
                "task_success": self.task_success,
                "brand_detected": self.brand_detected,
                "model_detected": self.model_detected,
                "error_message": self.error_message,
                "command_results": list(self.command_results),
                "duration_seconds": 1.0,
            }

        @staticmethod
        def disconnect():
            return None

    monkeypatch.setattr(
        device_diagnostics_worker, "SSHConnection", FakeHuaweiConnection
    )
    device = DeviceInfo(
        "huawei", "192.0.2.12", 22, "admin", "secret", "HW1"
    )
    result = DeviceDiagnosticsWorker(
        "health_check", [device]
    )._health_device(device)

    commands = [
        item["command"] for item in result["command_results"][1:]
    ]
    assert result["task_success"] is True
    assert commands == list(get_health_commands("huawei"))
    assert "Huawei VRP 一键巡检摘要" in result["command_results"][0]["output"]
