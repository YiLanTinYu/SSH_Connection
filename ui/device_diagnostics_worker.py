"""Background workers for vendor-specific read-only diagnostic tools."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal

from config.health_profiles import normalize_custom_commands
from core.ssh_manager_simple import SSHConnection
from utils.device_diagnostics import (
    SUPPORTED_DIAGNOSTIC_BRANDS,
    choose_discovered_mac,
    command_is_supported,
    extract_mac_addresses,
    get_health_commands,
    get_interface_commands,
    get_lookup_command,
    normalize_brand,
    normalize_mac,
    parse_device_output,
    summarize_health,
    summarize_interface,
    summarize_mac_locations,
)


class DeviceDiagnosticsWorker(QThread):
    """Execute diagnostics in parallel and return ResultCenter-compatible rows."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str, object)

    def __init__(self, mode, devices, options=None, logger=None):
        super().__init__()
        self.mode = mode
        self.devices = list(devices or [])
        self.options = dict(options or {})
        self.logger = logger

    @staticmethod
    def _device_label(device):
        name = str(getattr(device, "name", "") or "").strip()
        ip = str(getattr(device, "ip", "") or "").strip()
        return f"{name} [{ip}]" if name else ip

    def run(self):
        if self.mode == "health_check":
            results = self._run_parallel(self.devices, self._health_device)
        elif self.mode == "interface_diagnosis":
            results = self._run_parallel(self.devices, self._diagnose_interface)
        elif self.mode == "terminal_locate":
            results = self._locate_terminal()
        else:
            results = []
        self.finished_signal.emit(self.mode, results)

    def _run_parallel(self, devices, handler, max_workers=5):
        if not devices:
            return []
        results = []
        with ThreadPoolExecutor(
            max_workers=min(max_workers, len(devices))
        ) as executor:
            futures = {executor.submit(handler, device): device for device in devices}
            for index, future in enumerate(as_completed(futures), start=1):
                device = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = self._exception_result(device, str(exc))
                results.append(result)
                state = "完成" if result.get("task_success") else "失败"
                self.progress_signal.emit(
                    f"({index}/{len(devices)}) "
                    f"{self._device_label(device)} {state}"
                )
        return results

    def _open_supported_connection(self, device):
        connection = SSHConnection(device, self.logger)
        if not connection.connect():
            return connection, (
                connection.error_message or "SSH 连接失败"
            )
        brand = normalize_brand(connection.brand_detected)
        if brand not in SUPPORTED_DIAGNOSTIC_BRANDS:
            return connection, (
                f"检测到品牌 {brand or '未知'}；当前诊断工具仅支持 "
                "H3C/Comware 和 Huawei VRP"
            )
        connection.brand_detected = brand
        return connection, ""

    def _health_device(self, device):
        connection, error = self._open_supported_connection(device)
        try:
            if error:
                return self._finish_connection(connection, False, error)
            outputs = {}
            brand = normalize_brand(connection.brand_detected)
            selected_items = self.options.get("builtin_items")
            builtin_commands = get_health_commands(brand, selected_items)
            custom_commands = normalize_custom_commands(
                self.options.get("custom_commands", {}).get(brand, [])
            )
            commands = list(builtin_commands)
            commands.extend(
                command for command in custom_commands
                if command not in commands
            )
            for command in commands:
                self.progress_signal.emit(
                    f"[一键巡检] {self._device_label(device)} 执行 {command}"
                )
                outputs[command] = connection.execute_command(
                    command, sleep_time=0.2
                )
            summary, usable = summarize_health(
                outputs,
                brand=brand,
                selected_items=selected_items,
            )
            custom_usable = any(
                command_is_supported(outputs.get(command, ""))
                for command in custom_commands
            )
            profile_name = str(
                self.options.get("profile_name") or "标准巡检"
            )
            summary = (
                f"巡检方案：{profile_name}\n"
                f"自定义只读命令：{len(custom_commands)} 条"
                "（仅保留原始输出）\n\n"
                f"{summary}"
            )
            usable = usable or custom_usable
            self._prepend_summary(connection, summary)
            return self._finish_connection(
                connection,
                usable,
                "" if usable else "未获得可结构化的巡检数据",
            )
        finally:
            connection.disconnect()

    def _diagnose_interface(self, device):
        interface = self.options["interface"]
        connection, error = self._open_supported_connection(device)
        try:
            if error:
                return self._finish_connection(connection, False, error)
            brand = normalize_brand(connection.brand_detected)
            command_templates = get_interface_commands(brand)
            outputs = {}
            for template in command_templates:
                command = template.format(interface=interface)
                self.progress_signal.emit(
                    f"[接口诊断] {self._device_label(device)} 执行 {command}"
                )
                outputs[template] = connection.execute_command(
                    command, sleep_time=0.2
                )
            summary, usable = summarize_interface(
                interface,
                outputs[command_templates[0]],
                outputs[command_templates[1]],
                outputs[command_templates[2]],
                brand=brand,
            )
            self._prepend_summary(connection, summary)
            return self._finish_connection(
                connection,
                usable,
                "" if usable else "未获得可结构化的接口详情",
            )
        finally:
            connection.disconnect()

    def _query_arp(self, device):
        target = self.options["target"]
        connection, error = self._open_supported_connection(device)
        try:
            if error:
                return self._finish_connection(connection, False, error), []
            brand = normalize_brand(connection.brand_detected)
            command, parse_command = get_lookup_command(brand, "arp", target)
            output = connection.execute_command(command, sleep_time=0.2)
            records = parse_device_output(brand, parse_command, output)
            records = [
                record for record in records
                if str(record.get("ip_address") or "").strip() == target
            ]
            macs = extract_mac_addresses(records)
            connection.task_success = command_is_supported(output)
            result = self._finish_connection(
                connection,
                connection.task_success,
                "" if connection.task_success else "ARP 查询命令未返回有效数据",
            )
            return result, macs
        finally:
            connection.disconnect()

    def _query_mac(self, device, mac):
        connection, error = self._open_supported_connection(device)
        try:
            if error:
                return self._finish_connection(connection, False, error), []
            brand = normalize_brand(connection.brand_detected)
            command, parse_command = get_lookup_command(brand, "mac", mac)
            output = connection.execute_command(command, sleep_time=0.2)
            records = parse_device_output(brand, parse_command, output)
            normalized_mac = normalize_mac(mac)
            records = [
                record for record in records
                if _record_mac(record) == normalized_mac
            ]
            connection.task_success = command_is_supported(output)
            result = self._finish_connection(
                connection,
                connection.task_success,
                "" if connection.task_success else "MAC 地址表查询命令未返回有效数据",
            )
            return result, records
        finally:
            connection.disconnect()

    def _locate_terminal(self):
        target_type = self.options["target_type"]
        target = self.options["target"]
        arp_results = {}
        mac_candidates = []
        if target_type == "ip":
            first_pass = self._run_parallel_pairs(self.devices, self._query_arp, "ARP")
            for device, result, values in first_pass:
                arp_results[self._device_key(device)] = result
                mac_candidates.extend(values)
            mac = choose_discovered_mac(mac_candidates)
            if not mac:
                for result in arp_results.values():
                    self._prepend_result_summary(
                        result,
                        f"目标 IP：{target}\n未在已选设备的 ARP 表中解析到 MAC 地址。",
                    )
                    result["task_success"] = False
                    result["error_message"] = "未解析到目标 IP 对应的 MAC 地址"
                return list(arp_results.values())
        else:
            mac = target

        second_pass = self._run_parallel_pairs(
            self.devices,
            lambda device: self._query_mac(device, mac),
            "MAC",
        )
        location_records = {}
        mac_results = {}
        for device, result, records in second_pass:
            key = self._device_key(device)
            mac_results[key] = result
            location_records[self._device_label(device)] = records

        summary = summarize_mac_locations(mac, location_records)
        if target_type == "ip":
            summary = f"目标 IP：{target}\n" + summary

        merged = []
        for device in self.devices:
            key = self._device_key(device)
            result = mac_results.get(key) or arp_results.get(key)
            if not result:
                continue
            arp_result = arp_results.get(key)
            if arp_result and result is not arp_result:
                result["command_results"] = (
                    arp_result.get("command_results", [])
                    + result.get("command_results", [])
                )
            self._prepend_result_summary(result, summary)
            result["task_success"] = bool(location_records.get(
                self._device_label(device)
            ))
            if not result["task_success"]:
                result["error_message"] = "本设备未找到目标 MAC"
            merged.append(result)
        return merged

    def _run_parallel_pairs(self, devices, handler, label):
        pairs = []
        if not devices:
            return pairs
        with ThreadPoolExecutor(max_workers=min(5, len(devices))) as executor:
            futures = {executor.submit(handler, device): device for device in devices}
            for index, future in enumerate(as_completed(futures), start=1):
                device = futures[future]
                try:
                    result, values = future.result()
                except Exception as exc:
                    result, values = self._exception_result(device, str(exc)), []
                pairs.append((device, result, values))
                self.progress_signal.emit(
                    f"[{label} 查询] ({index}/{len(devices)}) "
                    f"{self._device_label(device)}"
                )
        return pairs

    @staticmethod
    def _device_key(device):
        return (
            str(getattr(device, "ip", "") or "").lower(),
            int(getattr(device, "port", 22) or 22),
        )

    @staticmethod
    def _prepend_summary(connection, summary):
        connection.command_results.insert(0, {
            "command": "诊断摘要",
            "output": summary,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": 0.0,
        })

    @staticmethod
    def _prepend_result_summary(result, summary):
        result.setdefault("command_results", []).insert(0, {
            "command": "定位摘要",
            "output": summary,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": 0.0,
        })

    @staticmethod
    def _finish_connection(connection, success, error_message):
        connection.task_success = bool(success)
        connection.error_message = str(error_message or "")
        connection.mark_finished()
        return connection.get_connection_info()

    @staticmethod
    def _exception_result(device, message):
        now = datetime.now().isoformat(timespec="seconds")
        return {
            "device_info": device.to_dict(include_secrets=False),
            "is_connected": False,
            "task_success": False,
            "ssh_active": False,
            "brand_detected": "",
            "model_detected": "",
            "error_message": f"诊断任务异常: {message}",
            "command_results": [],
            "started_at": now,
            "finished_at": now,
            "duration_seconds": 0.0,
        }


def _record_mac(record):
    try:
        return normalize_mac(record.get("mac_address", ""))
    except ValueError:
        return ""
