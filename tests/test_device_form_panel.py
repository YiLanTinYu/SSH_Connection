import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QLineEdit

from ui.device_form_panel import DeviceFormPanel


def test_device_form_panel_defaults_and_auth_visibility():
    app = QApplication.instance() or QApplication([])
    panel = DeviceFormPanel()

    assert [panel.brand_combo.itemText(i) for i in range(panel.brand_combo.count())] == [
        "H3C", "Huawei"
    ]
    assert panel.port_spin.value() == 22
    assert panel.port_spin.minimum() == 1
    assert panel.port_spin.maximum() == 65535
    assert panel.password_input.echoMode() == QLineEdit.Password
    assert panel.host_key_policy_combo.currentData() == "tofu"
    assert panel.private_key_row.isHidden() is True
    assert panel.key_passphrase_input.isHidden() is True

    panel.auth_method_combo.setCurrentIndex(1)
    assert panel.password_input.isHidden() is True
    assert panel.private_key_row.isHidden() is False
    assert panel.key_passphrase_input.isHidden() is False
    assert app is not None


def test_device_form_panel_forwards_actions():
    app = QApplication.instance() or QApplication([])
    panel = DeviceFormPanel()
    events = []
    panel.auth_method_changed.connect(lambda: events.append("auth"))
    panel.browse_private_key_requested.connect(lambda: events.append("browse"))
    panel.add_requested.connect(lambda: events.append("add"))

    panel.auth_method_combo.setCurrentIndex(1)
    panel.private_key_button.click()
    panel.add_btn.click()

    assert events == ["auth", "browse", "add"]
    assert app is not None
