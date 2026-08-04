"""Coordinate maintenance worker lifecycle and mutual exclusion."""

from PyQt5.QtCore import QObject, pyqtSignal

from ui.device_diagnostics_worker import DeviceDiagnosticsWorker
from ui.maintenance_worker import MaintenanceWorker
from ui.ping_worker import PingWorker


class MaintenanceController(QObject):
    ping_progress = pyqtSignal(str)
    ping_finished = pyqtSignal(int, int, int)
    maintenance_progress = pyqtSignal(str)
    maintenance_finished = pyqtSignal(str, int, int, int)
    diagnostics_progress = pyqtSignal(str)
    diagnostics_finished = pyqtSignal(str, object)

    def __init__(
        self,
        logger=None,
        ping_worker_factory=PingWorker,
        maintenance_worker_factory=MaintenanceWorker,
        diagnostics_worker_factory=DeviceDiagnosticsWorker,
        parent=None,
    ):
        super().__init__(parent)
        self.logger = logger
        self.ping_worker_factory = ping_worker_factory
        self.maintenance_worker_factory = maintenance_worker_factory
        self.diagnostics_worker_factory = diagnostics_worker_factory
        self.ping_worker = None
        self.maintenance_worker = None
        self.diagnostics_worker = None

    @staticmethod
    def _is_running(worker) -> bool:
        return bool(worker and worker.isRunning())

    def blocking_reason(self, task_kind: str) -> str:
        if task_kind == "ping":
            if self._is_running(self.ping_worker):
                return "批量 Ping 正在执行，请等待当前任务完成"
            if self._is_running(self.maintenance_worker):
                return "另一项批量运维任务正在执行，请等待当前任务完成"
            return ""

        if task_kind == "maintenance":
            if self._is_running(self.maintenance_worker):
                return "另一项批量运维任务正在执行，请等待当前任务完成"
            if self._is_running(self.ping_worker):
                return "批量 Ping 正在执行，请等待当前任务完成"
            return ""

        if task_kind == "diagnostics":
            if self._is_running(self.diagnostics_worker):
                return "另一项设备诊断正在执行，请等待当前任务完成"
            if self._is_running(self.maintenance_worker):
                return "另一项批量运维任务正在执行，请等待当前任务完成"
            if self._is_running(self.ping_worker):
                return "批量 Ping 正在执行，请等待当前任务完成"
        return ""

    def start_ping(self, ips):
        self.ping_worker = self.ping_worker_factory(list(ips))
        self.ping_worker.progress_signal.connect(self.ping_progress.emit)
        self.ping_worker.finished_signal.connect(self.ping_finished.emit)
        self.ping_worker.start()
        return self.ping_worker

    def start_maintenance(self, mode: str, devices, options=None):
        self.maintenance_worker = self.maintenance_worker_factory(
            mode,
            list(devices),
            options=options,
            logger=self.logger,
        )
        self.maintenance_worker.progress_signal.connect(
            self.maintenance_progress.emit
        )
        self.maintenance_worker.finished_signal.connect(
            self.maintenance_finished.emit
        )
        self.maintenance_worker.start()
        return self.maintenance_worker

    def start_diagnostics(self, mode: str, devices, options=None):
        self.diagnostics_worker = self.diagnostics_worker_factory(
            mode,
            list(devices),
            options=options,
            logger=self.logger,
        )
        self.diagnostics_worker.progress_signal.connect(
            self.diagnostics_progress.emit
        )
        self.diagnostics_worker.finished_signal.connect(
            self.diagnostics_finished.emit
        )
        self.diagnostics_worker.start()
        return self.diagnostics_worker
