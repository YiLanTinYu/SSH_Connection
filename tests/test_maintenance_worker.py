from types import SimpleNamespace

from ui.maintenance_worker import MaintenanceWorker


def test_maintenance_worker_keeps_mode_options_and_device_label_contract():
    device = SimpleNamespace(name="SW1", ip="192.0.2.10")
    worker = MaintenanceWorker("port", [device], options={"ports": [22]})

    assert worker.mode == "port"
    assert worker.devices == [device]
    assert worker.options == {"ports": [22]}
    assert worker._device_label(device) == "SW1 [192.0.2.10]"
