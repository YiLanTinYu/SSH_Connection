import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QDialogButtonBox

from config.device_config import DeviceInfo
from ui.execution_preview_dialog import (
    ExecutionPreviewDialog,
    build_execution_preview,
    command_risks,
    redact_command,
)


class FakeManager:
    sensitive_values = ["TopSecret123"]

    def _load_commands_for_device(self, device):
        if device.name == "SW2":
            return [], None
        return [
            "display version",
            "local-user admin password cipher TopSecret123",
            "reboot",
        ], "SW1.txt"


def test_preview_redacts_secrets_and_detects_risk():
    redacted = redact_command(
        "local-user admin password cipher TopSecret123",
        ["TopSecret123"],
    )
    assert "TopSecret123" not in redacted
    assert "********" in redacted
    risks = command_risks(["display version", "reboot"])
    assert risks == [{"level": "高", "label": "重启设备", "line": 2}]


def test_preview_builds_entries_for_matched_and_missing_scripts():
    entries = build_execution_preview([
        DeviceInfo(name="SW1", brand="h3c", ip="192.0.2.1"),
        DeviceInfo(name="SW2", brand="h3c", ip="192.0.2.2"),
    ], FakeManager())
    assert entries[0]["command_count"] == 3
    assert entries[0]["source"] == "SW1.txt"
    assert "TopSecret123" not in "\n".join(entries[0]["commands"])
    assert entries[1]["missing"] is True


def test_preview_requires_explicit_confirmation():
    app = QApplication.instance() or QApplication([])
    entries = build_execution_preview([
        DeviceInfo(name="SW1", brand="h3c", ip="192.0.2.1"),
    ], FakeManager())
    dialog = ExecutionPreviewDialog(entries)
    try:
        accept_button = dialog.buttons.button(QDialogButtonBox.Ok)
        assert not accept_button.isEnabled()
        dialog.confirm_check.setChecked(True)
        app.processEvents()
        assert accept_button.isEnabled()
        assert "TopSecret123" not in dialog.detail.toPlainText()
    finally:
        dialog.close()
