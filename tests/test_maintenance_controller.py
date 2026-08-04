import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QObject, pyqtSignal

from controllers.maintenance_controller import MaintenanceController


class FakeWorker(QObject):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(object, object, object, object)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        self.started = False
        self.running = False

    def start(self):
        self.started = True
        self.running = True

    def isRunning(self):
        return self.running


class FakePingWorker(QObject):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int, int)

    def __init__(self, ips):
        super().__init__()
        self.ips = ips
        self.started = False
        self.running = False

    def start(self):
        self.started = True
        self.running = True

    def isRunning(self):
        return self.running


class FakeMaintenanceWorker(QObject):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, int, int, int)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        self.started = False
        self.running = False

    def start(self):
        self.started = True
        self.running = True

    def isRunning(self):
        return self.running


class FakeDiagnosticsWorker(QObject):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, object)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        self.started = False
        self.running = False

    def start(self):
        self.started = True
        self.running = True

    def isRunning(self):
        return self.running


def _controller():
    return MaintenanceController(
        logger="logger",
        ping_worker_factory=FakePingWorker,
        maintenance_worker_factory=FakeMaintenanceWorker,
        diagnostics_worker_factory=FakeDiagnosticsWorker,
    )


def test_controller_preserves_task_blocking_precedence():
    controller = _controller()
    controller.ping_worker = FakePingWorker([])
    controller.ping_worker.running = True
    assert controller.blocking_reason("ping") == "批量 Ping 正在执行，请等待当前任务完成"
    assert controller.blocking_reason("maintenance") == "批量 Ping 正在执行，请等待当前任务完成"
    assert controller.blocking_reason("diagnostics") == "批量 Ping 正在执行，请等待当前任务完成"

    controller.maintenance_worker = FakeMaintenanceWorker()
    controller.maintenance_worker.running = True
    assert controller.blocking_reason("ping") == "批量 Ping 正在执行，请等待当前任务完成"
    assert controller.blocking_reason("maintenance") == "另一项批量运维任务正在执行，请等待当前任务完成"
    assert controller.blocking_reason("diagnostics") == "另一项批量运维任务正在执行，请等待当前任务完成"

    controller.diagnostics_worker = FakeDiagnosticsWorker()
    controller.diagnostics_worker.running = True
    assert controller.blocking_reason("diagnostics") == "另一项设备诊断正在执行，请等待当前任务完成"


def test_controller_starts_workers_and_forwards_signals():
    controller = _controller()
    events = []
    controller.ping_progress.connect(lambda text: events.append(("ping", text)))
    controller.ping_finished.connect(
        lambda total, success, failure: events.append(
            ("ping_done", total, success, failure)
        )
    )
    controller.maintenance_progress.connect(
        lambda text: events.append(("maintenance", text))
    )
    controller.diagnostics_progress.connect(
        lambda text: events.append(("diagnostics", text))
    )

    ping = controller.start_ping(["192.0.2.1"])
    maintenance = controller.start_maintenance(
        "port", ["device"], {"ports": [22]}
    )
    diagnostics = controller.start_diagnostics(
        "health_check", ["device"], {"profile": "standard"}
    )

    assert ping.started and ping.ips == ["192.0.2.1"]
    assert maintenance.started
    assert maintenance.args == ("port", ["device"])
    assert maintenance.kwargs == {"options": {"ports": [22]}, "logger": "logger"}
    assert diagnostics.started
    assert diagnostics.args == ("health_check", ["device"])

    ping.progress_signal.emit("ping progress")
    ping.finished_signal.emit(1, 1, 0)
    maintenance.progress_signal.emit("maintenance progress")
    diagnostics.progress_signal.emit("diagnostics progress")
    assert events == [
        ("ping", "ping progress"),
        ("ping_done", 1, 1, 0),
        ("maintenance", "maintenance progress"),
        ("diagnostics", "diagnostics progress"),
    ]
