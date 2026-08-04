from ui.connection_worker import ConnectionWorker


class _FakeManager:
    logger = None


def test_connection_worker_keeps_manager_devices_and_logger_contract():
    manager = _FakeManager()
    devices = [{"ip": "192.0.2.1"}]
    worker = ConnectionWorker(manager, devices)

    marker = object()
    worker.set_logger(marker)

    assert worker.ssh_manager is manager
    assert worker.device_infos == devices
    assert worker.logger is marker
    assert manager.logger is marker
