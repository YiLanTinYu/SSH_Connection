import os

import pytest

from config.device_config import DeviceInfo
from config.health_profiles import (
    DEFAULT_PROFILE_NAME,
    HealthProfileStore,
    normalize_custom_commands,
)
from ui import device_diagnostics_worker
from ui.device_diagnostics_worker import DeviceDiagnosticsWorker
from utils.device_diagnostics import HEALTH_CHECK_ITEM_IDS


def test_health_profile_store_round_trip_and_protects_builtin(tmp_path):
    path = tmp_path / "health_profiles.json"
    store = HealthProfileStore(HEALTH_CHECK_ITEM_IDS, str(path))
    profile = {
        "builtin_items": ["cpu", "interfaces", "unknown"],
        "custom_commands": {
            "h3c": ["display clock", "display clock"],
            "huawei": ["display current-configuration | include sysname"],
        },
    }

    store.save("轻量巡检", profile)
    loaded = store.load()["轻量巡检"]

    assert loaded["builtin_items"] == ["cpu", "interfaces"]
    assert loaded["custom_commands"]["h3c"] == ["display clock"]
    with pytest.raises(ValueError):
        store.save(DEFAULT_PROFILE_NAME, profile)
    with pytest.raises(ValueError):
        store.delete(DEFAULT_PROFILE_NAME)


def test_custom_health_commands_only_allow_single_display_queries():
    assert normalize_custom_commands([
        " display clock ",
        "display interface brief",
    ]) == ["display clock", "display interface brief"]
    with pytest.raises(ValueError):
        normalize_custom_commands(["system-view"])
    with pytest.raises(ValueError):
        normalize_custom_commands(["display clock ; reboot"])
    with pytest.raises(ValueError):
        normalize_custom_commands(["display clock\ndisplay version"])


def test_health_profile_dialog_defaults_and_window_flags(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    from ui.health_profile_dialog import HealthProfileDialog

    app = QApplication.instance() or QApplication([])
    store = HealthProfileStore(
        HEALTH_CHECK_ITEM_IDS, str(tmp_path / "profiles.json")
    )
    dialog = HealthProfileDialog(store=store)
    try:
        assert dialog.profile_combo.currentText() == DEFAULT_PROFILE_NAME
        assert all(
            checkbox.isChecked()
            for checkbox in dialog.item_checks.values()
        )
        assert dialog.windowFlags() & Qt.WindowMaximizeButtonHint
        assert not dialog.windowFlags() & Qt.WindowContextHelpButtonHint
    finally:
        dialog.close()
        app.processEvents()


def test_health_worker_executes_selected_and_brand_custom_commands(monkeypatch):
    outputs = {
        "display cpu-usage": (
            "CPU utilization for five seconds: 18%: "
            "one minute: 15%: five minutes: 12%\n"
        ),
        "display clock": "2026-07-30 10:00:00\n<HW1>",
    }

    class FakeConnection:
        def __init__(self, device, _logger):
            self.device_info = device
            self.brand_detected = "huawei"
            self.model_detected = "S5720"
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
                "duration_seconds": 0.5,
            }

        @staticmethod
        def disconnect():
            return None

    monkeypatch.setattr(
        device_diagnostics_worker, "SSHConnection", FakeConnection
    )
    device = DeviceInfo(
        "huawei", "192.0.2.12", 22, "admin", "secret", "HW1"
    )
    worker = DeviceDiagnosticsWorker(
        "health_check",
        [device],
        options={
            "profile_name": "轻量巡检",
            "builtin_items": ["cpu"],
            "custom_commands": {
                "h3c": ["display version"],
                "huawei": ["display clock"],
            },
        },
    )

    result = worker._health_device(device)
    commands = [
        item["command"] for item in result["command_results"][1:]
    ]
    summary = result["command_results"][0]["output"]

    assert commands == ["display cpu-usage", "display clock"]
    assert "巡检方案：轻量巡检" in summary
    assert "CPU 使用率：18%" in summary
    assert "内存" not in summary
    assert result["task_success"] is True
