from ui.ping_worker import PingWorker


def test_ping_worker_preserves_target_list_and_platform_mode():
    targets = ["192.0.2.1", "2001:db8::1"]
    worker = PingWorker(targets)

    assert worker.ips == targets
    assert isinstance(worker._is_windows, bool)
