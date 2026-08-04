from types import SimpleNamespace

from PyQt5.QtCore import QObject, pyqtSignal

from controllers.batch_execution_controller import BatchExecutionController
from services.batch_execution import BatchCommandSettings


class FakeManager:
    def __init__(self):
        self.command_file = None
        self.command_directory = None
        self.command_lines = None
        self.command_label = ""
        self.required_brand = ""
        self.sensitive_values = []
        self.save_after_exec = False
        self.detect_l2_uplink = False
        self.stopped = False
        self._results = [{"is_connected": True}]

    def stop_connections(self):
        self.stopped = True

    def get_results(self):
        return list(self._results)


class FakeWorker(QObject):
    progress_signal = pyqtSignal(str)
    device_status_signal = pyqtSignal(str, str, bool, str, str)
    result_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()

    def __init__(self, manager, devices):
        super().__init__()
        self.manager = manager
        self.devices = devices
        self.logger = None
        self.started = False
        self.running = False

    def set_logger(self, logger):
        self.logger = logger

    def start(self):
        self.started = True
        self.running = True

    def isRunning(self):
        return self.running


def _controller():
    return BatchExecutionController(
        logger="logger",
        manager_factory=FakeManager,
        worker_factory=FakeWorker,
    )


def test_batch_controller_prepares_fresh_manager_and_copies_settings():
    controller = _controller()
    original = controller.manager
    settings = BatchCommandSettings(
        command_file="commands.txt",
        command_lines=("display version",),
        command_label="巡检",
        required_brand="h3c",
        sensitive_values=("secret",),
    )

    manager = controller.prepare(settings)
    assert manager is not original
    assert manager.command_file == "commands.txt"
    assert manager.command_lines == ["display version"]
    assert manager.command_label == "巡检"
    assert manager.required_brand == "h3c"
    assert manager.sensitive_values == ["secret"]


def test_batch_controller_starts_forwards_stops_and_clears_sensitive_data():
    controller = _controller()
    events = []
    controller.progress.connect(lambda text: events.append(("progress", text)))
    controller.device_status.connect(
        lambda *args: events.append(("status",) + args)
    )
    controller.result.connect(lambda result: events.append(("result", result)))
    controller.finished.connect(lambda: events.append(("finished",)))
    device = SimpleNamespace(ip="192.0.2.1")

    worker = controller.start(
        [device],
        save_after_exec=True,
        detect_l2_uplink=True,
    )
    assert worker.started and worker.logger == "logger"
    assert worker.devices == [device]
    assert controller.is_running()
    assert controller.manager.save_after_exec is True
    assert controller.manager.detect_l2_uplink is True

    worker.progress_signal.emit("connecting")
    worker.device_status_signal.emit("192.0.2.1", "成功", True, "h3c", "S6850")
    worker.result_signal.emit({"is_connected": True})
    worker.finished_signal.emit()
    assert events == [
        ("progress", "connecting"),
        ("status", "192.0.2.1", "成功", True, "h3c", "S6850"),
        ("result", {"is_connected": True}),
        ("finished",),
    ]

    controller.stop()
    assert controller.manager.stopped is True
    assert controller.results() == [{"is_connected": True}]
    controller.manager.command_lines = ["secret command"]
    controller.manager.sensitive_values = ["secret"]
    controller.clear_sensitive_commands()
    assert controller.manager.command_lines is None
    assert controller.manager.sensitive_values == []
