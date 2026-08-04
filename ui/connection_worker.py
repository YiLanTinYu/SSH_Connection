"""Background worker for batch SSH connections."""

from PyQt5.QtCore import QThread, pyqtSignal


class ConnectionWorker(QThread):
    """连接工作线程

    修复说明：
    - 新增 device_status_signal：每台设备完成后立即 emit，实现逐设备实时刷新（建议2）
    - result_signal 保留，用于传递完整结构化结果（型号/品牌填充）
    """

    progress_signal      = pyqtSignal(str)
    finished_signal      = pyqtSignal()
    result_signal        = pyqtSignal(dict)
    # 建议2：逐设备实时状态信号 (ip, status_text, is_success, brand, model)
    device_status_signal = pyqtSignal(str, str, bool, str, str)

    def __init__(self, ssh_manager, device_infos):
        super().__init__()
        self.ssh_manager  = ssh_manager
        self.device_infos = device_infos
        self.logger       = None

    def set_logger(self, logger):
        self.logger = logger
        self.ssh_manager.logger = logger

    def run(self):
        self.ssh_manager.add_devices(self.device_infos)
        self.ssh_manager.set_progress_callback(
            lambda msg: self.progress_signal.emit(msg)
        )
        # 建议2：注册逐设备完成回调，每台完成立即通知主线程
        self.ssh_manager.set_device_done_callback(self._on_device_done)
        self.ssh_manager.start_connections()
        self.ssh_manager.wait_for_completion()
        self.finished_signal.emit()

    def _on_device_done(self, result: dict):
        """SSHManager 每台设备完成时的回调（在工作线程中执行，通过信号转发到主线程）"""
        self.result_signal.emit(result)
        device_info   = result.get("device_info", {})
        is_connected  = result.get("is_connected", False)
        error_message = result.get("error_message", "") or ""
        ip            = device_info.get("ip", "")
        brand         = result.get("brand_detected", "") or ""
        model         = result.get("model_detected", "") or ""

        if is_connected:
            status_text = f"✔ 成功  {brand}" if brand else "✔ 连接成功"
        else:
            # 截断错误信息，避免状态列过宽
            short_err = error_message[:30] + "..." if len(error_message) > 30 else error_message
            status_text = f"✘ {short_err}"

        self.device_status_signal.emit(ip, status_text, is_connected, brand, model)
