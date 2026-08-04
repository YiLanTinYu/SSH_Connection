import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from config.device_config import DeviceInfo
from ui.task_history_dialog import TaskHistoryDialog
from utils.task_audit import TaskAuditStore, preview_fingerprint


def test_task_audit_records_secret_free_batch_history(tmp_path):
    store = TaskAuditStore(str(tmp_path / "history.db"))
    devices = [
        DeviceInfo(
            name="SW1",
            brand="h3c",
            ip="192.0.2.1",
            username="admin",
            password="DoNotStoreThis",
        )
    ]
    entries = [{
        "name": "SW1",
        "ip": "192.0.2.1",
        "source": "SW1.txt",
        "commands": ["display version"],
    }]
    task_id = store.start_task(
        "batch_command",
        "SW1.txt",
        preview_fingerprint(entries),
        devices,
        {"save_after_exec": False},
    )
    store.finish_task(task_id, [{
        "device_info": devices[0].to_dict(include_secrets=False),
        "task_success": True,
        "model_detected": "S6850",
        "duration_seconds": 1.25,
        "error_message": "",
    }])

    task = store.list_tasks()[0]
    detail = store.task_detail(task_id)
    assert task["status"] == "completed"
    assert task["success_count"] == 1
    assert detail["devices"][0]["model"] == "S6850"
    assert json.loads(task["options_json"]) == {"save_after_exec": False}
    database_bytes = (tmp_path / "history.db").read_bytes()
    assert b"DoNotStoreThis" not in database_bytes


def test_preview_fingerprint_is_stable_and_changes_with_commands():
    first = [{
        "name": "SW1",
        "ip": "192.0.2.1",
        "source": "SW1.txt",
        "commands": ["display version"],
    }]
    same = [dict(first[0])]
    changed = [dict(first[0], commands=["display current-configuration"])]
    assert preview_fingerprint(first) == preview_fingerprint(same)
    assert preview_fingerprint(first) != preview_fingerprint(changed)


def test_task_history_dialog_displays_persisted_records(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = TaskAuditStore(str(tmp_path / "dialog_history.db"))
    device = DeviceInfo(name="SW1", brand="h3c", ip="192.0.2.1")
    task_id = store.start_task(
        "batch_command",
        "SW1.txt",
        "abc123",
        [device],
        {"save_after_exec": False},
    )
    store.finish_task(task_id, [{
        "device_info": device.to_dict(include_secrets=False),
        "task_success": False,
        "model_detected": "",
        "duration_seconds": 2.0,
        "error_message": "连接超时",
    }])
    dialog = TaskHistoryDialog(store)
    try:
        app.processEvents()
        assert dialog.table.rowCount() == 1
        assert "SW1" in dialog.detail.toPlainText()
        assert "连接超时" in dialog.detail.toPlainText()
    finally:
        dialog.close()
