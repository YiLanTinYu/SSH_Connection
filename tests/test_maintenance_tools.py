import socket

import pytest

from utils.maintenance_tools import (
    calculate_subnet,
    check_tcp_port,
    normalize_device_config,
    parse_tcp_ports,
    safe_filename,
    unified_config_diff,
)


def test_parse_tcp_ports_removes_duplicates_and_validates_range():
    assert parse_tcp_ports("22, 443，22 80") == [22, 443, 80]
    with pytest.raises(ValueError):
        parse_tcp_ports("0")
    with pytest.raises(ValueError):
        parse_tcp_ports("ssh")


def test_check_tcp_port_reports_open_socket(monkeypatch):
    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(socket, "create_connection", lambda *_args, **_kwargs: FakeSocket())
    assert check_tcp_port("[2001:db8::10]", 22) == (True, "端口开放")


def test_calculate_ipv4_and_ipv6_subnets():
    ipv4 = dict(calculate_subnet("192.168.10.20/24"))
    assert ipv4["网络地址"] == "192.168.10.0"
    assert ipv4["广播地址"] == "192.168.10.255"
    assert ipv4["可用地址数"] == "254"

    ipv6 = dict(calculate_subnet("2001:db8::20/64"))
    assert ipv6["IP 版本"] == "IPv6"
    assert ipv6["网络地址"] == "2001:db8::"
    assert ipv6["完整地址"] == "2001:0db8:0000:0000:0000:0000:0000:0020"
    assert ipv6["主机位数"] == "64"
    assert ipv6["主机标识"] == "0x0000000000000020"
    assert ipv6["所在 /64"] == "2001:db8::/64"
    assert ipv6["/64 划分关系"] == "当前网络就是一个 /64 子网"
    assert ipv6["请求节点组播"] == "ff02::1:ff00:20"


def test_calculate_ipv6_prefix_longer_than_64():
    ipv6 = dict(calculate_subnet("2026::1/65"))
    assert ipv6["网络地址"] == "2026::"
    assert ipv6["主机位数"] == "63"
    assert ipv6["精确地址数"] == "2^63 = 9,223,372,036,854,775,808"
    assert ipv6["所在 /64"] == "2026::/64"
    assert "2^1 = 2" in ipv6["/64 划分关系"]


def test_unified_config_diff_and_safe_filename(tmp_path):
    first = tmp_path / "before.cfg"
    second = tmp_path / "after.cfg"
    first.write_text("sysname SW1\nvlan 10\n", encoding="utf-8")
    second.write_text("sysname SW1\nvlan 20\n", encoding="utf-8")

    diff = unified_config_diff(str(first), str(second))
    assert "-vlan 10" in diff
    assert "+vlan 20" in diff
    assert safe_filename('SW1:core/01*') == "SW1_core_01_"


def test_normalize_device_config_removes_terminal_artifacts():
    output = (
        "\x1b[32m<H3C>display current-configuration\x1b[0m\r\n"
        "#\r\n"
        "sysname H3C\r\n"
        "---- More ----\r\n"
        "interface GigabitEthernet1/0/1\r\n"
        " description uplXX\b\bink\r\n"
        "<H3C>\r\n"
    )

    normalized = normalize_device_config(
        output,
        "display current-configuration",
    )

    assert normalized == (
        "#\n"
        "sysname H3C\n"
        "interface GigabitEthernet1/0/1\n"
        " description uplink"
    )
