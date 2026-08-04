"""Coordinate managed devices and shared temporary task targets."""

from services.device_management import (
    add_device_from_form,
    clear_all_devices,
    import_device_excel,
    remove_devices_at_rows,
)
from services.task_targets import (
    describe_task_targets,
    sync_temporary_task_devices,
    task_devices_for_mode,
    valid_custom_task_targets,
)


class DeviceInventoryController:
    def __init__(self, manager):
        self.manager = manager

    def add_from_form(self, values):
        return add_device_from_form(self.manager, values)

    def import_excel(self, file_path: str, master_password: str = ""):
        return import_device_excel(
            self.manager,
            file_path,
            master_password=master_password,
        )

    def remove_rows(self, rows) -> int:
        return remove_devices_at_rows(self.manager, rows)

    def clear(self) -> int:
        return clear_all_devices(self.manager)

    def sync_temporary_targets(self, selected_devices, removed_devices=None):
        return sync_temporary_task_devices(
            self.manager,
            selected_devices,
            removed_devices,
        )

    def valid_custom_targets(self, targets):
        return valid_custom_task_targets(self.manager, targets)

    @staticmethod
    def task_devices(devices, mode: str = ""):
        return task_devices_for_mode(devices, mode)

    @staticmethod
    def describe_targets(scope: str, devices) -> str:
        return describe_task_targets(scope, devices)
