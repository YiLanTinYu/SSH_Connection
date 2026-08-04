from types import SimpleNamespace

from controllers.tool_window_controller import ToolWindowController


class FakeSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback


class FakeDialog:
    def __init__(self, *args):
        self.args = args
        self.destroyed = FakeSignal()
        self.attributes = []
        self.calls = []
        self.devices = None

    def setAttribute(self, attribute):
        self.attributes.append(attribute)

    def show(self):
        self.calls.append("show")

    def raise_(self):
        self.calls.append("raise")

    def activateWindow(self):
        self.calls.append("activate")

    def set_devices(self, devices):
        self.devices = devices


def _window():
    return SimpleNamespace(
        _serial_console=None,
        _ssh_console=None,
        _file_transfer_dialog=None,
        _packet_capture_dialog=None,
        _get_task_devices=lambda mode: [mode],
    )


def test_tool_window_controller_reuses_singleton_and_clears_destroyed_cache():
    window = _window()
    controller = ToolWindowController(window, serial_dialog=FakeDialog)

    first = controller.show_serial_console()
    second = controller.show_serial_console()

    assert first is second
    assert first.args == (window,)
    assert first.calls == [
        "show", "raise", "activate",
        "show", "raise", "activate",
    ]
    first.destroyed.callback()
    assert window._serial_console is None


def test_tool_window_controller_refreshes_devices_for_existing_ssh_dialog():
    window = _window()
    controller = ToolWindowController(window, ssh_dialog=FakeDialog)

    dialog = controller.show_ssh_console()
    assert dialog.args == (["ssh_console"], window)

    window._get_task_devices = lambda mode: ["updated", mode]
    reused = controller.show_ssh_console()
    assert reused is dialog
    assert reused.devices == ["updated", "ssh_console"]
