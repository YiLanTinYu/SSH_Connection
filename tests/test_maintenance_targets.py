import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from config.device_config import DeviceConfigManager, DeviceInfo
from ui.maintenance_target_dialog import (
    MaintenanceTargetDialog,
    expand_ping_networks,
    parse_manual_targets,
)
from ui.main_window import MainWindow, PingWorker


def test_parse_manual_targets_supports_ipv4_ipv6_hostname_and_deduplication():
    targets = parse_manual_targets(
        "192.168.10.10, [2026:1000:120::23]:2222\n"
        "switch.example.com:2200 192.168.10.10",
        allow_port=True,
        default_port=22,
    )

    assert targets == [
        ("192.168.10.10", 22),
        ("2026:1000:120::23", 2222),
        ("switch.example.com", 2200),
    ]
    with pytest.raises(ValueError, match="主机名无效"):
        parse_manual_targets("bad/host")


def test_expand_ping_networks_uses_hosts_and_deduplicates_overlaps():
    targets = expand_ping_networks(
        "192.168.10.0/30, 192.168.10.1/32\n2026:1000:120::/126"
    )

    assert targets == [
        "192.168.10.1",
        "192.168.10.2",
        "2026:1000:120::1",
        "2026:1000:120::2",
        "2026:1000:120::3",
    ]


def test_expand_ping_networks_rejects_missing_prefix_and_oversized_network():
    with pytest.raises(ValueError, match="必须包含前缀长度"):
        expand_ping_networks("192.168.10.1")
    with pytest.raises(ValueError, match="超过单次上限"):
        expand_ping_networks("10.0.0.0/8")


def test_ping_dialog_merges_imported_manual_and_network_targets():
    app = QApplication.instance() or QApplication([])
    imported = SimpleNamespace(
        name="SW10",
        ip="192.168.10.1",
        port=22,
        username="",
        password="",
    )
    dialog = MaintenanceTargetDialog("ping", [imported])
    try:
        dialog.manual_input.setPlainText("192.168.10.2")
        dialog.network_input.setPlainText("192.168.10.0/29")

        devices = dialog.selected_devices()

        assert [device.ip for device in devices] == [
            "192.168.10.1",
            "192.168.10.2",
            "192.168.10.3",
            "192.168.10.4",
            "192.168.10.5",
            "192.168.10.6",
        ]
        app.processEvents()
    finally:
        dialog.close()


def test_shared_target_dialog_marks_temporary_and_ping_only_targets():
    app = QApplication.instance() or QApplication([])
    dialog = MaintenanceTargetDialog("shared_targets", [])
    try:
        dialog.manual_input.setPlainText("192.0.2.10")
        dialog.network_input.setPlainText("192.0.2.0/30")

        devices = dialog.selected_devices()

        assert [device.ip for device in devices] == [
            "192.0.2.10",
            "192.0.2.1",
            "192.0.2.2",
        ]
        assert all(
            getattr(device, "_aomt_temporary", False)
            for device in devices
        )
        assert not getattr(devices[0], "_aomt_ping_only", False)
        assert all(
            getattr(device, "_aomt_ping_only", False)
            for device in devices[1:]
        )
        app.processEvents()
    finally:
        dialog.close()


def test_shared_target_dialog_requires_complete_optional_credentials():
    app = QApplication.instance() or QApplication([])
    dialog = MaintenanceTargetDialog("shared_targets", [])
    try:
        dialog.manual_input.setPlainText("192.0.2.10")
        dialog.username_input.setText("operator")

        with pytest.raises(ValueError, match="必须同时填写"):
            dialog.selected_devices()
    finally:
        dialog.close()


