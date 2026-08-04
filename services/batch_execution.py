"""Pure preparation helpers for batch command execution."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class BatchCommandSettings:
    command_file: str = None
    command_directory: str = None
    command_lines: tuple = None
    command_label: str = ""
    required_brand: str = ""
    sensitive_values: tuple = ()


def configure_ssh_manager(manager, settings: BatchCommandSettings) -> None:
    manager.command_file = settings.command_file
    manager.command_directory = settings.command_directory
    manager.command_lines = (
        list(settings.command_lines)
        if settings.command_lines is not None
        else None
    )
    manager.command_label = settings.command_label
    manager.required_brand = settings.required_brand
    manager.sensitive_values = list(settings.sensitive_values)


def devices_with_brand_mismatch(devices, required_brand: str) -> list:
    required = str(required_brand or "").lower()
    if not required:
        return []
    return [
        device
        for device in devices
        if str(getattr(device, "brand", "") or "").lower()
        not in ("", "unknown", required)
    ]


def command_source_label(
    active_template_name: str,
    mode: str,
    command_directory: str,
    command_file: str,
) -> str:
    if active_template_name:
        return active_template_name
    if mode == "per_device" and command_directory:
        return f"按设备匹配：{os.path.basename(command_directory)}"
    return os.path.basename(command_file or "SSH_command.txt")


def execution_device_keys(devices) -> set:
    return {(device.ip, int(device.port)) for device in devices}
