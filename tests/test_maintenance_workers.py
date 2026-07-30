import hashlib
import json

from config.device_config import DeviceInfo
from ui import main_window


def make_device(brand="h3c"):
    return DeviceInfo(brand, "192.0.2.10", 22, "admin", "secret", "SW1")


def test_ssh_login_check_authenticates_without_opening_shell(monkeypatch):
    calls = {}

    class FakeTransport:
        @staticmethod
        def is_active():
            return True

    class FakeClient:
        def load_system_host_keys(self):
            calls["system_host_keys"] = True

        def load_host_keys(self, path):
            calls["loaded_host_keys"] = path

        def set_missing_host_key_policy(self, _policy):
            calls["policy"] = True

        def connect(self, **kwargs):
            calls["connect"] = kwargs

        @staticmethod
        def get_transport():
            return FakeTransport()

        def close(self):
            calls["closed"] = True

        def save_host_keys(self, path):
            calls["saved_host_keys"] = path

    monkeypatch.setattr(main_window.paramiko, "SSHClient", FakeClient)
    worker = main_window.MaintenanceWorker("ssh_login", [make_device()])

    ok, message = worker._test_ssh_login(make_device())

    assert ok is True
    assert "未执行设备命令" in message
    assert calls["connect"]["allow_agent"] is False
    assert calls["connect"]["look_for_keys"] is False
    assert calls["system_host_keys"] is True
    assert calls["saved_host_keys"].endswith("known_hosts")
    assert calls["closed"] is True


def test_config_backup_uses_read_only_brand_command(monkeypatch, tmp_path):
    calls = {}

    class FakeConnection:
        def __init__(self, _device, _logger):
            self.brand_detected = "cisco"
            self.error_message = ""

        @staticmethod
        def connect():
            return True

        @staticmethod
        def execute_command(command, sleep_time=0.3):
            calls["command"] = command
            calls["sleep_time"] = sleep_time
            return (
                "\x1b[32mSW1#show running-config\x1b[0m\r\n"
                "hostname SW1\r\n"
                "---- More ----\r\n"
                "interface GigabitEthernet1/0/1\r\n"
                "SW1#"
            )

        @staticmethod
        def disconnect():
            calls["disconnected"] = True

    monkeypatch.setattr(main_window, "SSHConnection", FakeConnection)
    worker = main_window.MaintenanceWorker(
        "backup",
        [make_device("cisco")],
        options={"output_dir": str(tmp_path)},
    )

    ok, message = worker._backup_config(make_device("cisco"))

    assert ok is True
    assert calls["command"] == "show running-config"
    assert calls["disconnected"] is True
    backup_files = list((tmp_path / "SW1").glob("SW1_*.cfg"))
    assert len(backup_files) == 1
    content = backup_files[0].read_text(encoding="utf-8")
    assert content == (
        "hostname SW1\n"
        "interface GigabitEthernet1/0/1\n"
    )
    metadata_files = list((tmp_path / "SW1").glob("SW1_*.json"))
    assert len(metadata_files) == 1
    metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
    assert metadata["schema"] == "aomt.config-backup.v1"
    assert metadata["device"] == {
        "name": "SW1",
        "ip": "192.0.2.10",
        "port": 22,
    }
    assert metadata["backup"]["brand"] == "cisco"
    assert metadata["backup"]["query_command"] == "show running-config"
    assert metadata["backup"]["config_file"] == backup_files[0].name
    assert metadata["backup"]["sha256"] == hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()
    assert "username" not in metadata["device"]
    assert "password" not in metadata["device"]
    assert str(backup_files[0]) in message
    assert str(metadata_files[0]) in message
