import sys
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.device_config import DeviceConfigManager, DeviceInfo
from config.device_commands import detect_brand, translate_command_for_brand


def write_excel(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    headers = list(rows[0].keys())
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    workbook.save(path)


def test_excel_import_rejects_blank_required_cells(tmp_path):
    path = tmp_path / "devices.xlsx"
    write_excel(path, [
        {"ip": None, "username": "admin", "password": "pwd", "brand": "h3c", "port": 22},
        {"ip": "192.168.1.1", "username": None, "password": "pwd", "brand": "h3c", "port": 22},
        {"ip": "192.168.1.2", "username": "admin", "password": None, "brand": "h3c", "port": 22},
        {"ip": "192.168.1.3", "username": "admin", "password": "pwd", "brand": None, "port": None},
    ])

    mgr = DeviceConfigManager()
    ok, fail, errors = mgr.import_from_excel(str(path))

    assert ok == 1
    assert fail == 3
    assert len(errors) == 3
    device = mgr.get_devices()[0]
    assert device.brand == "h3c"
    assert device.port == 22
    assert device.ip == "192.168.1.3"


def test_excel_import_validates_ip_and_port(tmp_path):
    path = tmp_path / "bad_devices.xlsx"
    write_excel(path, [
        {"ip": "999.1.1.1", "username": "admin", "password": "pwd", "brand": "h3c", "port": 22},
        {"ip": "192.168.1.1", "username": "admin", "password": "pwd", "brand": "h3c", "port": 70000},
    ])

    mgr = DeviceConfigManager()
    ok, fail, errors = mgr.import_from_excel(str(path))

    assert ok == 0
    assert fail == 2
    assert any("IP" in e for e in errors)
    assert any("port" in e for e in errors)


def test_excel_import_skips_duplicate_ip_port(tmp_path):
    path = tmp_path / "duplicate_devices.xlsx"
    write_excel(path, [
        {"ip": "192.168.1.1", "username": "admin", "password": "pwd", "brand": "h3c", "port": 22},
        {"ip": "192.168.1.1", "username": "admin2", "password": "pwd2", "brand": "huawei", "port": 22},
        {"ip": "192.168.1.1", "username": "admin3", "password": "pwd3", "brand": "h3c", "port": 2222},
    ])

    mgr = DeviceConfigManager()
    ok, fail, errors = mgr.import_from_excel(str(path))

    assert ok == 2
    assert fail == 0
    assert errors == []
    assert mgr.last_import_skipped_count == 1
    assert len(mgr.get_devices()) == 2


def test_add_device_rejects_duplicate_ip_port():
    mgr = DeviceConfigManager()

    assert mgr.add_device(DeviceInfo("h3c", "192.168.1.1", 22, "admin", "pwd"))
    assert not mgr.add_device(DeviceInfo("huawei", "192.168.1.1", 22, "admin2", "pwd2"))
    assert mgr.add_device(DeviceInfo("h3c", "192.168.1.1", 2222, "admin3", "pwd3"))
    assert len(mgr.get_devices()) == 2


def test_unknown_brand_stays_unknown_until_user_fallback():
    assert detect_brand("") == "unknown"
    assert detect_brand("% Invalid input detected") == "unknown"


def test_command_translation_covers_inventory_command():
    assert translate_command_for_brand("display device manuinfo", "cisco") == "show inventory"
    assert translate_command_for_brand("display device manuinfo", "huawei") == "display device manuinfo"


def test_default_h3c_style_commands_translate_for_supported_brands():
    cases = {
        "h3c": {
            "display version": "display version",
            "display device manuinfo": "display device manuinfo",
            "display interface brief": "display interface brief",
            "display vlan": "display vlan",
            "display cpu-usage": "display cpu-usage",
            "display memory": "display memory",
            "display arp": "display arp",
            "display ip routing-table": "display ip routing-table",
        },
        "huawei": {
            "display version": "display version",
            "display device manuinfo": "display device manuinfo",
            "display interface brief": "display interface brief",
            "display vlan": "display vlan",
            "display cpu-usage": "display cpu-usage",
            "display memory": "display memory-usage",
            "display arp": "display arp all",
            "display ip routing-table": "display ip routing-table",
        },
        "ruijie": {
            "display version": "show version",
            "display device manuinfo": "show inventory",
            "display interface brief": "show interface brief",
            "display vlan": "show vlan",
            "display cpu-usage": "show cpu",
            "display memory": "show memory",
            "display arp": "show arp",
            "display ip routing-table": "show ip route",
        },
        "cisco": {
            "display version": "show version",
            "display device manuinfo": "show inventory",
            "display interface brief": "show ip interface brief",
            "display vlan": "show vlan brief",
            "display cpu-usage": "show processes cpu",
            "display memory": "show processes memory",
            "display arp": "show arp",
            "display ip routing-table": "show ip route",
        },
        "tplink": {
            "display version": "show version",
            "display device manuinfo": "show system-info",
            "display interface brief": "show interfaces status",
            "display vlan": "show vlan",
            "display cpu-usage": "show cpu-usage",
            "display memory": "show memory-usage",
            "display arp": "show arp",
            "display ip routing-table": "show ip route",
        },
    }

    for brand, expected_by_command in cases.items():
        for command, expected in expected_by_command.items():
            assert translate_command_for_brand(command, brand) == expected
