"""Coordinate SSH manager and batch connection worker lifecycle."""

from PyQt5.QtCore import QObject, pyqtSignal

from core.ssh_manager_simple import SSHManager
from services.batch_execution import configure_ssh_manager
from ui.connection_worker import ConnectionWorker


class BatchExecutionController(QObject):
    progress = pyqtSignal(str)
    device_status = pyqtSignal(str, str, bool, str, str)
    result = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(
        self,
        logger=None,
        manager_factory=None,
        worker_factory=ConnectionWorker,
        parent=None,
    ):
        super().__init__(parent)
        self.logger = logger
        self.manager_factory = manager_factory or (
            lambda: SSHManager(max_connections=5)
        )
        self.worker_factory = worker_factory
        self.manager = self.manager_factory()
        self.worker = None

    def is_running(self) -> bool:
        return bool(self.worker and self.worker.isRunning())

    def prepare(self, settings):
        self.manager = self.manager_factory()
        configure_ssh_manager(self.manager, settings)
        return self.manager

    def start(
        self,
        devices,
        save_after_exec: bool = False,
        detect_l2_uplink: bool = False,
    ):
        self.manager.save_after_exec = bool(save_after_exec)
        self.manager.detect_l2_uplink = bool(detect_l2_uplink)
        self.worker = self.worker_factory(self.manager, list(devices))
        self.worker.set_logger(self.logger)
        self.worker.progress_signal.connect(self.progress.emit)
        self.worker.device_status_signal.connect(self.device_status.emit)
        self.worker.result_signal.connect(self.result.emit)
        self.worker.finished_signal.connect(self.finished.emit)
        self.worker.start()
        return self.worker

    def stop(self) -> None:
        if self.manager:
            self.manager.stop_connections()

    def results(self):
        return self.manager.get_results() if self.manager else []

    def clear_sensitive_commands(self) -> None:
        if not self.manager:
            return
        self.manager.command_lines = None
        self.manager.sensitive_values = []
