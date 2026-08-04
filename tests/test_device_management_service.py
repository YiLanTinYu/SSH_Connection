from pathlib import Path

import pytest

from config.device_config import DeviceConfigManager
from services.device_management import (
    DeviceFormError,
    DeviceFormValues,
    add_device_from_form,
    clear_all_devices,
    import_device_excel,
    remove_devices_at_rows,
)


def _values(**overrides):
    values = {
        "brand": "H3C",
        "ip": "192.0.2.10",
        "port": 22,
        "username": "admin",
        "password": "secret",
    }
    values.update(overrides)
    return DeviceFormValues(**values)


def test_add_device_from_form_validates_and_rejects_duplicates():
    manager = DeviceConfigManager()
    device = add_device_from_form(manager, _values(name="SW1", group="核心"))

    assert device.name == "SW1"
    assert device.group == "核心"
    assert manager.get_devices() == [device]

    with pytest.raises(DeviceFormError, match="设备已存在"):
        add_device_from_form(manager, _values())


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"ip": ""}, "请输入 IP 地址"),
        ({"ip": "999.999.999.999"}, "IP 地址格式错误"),
        ({"username": ""}, "请输入用户名"),
        ({"password": ""}, "请输入密码"),
        (
            {
                "auth_method": "key",
                "password": "",
                "private_key_path": "",
            },
            "请选择 SSH 私钥文件",
        ),
    ],
)
def test_add_device_from_form_keeps_validation_messages(overrides, message):
    with pytest.raises(DeviceFormError, match=message):
        add_device_from_form(DeviceConfigManager(), _values(**overrides))


def test_add_device_from_form_accepts_existing_private_key(tmp_path: Path):
    key_path = tmp_path / "id_ed25519"
    key_path.write_text("test", encoding="ascii")
    device = add_device_from_form(
        DeviceConfigManager(),
        _values(
            auth_method="key",
            password="",
            private_key_path=str(key_path),
        ),
    )
    assert device.auth_method == "key"
    assert device.private_key_path == str(key_path)


def test_import_device_excel_collects_duplicate_and_error_details():
    class FakeManager:
        last_import_skipped_count = 2
        last_import_skipped = ["SW1", "SW2"]

        @staticmethod
        def import_from_excel(file_path, master_password=""):
            assert file_path == "devices.xlsx"
            assert master_password == "master-password"
            return 3, 1, ["第 4 行地址无效"]

    result = import_device_excel(
        FakeManager(),
        "devices.xlsx",
        master_password="master-password",
    )

    assert (result.added, result.skipped, result.failed) == (3, 2, 1)
    assert result.skipped_devices == ("SW1", "SW2")
    assert result.errors == ("第 4 行地址无效",)
    assert "新增: 3 个" in result.summary()
    assert "重复设备:\nSW1\nSW2" in result.summary()
    assert "错误信息:\n第 4 行地址无效" in result.summary()


def test_remove_devices_at_rows_deletes_in_reverse_and_ignores_invalid_rows():
    class FakeManager:
        def __init__(self):
            self.devices = ["SW1", "SW2", "SW3", "SW4"]
            self.removed = []

        def get_devices(self):
            return self.devices

        def remove_device(self, row):
            self.removed.append(row)
            self.devices.pop(row)

    manager = FakeManager()
    count = remove_devices_at_rows(manager, [1, 3, 1, 99, -1])

    assert count == 2
    assert manager.removed == [3, 1]
    assert manager.devices == ["SW1", "SW3"]


def test_clear_all_devices_returns_previous_count():
    class FakeManager:
        def __init__(self):
            self.devices = ["SW1", "SW2"]

        def get_devices(self):
            return self.devices

        def clear_devices(self):
            self.devices.clear()

    manager = FakeManager()
    assert clear_all_devices(manager) == 2
    assert manager.devices == []
