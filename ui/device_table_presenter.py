"""Presentation logic for the shared device table."""

from typing import List

from PyQt5.QtWidgets import QComboBox, QLineEdit, QTableWidget, QTableWidgetItem

from ui.status_badge import StatusBadge


class DeviceTablePresenter:
    def __init__(
        self,
        table: QTableWidget,
        search_input: QLineEdit,
        group_filter: QComboBox,
    ):
        self.table = table
        self.search_input = search_input
        self.group_filter = group_filter

    def refresh(self, devices: List, status_font_px: int = 14) -> None:
        self.table.setRowCount(len(devices))
        for row, device in enumerate(devices):
            display_ip = device.get_display_address()
            ip_version = device.ip_version.value if device.ip_version else 0
            version_text = (
                "IPv6" if ip_version == 6
                else "IPv4" if ip_version == 4
                else "未知"
            )
            values = (
                device.name,
                device.group,
                device.tags,
                device.brand,
                "",
                display_ip,
                version_text,
                str(device.port),
                device.username,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            self.table.setCellWidget(
                row,
                9,
                StatusBadge("待连接", font_px=status_font_px),
            )

    def refresh_group_filter(self, devices: List) -> None:
        current = self.group_filter.currentData()
        groups = sorted({device.group for device in devices if device.group})
        self.group_filter.blockSignals(True)
        self.group_filter.clear()
        self.group_filter.addItem("全部分组", "")
        for group in groups:
            self.group_filter.addItem(group, group)
        index = self.group_filter.findData(current)
        self.group_filter.setCurrentIndex(max(0, index))
        self.group_filter.blockSignals(False)

    def apply_filters(self, devices: List) -> None:
        query = self.search_input.text().strip().lower()
        group = self.group_filter.currentData() or ""
        for row, device in enumerate(devices):
            haystack = " ".join(
                [
                    device.name,
                    device.ip,
                    device.brand,
                    device.group,
                    device.tags,
                    device.username,
                ]
            ).lower()
            visible = (not query or query in haystack) and (
                not group or device.group == group
            )
            self.table.setRowHidden(row, not visible)

    def devices_for_scope(self, devices: List, scope: str) -> List:
        if scope == "filtered":
            return [
                device
                for row, device in enumerate(devices)
                if not self.table.isRowHidden(row)
            ]
        if scope == "selected":
            rows = sorted({index.row() for index in self.table.selectedIndexes()})
            return [devices[row] for row in rows if 0 <= row < len(devices)]
        return list(devices)
