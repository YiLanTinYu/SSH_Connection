from types import SimpleNamespace

from controllers.device_inventory_controller import DeviceInventoryController


class FakeManager:
    def __init__(self):
        self.devices = []

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

    def clear_devices(self):
        self.devices.clear()


def _device(name, ip, temporary=False, ping_only=False):
    return SimpleNamespace(
        name=name,
        ip=ip,
        port=22,
        _aomt_temporary=temporary,
        _aomt_ping_only=ping_only,
    )


def test_inventory_controller_removes_clears_and_describes_targets():
    manager = FakeManager()
    manager.devices = [_device("SW1", "192.0.2.1"), _device("SW2", "192.0.2.2")]
    controller = DeviceInventoryController(manager)

    assert controller.remove_rows([0]) == 1
    assert [device.name for device in manager.devices] == ["SW2"]
    assert controller.describe_targets("all", manager.devices) == "全部设备：1 台"
    assert controller.clear() == 1
    assert manager.devices == []


def test_inventory_controller_synchronizes_and_filters_temporary_targets():
    manager = FakeManager()
    managed = _device("SW1", "192.0.2.1")
    temporary = _device("TEMP", "192.0.2.2", temporary=True)
    ping_only = _device("PING", "192.0.2.3", temporary=True, ping_only=True)
    manager.devices.append(managed)
    controller = DeviceInventoryController(manager)

    selected = controller.sync_temporary_targets(
        [managed, temporary, ping_only]
    )
    assert selected == [managed, temporary, ping_only]
    assert manager.devices == [managed, temporary]
    assert controller.valid_custom_targets(selected) == selected
    assert controller.task_devices(selected, "ping") == selected
    assert controller.task_devices(selected, "health_check") == [managed, temporary]

    controller.sync_temporary_targets([], [temporary])
    assert manager.devices == [managed]
    assert controller.valid_custom_targets(selected) == [managed, ping_only]
