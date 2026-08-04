import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

import ui.config_diff_dialog as config_diff_dialog
from ui.config_diff_dialog import ConfigDiffDialog
from ui.subnet_calculator_dialog import SubnetCalculatorDialog


def test_subnet_calculator_dialog_formats_ipv4_and_ipv6_results():
    app = QApplication.instance() or QApplication([])
    dialog = SubnetCalculatorDialog()

    dialog.address_input.setText("192.168.10.20/24")
    dialog.calculate_button.click()
    ipv4 = dialog.result_view.toPlainText()
    assert "IPv4" in ipv4
    assert "255.255.255.0" in ipv4
    assert "192.168.10.255" in ipv4

    dialog.address_input.setText("2001:db8::20/64")
    dialog.calculate_button.click()
    ipv6 = dialog.result_view.toPlainText()
    assert "IPv6" in ipv6
    assert "2001:db8::" in ipv6
    assert app is not None


def test_config_diff_dialog_displays_and_saves_exact_diff(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    output = tmp_path / "diff.txt"
    monkeypatch.setattr(
        config_diff_dialog.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output), "文本文件 (*.txt)"),
    )
    dialog = ConfigDiffDialog("a.cfg", "b.cfg", "-vlan 10\n+vlan 20")
    saved = []
    dialog.diff_saved.connect(saved.append)

    assert "第一份：a.cfg" in dialog.title_label.text()
    assert dialog.viewer.toPlainText() == "-vlan 10\n+vlan 20"
    assert dialog.viewer.isReadOnly()
    dialog.save_button.click()

    assert saved == [str(output)]
    assert output.read_text(encoding="utf-8").splitlines() == [
        "-vlan 10",
        "+vlan 20",
    ]
    assert app is not None
