import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QComboBox, QLineEdit, QTableWidget

from ui.device_table_presenter import DeviceTablePresenter


def _device(name, ip, group="", tags=""):
    return SimpleNamespace(
        name=name,
        ip=ip,
        brand="h3c",
        group=group,
        tags=tags,
        port=22,
        username="admin",
        ip_version=SimpleNamespace(value=6 if ":" in ip else 4),
        get_display_address=lambda: f"[{ip}]" if ":" in ip else ip,
    )


def test_device_table_presenter_refreshes_filters_and_scope():
    app = QApplication.instance() or QApplication([])
    table = QTableWidget(0, 10)
    search = QLineEdit()
    groups = QComboBox()
    presenter = DeviceTablePresenter(table, search, groups)
    devices = [
        _device("SW1", "192.0.2.1", "核心"),
        _device("SW2", "2001:db8::2", "接入"),
    ]

    presenter.refresh(devices)
    presenter.refresh_group_filter(devices)
    search.setText("SW2")
    presenter.apply_filters(devices)

    assert table.rowCount() == 2
    assert table.item(0, 5).text() == "192.0.2.1"
    assert table.item(1, 5).text() == "[2001:db8::2]"
    assert table.isRowHidden(0) is True
    assert table.isRowHidden(1) is False
    assert presenter.devices_for_scope(devices, "filtered") == [devices[1]]
    assert groups.findData("核心") >= 0
    assert groups.findData("接入") >= 0
    assert app is not None
