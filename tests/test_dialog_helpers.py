import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QLineEdit, QMessageBox, QWidget

from ui.dialog_helpers import (
    confirm_action,
    create_secret_input_dialog,
    show_input_warning,
)


def test_secret_dialog_keeps_password_mode_and_fixed_size():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    dialog = create_secret_input_dialog(parent, "设置主密码", "请输入密码：")

    assert dialog.size().width() == 520
    assert dialog.size().height() == 210
    assert dialog.textEchoMode() == QLineEdit.Password
    assert dialog.parent() is parent

    dialog.close()
    parent.close()
    assert app is not None


def test_warning_and_confirmation_keep_message_box_contract(monkeypatch):
    calls = {}

    def fake_warning(parent, title, message):
        calls["warning"] = (parent, title, message)

    def fake_question(parent, title, message, buttons, default):
        calls["question"] = (parent, title, message, buttons, default)
        return QMessageBox.Yes

    monkeypatch.setattr(QMessageBox, "warning", fake_warning)
    monkeypatch.setattr(QMessageBox, "question", fake_question)

    show_input_warning(None, "地址格式错误")
    accepted = confirm_action(None, "确认清空", "确定吗？")

    assert calls["warning"][1:] == ("输入错误", "地址格式错误")
    assert calls["question"][1:3] == ("确认清空", "确定吗？")
    assert accepted is True
