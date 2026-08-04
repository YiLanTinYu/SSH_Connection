"""Background worker for batch maintenance operations."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from typing import List

import paramiko
from PyQt5.QtCore import QThread, pyqtSignal

from config.device_commands import get_command
from config.ssh_security import (
    build_connect_kwargs,
    configure_host_key_policy,
    normalize_host_key_policy,
    persist_host_keys,
)
from core.ssh_manager_simple import SSHConnection
from utils.maintenance_tools import (
    check_tcp_port,
    normalize_device_config,
    normalize_host,
    run_traceroute,
    write_config_backup,
)


class MaintenanceWorker(QThread):
    """Run batch maintenance checks without blocking the UI thread."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, int, int, int)

    def __init__(self, mode: str, devices: List, options=None, logger=None):
        super().__init__()
        self.mode = mode
        self.devices = list(devices)
        self.options = options or {}
        self.logger = logger

    def run(self):
        if self.mode == "port":
            tasks = [
                (device, port)
                for device in self.devices
                for port in self.options.get("ports", [])
            ]
            self._run_parallel(tasks, self._check_port, max_workers=10)
        elif self.mode == "ssh_login":
            self._run_parallel(self.devices, self._test_ssh_login, max_workers=5)
        elif self.mode == "traceroute":
            self._run_parallel(self.devices, self._trace_device, max_workers=3)
        elif self.mode == "backup":
            self._run_parallel(self.devices, self._backup_config, max_workers=5)
        else:
            self.finished_signal.emit(self.mode, 0, 0, 0)

    def _run_parallel(self, tasks, handler, max_workers: int):
        total = len(tasks)
        success = 0
        failure = 0
        if not tasks:
            self.finished_signal.emit(self.mode, 0, 0, 0)
            return

        with ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
            futures = {executor.submit(handler, task): task for task in tasks}
            for index, future in enumerate(as_completed(futures), start=1):
                try:
                    ok, message = future.result()
                except Exception as exc:
                    ok, message = False, f"任务异常: {exc}"
                success += int(ok)
                failure += int(not ok)
                self.progress_signal.emit(f"({index}/{total}) {message}")

        self.finished_signal.emit(self.mode, total, success, failure)

    @staticmethod
    def _device_label(device) -> str:
        name = str(getattr(device, "name", "") or "").strip()
        ip = str(getattr(device, "ip", "") or "").strip()
        return f"{name} [{ip}]" if name else ip

    def _check_port(self, task):
        device, port = task
        ip = str(getattr(device, "ip", "") or "")
        ok, detail = check_tcp_port(ip, port)
        state = "开放" if ok else "不可用"
        return ok, f"[端口检测] {self._device_label(device)} TCP/{port} {state}，{detail}"

    def _test_ssh_login(self, device):
        client = paramiko.SSHClient()
        policy = normalize_host_key_policy(
            getattr(device, "host_key_policy", "tofu")
        )
        known_hosts_path = configure_host_key_policy(client, policy)
        try:
            kwargs = build_connect_kwargs(
                device, normalize_host(getattr(device, "ip", ""))
            )
            client.connect(**kwargs)
            persist_host_keys(client, policy, known_hosts_path)
            transport = client.get_transport()
            if not transport or not transport.is_active():
                return False, f"[SSH 登录] {self._device_label(device)} 会话未激活"
            return True, f"[SSH 登录] {self._device_label(device)} 认证成功，未执行设备命令"
        except paramiko.AuthenticationException:
            return False, f"[SSH 登录] {self._device_label(device)} 认证失败"
        except paramiko.SSHException as exc:
            return False, f"[SSH 登录] {self._device_label(device)} SSH 协议错误: {exc}"
        except OSError as exc:
            return False, f"[SSH 登录] {self._device_label(device)} 连接失败: {exc}"
        finally:
            client.close()

    def _trace_device(self, device):
        ip = str(getattr(device, "ip", "") or "")
        ok, output = run_traceroute(ip)
        state = "完成" if ok else "失败"
        return ok, f"[路由跟踪] {self._device_label(device)} {state}\n{output}"

    def _backup_config(self, device):
        connection = SSHConnection(device, self.logger)
        try:
            if not connection.connect():
                return False, (
                    f"[配置备份] {self._device_label(device)} 连接失败: "
                    f"{connection.error_message or '未知错误'}"
                )

            brand = connection.brand_detected or getattr(device, "brand", "") or "h3c"
            command = get_command(brand, "display_config")
            output = connection.execute_command(command, sleep_time=0.5)
            if not output or re.search(
                r"%\s*Invalid|Unrecognized command|命令执行失败|Error:",
                output,
                re.IGNORECASE,
            ):
                return False, (
                    f"[配置备份] {self._device_label(device)} 未获得有效配置，"
                    f"实际查询命令: {command}"
                )

            config_text = normalize_device_config(output, command)
            if not config_text:
                return False, (
                    f"[配置备份] {self._device_label(device)} 清理终端信息后"
                    "没有可保存的配置内容"
                )

            output_dir = self.options["output_dir"]
            device_name = getattr(device, "name", "") or getattr(device, "ip", "")
            config_path, metadata_path = write_config_backup(
                output_dir,
                device_name=device_name,
                device_ip=getattr(device, "ip", ""),
                device_port=getattr(device, "port", 22),
                brand=brand,
                command=command,
                config_text=config_text,
            )
            return True, (
                f"[配置备份] {self._device_label(device)} 已保存配置: "
                f"{config_path}；元数据: {metadata_path}"
            )
        finally:
            connection.disconnect()
