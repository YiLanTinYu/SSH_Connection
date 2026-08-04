from types import SimpleNamespace

from controllers.main_window_action_controller import MainWindowActionController


class FakeLabel:
    def __init__(self):
        self.text = ""
        self.tooltip = "unset"

    def setText(self, text):
        self.text = text

    def setToolTip(self, text):
        self.tooltip = text


class FakeCombo:
    def __init__(self, data):
        self.data = data

    def currentData(self):
        return self.data


def _command_window(mode="single"):
    return SimpleNamespace(
        _command_file="custom.txt",
        _command_directory="scripts",
        _command_lines=None,
        cmd_mode_combo=FakeCombo(mode),
        cmd_browse_btn=FakeLabel(),
        cmd_file_label=FakeLabel(),
        _cmd_tip_label=FakeLabel(),
        _clear_parameterized_template=lambda *args: None,
        _log_info=lambda text: None,
        _set_status=lambda text: None,
        _update_device_count=lambda: None,
    )


def test_action_controller_switches_command_mode_without_losing_contract():
    window = _command_window("per_device")
    MainWindowActionController(window).on_command_mode_changed()

    assert window._command_file is None
    assert window.cmd_browse_btn.text == "选择脚本目录"
    assert window.cmd_file_label.text == "scripts"
    assert "SW1.txt" in window._cmd_tip_label.text


def test_action_controller_resets_command_source_for_current_mode():
    window = _command_window("single")
    MainWindowActionController(window).reset_command_file()

    assert window._command_file is None
    assert window._command_directory is None
    assert window.cmd_file_label.text == "SSH_command.txt  (默认)"
    assert window.cmd_file_label.tooltip == ""
