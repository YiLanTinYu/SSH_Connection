"""Device creation and validation independent from Qt widgets."""

from dataclasses import dataclass
import os

from config.device_config import DeviceInfo
from utils.ipv6_utils import IPv6AddressValidator


class DeviceFormError(ValueError):
    pass


@dataclass(frozen=True)
class DeviceFormValues:
    brand: str
    ip: str
    port: int
    username: str
    password: str
    name: str = ""
    group: str = ""
    tags: str = ""
    auth_method: str = "password"
    private_key_path: str = ""
    private_key_passphrase: str = ""
    host_key_policy: str = "tofu"


@dataclass(frozen=True)
class ExcelImportResult:
    added: int
    failed: int
    skipped: int
    errors: tuple
    skipped_devices: tuple

    def summary(self) -> str:
        message = (
            "导入完成！\n"
            f"新增: {self.added} 个\n"
            f"跳过重复: {self.skipped} 个\n"
            f"失败: {self.failed} 个"
        )
        details = []
        if self.skipped_devices:
            details.append("重复设备:")
            details.extend(self.skipped_devices[:5])
        if self.errors:
            details.append("错误信息:")
            details.extend(self.errors[:5])
        if details:
            message += "\n\n" + "\n".join(details)
        return message


def add_device_from_form(manager, values: DeviceFormValues) -> DeviceInfo:
    ip = values.ip.strip()
    username = values.username.strip()
    password = values.password.strip()
    private_key_path = values.private_key_path.strip()

    if not ip:
        raise DeviceFormError("请输入 IP 地址")
    is_valid, error_message = IPv6AddressValidator().validate_for_ssh(ip)
    if not is_valid:
        raise DeviceFormError(f"IP 地址格式错误:\n{error_message}")
    if not username:
        raise DeviceFormError("请输入用户名")
    if values.auth_method == "password" and not password:
        raise DeviceFormError("请输入密码")
    if values.auth_method == "key" and not private_key_path:
        raise DeviceFormError("请选择 SSH 私钥文件")
    if values.auth_method == "key" and not os.path.isfile(private_key_path):
        raise DeviceFormError("SSH 私钥文件不存在")

    device = DeviceInfo(
        values.brand,
        ip,
        values.port,
        username,
        password,
        values.name.strip(),
        group=values.group.strip(),
        tags=values.tags.strip(),
        auth_method=values.auth_method,
        private_key_path=private_key_path,
        private_key_passphrase=values.private_key_passphrase,
        host_key_policy=values.host_key_policy,
    )
    if not manager.add_device(device):
        raise DeviceFormError(f"设备已存在，已跳过: {ip}:{values.port}")
    return device


def import_device_excel(
    manager,
    file_path: str,
    master_password: str = "",
) -> ExcelImportResult:
    added, failed, errors = manager.import_from_excel(
        file_path,
        master_password=master_password,
    )
    return ExcelImportResult(
        added=added,
        failed=failed,
        skipped=getattr(manager, "last_import_skipped_count", 0),
        errors=tuple(errors or ()),
        skipped_devices=tuple(getattr(manager, "last_import_skipped", ()) or ()),
    )


def remove_devices_at_rows(manager, rows) -> int:
    device_count = len(manager.get_devices())
    valid_rows = sorted(
        {int(row) for row in rows if 0 <= int(row) < device_count},
        reverse=True,
    )
    for row in valid_rows:
        manager.remove_device(row)
    return len(valid_rows)


def clear_all_devices(manager) -> int:
    count = len(manager.get_devices())
    manager.clear_devices()
    return count
