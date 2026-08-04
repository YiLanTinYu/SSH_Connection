from types import SimpleNamespace

from services.batch_execution import (
    BatchCommandSettings,
    command_source_label,
    configure_ssh_manager,
    devices_with_brand_mismatch,
    execution_device_keys,
)


def test_configure_ssh_manager_copies_mutable_command_data():
    manager = SimpleNamespace()
    settings = BatchCommandSettings(
        command_file="commands.txt",
        command_directory="scripts",
        command_lines=("display version",),
        command_label="巡检",
        required_brand="h3c",
        sensitive_values=("secret",),
    )
    configure_ssh_manager(manager, settings)

    assert manager.command_lines == ["display version"]
    assert manager.sensitive_values == ["secret"]
    assert manager.required_brand == "h3c"


def test_brand_mismatch_allows_unknown_but_blocks_other_known_brand():
    h3c = SimpleNamespace(brand="h3c")
    huawei = SimpleNamespace(brand="huawei")
    unknown = SimpleNamespace(brand="unknown")
    assert devices_with_brand_mismatch([h3c, huawei, unknown], "h3c") == [huawei]


def test_command_source_and_execution_keys_follow_current_modes():
    assert command_source_label("开局模板", "single", None, None) == "开局模板"
    assert command_source_label("", "per_device", "C:/scripts/SW", None) == (
        "按设备匹配：SW"
    )
    assert command_source_label("", "single", None, None) == "SSH_command.txt"
    devices = [
        SimpleNamespace(ip="192.0.2.1", port=22),
        SimpleNamespace(ip="2001:db8::1", port="2222"),
    ]
    assert execution_device_keys(devices) == {
        ("192.0.2.1", 22),
        ("2001:db8::1", 2222),
    }
