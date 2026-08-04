"""Background worker for batch ICMP checks."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import sys
from typing import List

from PyQt5.QtCore import QThread, pyqtSignal


class PingWorker(QThread):
    """批量 Ping 工作线程，避免阻塞界面。"""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int, int)

    def __init__(self, ips: List[str]):
        super().__init__()
        self.ips = ips
        self._is_windows = sys.platform.startswith("win")

    def run(self):
        success = 0
        failure = 0
        total = len(self.ips)

        max_workers = min(32, max(1, total))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._ping, ip): ip
                for ip in self.ips
            }
            for index, future in enumerate(as_completed(futures), start=1):
                ip = futures[future]
                try:
                    ok, detail = future.result()
                except Exception as exc:
                    ok, detail = False, f"执行失败: {exc}"
                if ok:
                    success += 1
                    self.progress_signal.emit(
                        f"[Ping] ({index}/{total}) {ip} 可达，响应正常"
                    )
                else:
                    failure += 1
                    self.progress_signal.emit(
                        f"[Ping] ({index}/{total}) {ip} 不可达，{detail}"
                    )

        self.finished_signal.emit(total, success, failure)

    def _ping(self, ip: str) -> tuple:
        if self._is_windows:
            cmd = ["ping", "-n", "1", "-w", "1000", ip]
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            cmd = ["ping", "-c", "1", "-W", "1", ip]
            creationflags = 0

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=creationflags,
            )
            if result.returncode == 0:
                return True, ""
            output = (result.stdout or result.stderr or "").strip().splitlines()
            detail = output[-1] if output else "无响应或超时"
            return False, detail
        except subprocess.TimeoutExpired:
            return False, "请求超时"
        except Exception as exc:
            return False, f"执行失败: {exc}"