def test_shared_target_dialog_can_remove_selected_temporary_target(
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    temporary = DeviceInfo(
        brand="",
        ip="192.0.2.10",
        port=22,
        username="operator",
        password="secret",
        name="192.0.2.10",
    )
    temporary._aomt_temporary = True
    dialog = MaintenanceTargetDialog("shared_targets", [temporary])
    try:
        dialog.device_list.item(0).setSelected(True)
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.Yes,
        )

        dialog.remove_selected_temporary_targets()

        assert dialog.device_list.count() == 0
        assert dialog.removed_temporary_targets() == [temporary]
        dialog._validate_and_accept()
        assert dialog.result() == dialog.Accepted
        app.processEvents()
    finally:
        dialog.close()


def test_temporary_targets_sync_with_main_device_manager():
    manager = DeviceConfigManager()
    owner = SimpleNamespace(
        device_manager=manager,
        _custom_task_targets=[],
    )
    temporary = DeviceInfo(
        brand="",
        ip="192.0.2.20",
        port=2222,
        username="operator",
        password="secret",
        name="192.0.2.20",
    )
    temporary._aomt_temporary = True

    synchronized = MainWindow._sync_temporary_task_devices(
        owner,
        [temporary],
    )
    owner._custom_task_targets = synchronized

    assert manager.get_devices() == [temporary]
    assert MainWindow._valid_custom_task_targets(owner) == [temporary]

    manager.remove_device(0)

    assert MainWindow._valid_custom_task_targets(owner) == []

    manager.add_device(temporary)
    synchronized = MainWindow._sync_temporary_task_devices(
        owner,
        [],
        [temporary],
    )

    assert synchronized == []
    assert manager.get_devices() == []


def test_ping_worker_reports_concurrent_results(monkeypatch):
    app = QApplication.instance() or QApplication([])
    worker = PingWorker(["192.0.2.1", "192.0.2.2", "192.0.2.3"])
    monkeypatch.setattr(
        worker,
        "_ping",
        lambda host: (
            (True, "") if host != "192.0.2.2" else (False, "请求超时")
        ),
    )
    progress = []
    finished = []
    worker.progress_signal.connect(progress.append)
    worker.finished_signal.connect(
        lambda total, success, failure: finished.append(
            (total, success, failure)
        )
    )

    worker.run()
    app.processEvents()

    assert len(progress) == 3
    assert finished == [(3, 2, 1)]
    assert any("192.0.2.2 不可达" in line for line in progress)


def test_target_dialog_combines_checked_devices_and_manual_ssh_targets():
    app = QApplication.instance() or QApplication([])
    imported = SimpleNamespace(
        name="SW10",
        ip="192.168.10.10",
        port=22,
        username="excel-admin",
        password="excel-secret",
    )
    dialog = MaintenanceTargetDialog("ssh_login", [imported])
    try:
        assert dialog.device_list.item(0).checkState() == Qt.Checked
        dialog.manual_input.setPlainText(
            "192.168.10.10\n[2026:1000:120::23]:2222"
        )
        dialog.username_input.setText("manual-admin")
        dialog.password_input.setText("manual-secret")

        devices = dialog.selected_devices()

        assert len(devices) == 2
        assert devices[0] is imported
        assert devices[1].ip == "2026:1000:120::23"
        assert devices[1].port == 2222
        assert devices[1].username == "manual-admin"
        assert devices[1].password == "manual-secret"
        app.processEvents()
    finally:
        dialog.close()


def test_diagnostic_target_dialog_accepts_manual_ssh_credentials():
    app = QApplication.instance() or QApplication([])
    dialog = MaintenanceTargetDialog("health_check", [])
    try:
        assert dialog.credentials_widget.isVisible() is False
        dialog.show()
        app.processEvents()
        assert dialog.credentials_widget.isVisible() is True
        dialog.manual_input.setPlainText("192.0.2.20:2222")
        dialog.username_input.setText("operator")
        dialog.password_input.setText("secret")

        devices = dialog.selected_devices()

        assert len(devices) == 1
        assert devices[0].ip == "192.0.2.20"
        assert devices[0].port == 2222
        assert devices[0].username == "operator"
    finally:
        dialog.close()
