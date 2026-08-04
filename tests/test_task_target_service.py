from types import SimpleNamespace

from services.task_targets import (
    describe_task_targets,
    sync_temporary_task_devices,
    task_devices_for_mode,
    valid_custom_task_targets,
)


def _device(ip, port=22, temporary=False, ping_only=False):
    device = SimpleNamespace(ip=ip, port=port)
    device._aomt_temporary = temporary
    device._aomt_ping_only = ping_only
    return device


class _Manager:
    def __init__(self, devices=()):
        self.devices = list(devices)

    def get_devices(self):
        return self.devices

    @staticmethod
    def _device_key(ip, port):
        return str(ip).lower(), int(port)

    def add_device(self, device):
        key = self._device_key(device.ip, device.port)
        if any(self._device_key(item.ip, item.port) == key for item in self.devices):
            return False
        self.devices.append(device)
        return True

    def remove_device(self, index):
        self.devices.pop(index)


def test_sync_temporary_targets_adds_and_removes_main_list_devices():
    original = _device("192.0.2.1")
    temporary = _device("192.0.2.2", temporary=True)
    manager = _Manager([original])

    selected = sync_temporary_task_devices(manager, [temporary], [original])

    assert selected == [temporary]
    assert manager.devices == [temporary]


def test_ping_only_targets_stay_custom_but_not_enter_device_library():
    ping_only = _device("192.0.2.0/24", ping_only=True)
    manager = _Manager()

    selected = sync_temporary_task_devices(manager, [ping_only])

    assert selected == [ping_only]
    assert manager.devices == []
    assert valid_custom_task_targets(manager, selected) == [ping_only]
    assert task_devices_for_mode(selected, "ping") == [ping_only]
    assert task_devices_for_mode(selected, "backup") == []


def test_removed_library_device_is_pruned_from_custom_targets():
    device = _device("192.0.2.10")
    manager = _Manager([device])
    assert valid_custom_task_targets(manager, [device]) == [device]

    manager.devices.clear()
    assert valid_custom_task_targets(manager, [device]) == []


def test_task_target_summary_distinguishes_scope_and_ping_only_targets():
    ping_only = _device("192.0.2.0/24", ping_only=True)
    regular = _device("192.0.2.10")

    assert describe_task_targets("all", [regular]) == "全部设备：1 台"
    assert describe_task_targets("filtered", []) == "当前筛选结果：0 台"
    assert describe_task_targets("selected", [regular]) == "设备表选中行：1 台"
    assert describe_task_targets("custom", [regular, ping_only]) == (
        "自定义目标：2 个（其中 Ping 网段地址 1 个）"
    )
