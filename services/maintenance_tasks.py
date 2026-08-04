"""Metadata, summaries, and log persistence for maintenance tasks."""

from dataclasses import dataclass
from datetime import datetime
import os

from utils.maintenance_tools import write_lines


@dataclass(frozen=True)
class TaskDefinition:
    label: str
    log_prefix: str
    completion_label: str = ""

    @property
    def result_label(self) -> str:
        return self.completion_label or self.label


MAINTENANCE_TASKS = {
    "port": TaskDefinition("批量端口检测", "port", "端口检测"),
    "ssh_login": TaskDefinition("批量 SSH 登录测试", "ssh_login", "SSH 登录测试"),
    "traceroute": TaskDefinition("批量路由跟踪", "traceroute", "路由跟踪"),
    "backup": TaskDefinition("批量配置备份", "config_backup", "配置备份"),
}

DIAGNOSTIC_TASKS = {
    "health_check": TaskDefinition("一键设备巡检", "health_check"),
    "terminal_locate": TaskDefinition(
        "IP/MAC 终端定位",
        "terminal_locate",
        "IP_MAC终端定位",
    ),
    "interface_diagnosis": TaskDefinition("接口综合诊断", "interface_diagnosis"),
}


def maintenance_task_definition(mode: str) -> TaskDefinition:
    return MAINTENANCE_TASKS.get(
        mode,
        TaskDefinition("运维任务", "maintenance"),
    )


def diagnostic_task_definition(mode: str) -> TaskDefinition:
    return DIAGNOSTIC_TASKS.get(
        mode,
        TaskDefinition("设备诊断", "diagnostics"),
    )


def diagnostic_result_counts(results) -> tuple:
    items = list(results or [])
    success = sum(bool(item.get("task_success")) for item in items)
    return items, success, len(items) - success


def save_maintenance_log(
    log_dir: str,
    prefix: str,
    lines,
    timestamp: datetime = None,
) -> str:
    target_dir = os.path.abspath(log_dir)
    os.makedirs(target_dir, exist_ok=True)
    current = timestamp or datetime.now()
    base_name = f"{prefix}{current.strftime('%Y%m%d%H%M')}"
    log_path = os.path.join(target_dir, f"{base_name}.log")
    counter = 1
    while os.path.exists(log_path):
        log_path = os.path.join(target_dir, f"{base_name}_{counter}.log")
        counter += 1
    write_lines(log_path, lines)
    return log_path
