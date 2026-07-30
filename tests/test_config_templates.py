import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QDialogButtonBox

from config.builtin_templates import get_builtin_templates
from config.template_renderer import (
    TemplateValidationError,
    render_template,
    validate_template_value,
)
from core.ssh_manager_simple import SSHManager
from ui.config_template_dialog import ConfigTemplateDialog


def _template(template_id):
    return next(
        item for item in get_builtin_templates() if item["id"] == template_id
    )


def _values(template, *, password="AomtPass!2026"):
    return {
        field["name"]: (
            password if field.get("sensitive") else field.get("default", "")
        )
        for field in template["parameters"]
    }


def test_h3c_ssh_template_masks_password_and_keeps_manual_key_step():
    template = _template("h3c_ssh")
    rendered = render_template(template, _values(template))
    commands = "\n".join(rendered.commands)

    assert "password simple AomtPass!2026" in commands
    assert "AomtPass!2026" not in rendered.preview
    assert "password simple ********" in rendered.preview
    assert "authentication-mode scheme" in commands
    assert "protocol inbound ssh" in commands
    assert any("public-key local create rsa" in step for step in rendered.manual_steps)


def test_huawei_ssh_template_uses_aaa_and_stelnet():
    template = _template("huawei_ssh")
    commands = "\n".join(render_template(template, _values(template)).commands)

    assert "local-user admin password irreversible-cipher" in commands
    assert "local-user admin service-type ssh terminal" in commands
    assert "stelnet server enable" in commands
    assert "authentication-mode aaa" in commands
    assert "protocol inbound ssh" in commands


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ({"label": "VLAN", "kind": "vlan"}, "4095", "范围"),
        ({"label": "地址", "kind": "ipv4"}, "999.1.1.1", "IPv4"),
        ({"label": "接口", "kind": "interface"}, "GE 1/0/1", "接口"),
        ({"label": "密码", "kind": "password"}, "password", "三类"),
        ({"label": "密码", "kind": "password"}, "AomtPass?2026", "字符"),
        ({"label": "描述", "kind": "description"}, "bad\ncommand", "控制字符"),
    ),
)
def test_template_parameter_validation_rejects_unsafe_values(
    field,
    value,
    message,
):
    with pytest.raises(TemplateValidationError, match=message):
        validate_template_value(field, value)


def test_manager_uses_rendered_commands_without_writing_password_file():
    template = _template("h3c_ssh")
    rendered = render_template(template, _values(template))
    manager = SSHManager()
    manager.command_lines = list(rendered.commands)
    manager.command_label = template["name"]
    manager.required_brand = template["brand"]

    commands, label = manager._load_commands_for_device(object())

    assert commands == list(rendered.commands)
    assert label == template["name"]
    assert manager.required_brand == "h3c"


def test_connection_results_and_progress_redact_template_password(monkeypatch):
    from config.device_config import DeviceInfo
    from core.ssh_manager_simple import SSHConnection

    connection = SSHConnection(
        DeviceInfo("h3c", "192.0.2.10", 22, "admin", "login-password")
    )
    connection.is_connected = True
    connection._shell = object()
    connection.sensitive_values = ["AomtPass!2026"]
    sent = []
    progress = []

    monkeypatch.setattr(
        connection,
        "execute_command",
        lambda command: (
            sent.append(command),
            f"echo {command}",
        )[1],
    )
    results = connection.execute_commands(
        ["password simple AomtPass!2026"],
        progress_cb=progress.append,
    )

    assert sent == ["password simple AomtPass!2026"]
    assert all("AomtPass!2026" not in message for message in progress)
    assert "AomtPass!2026" not in str(results)
    assert "********" in str(results)


def test_low_level_command_history_redacts_template_password(monkeypatch):
    from config.device_config import DeviceInfo
    from core.ssh_manager_simple import SSHConnection

    class FakeShell:
        def __init__(self):
            self.sent = []

        def send(self, value):
            self.sent.append(value)

    connection = SSHConnection(
        DeviceInfo("h3c", "192.0.2.10", 22, "admin", "login-password")
    )
    connection.is_connected = True
    connection._shell = FakeShell()
    connection.sensitive_values = ["AomtPass!2026"]
    monkeypatch.setattr(
        connection,
        "_read_until_prompt",
        lambda timeout=15: "password simple AomtPass!2026\n[SW1]",
    )

    output = connection.execute_command(
        "password simple AomtPass!2026",
        sleep_time=0,
    )

    assert connection._shell.sent == ["password simple AomtPass!2026\n"]
    assert "AomtPass!2026" in output
    assert "AomtPass!2026" not in str(connection.command_results)
    assert "********" in str(connection.command_results)


def test_parameter_dialog_disables_call_until_sensitive_fields_are_valid():
    app = QApplication.instance() or QApplication([])
    template = _template("h3c_ssh")
    dialog = ConfigTemplateDialog(template)
    try:
        ok_button = dialog.buttons.button(QDialogButtonBox.Ok)
        assert not ok_button.isEnabled()

        dialog.inputs["ADMIN_PASSWORD"].setText("AomtPass!2026")
        app.processEvents()

        assert ok_button.isEnabled()
        assert dialog.rendered_template is not None
        assert "AomtPass!2026" not in dialog.preview.toPlainText()
    finally:
        dialog.close()
