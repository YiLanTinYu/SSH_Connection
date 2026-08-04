"""Reusable dialogs with consistent AOMT sizing and behavior."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QWidget,
)


def create_secret_input_dialog(
    parent: QWidget,
    title: str,
    prompt: str,
) -> QInputDialog:
    """Create the consistently sized password dialog used for credentials."""
    dialog = QInputDialog(parent)
    dialog.setObjectName("secret_input_dialog")
    dialog.setWindowTitle(title)
    dialog.setInputMode(QInputDialog.TextInput)
    dialog.setLabelText(prompt)
    dialog.setTextEchoMode(QLineEdit.Password)
    dialog.setOkButtonText("确定")
    dialog.setCancelButtonText("取消")
    dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    dialog.setFixedSize(520, 210)
    return dialog


def prompt_secret(parent: QWidget, title: str, prompt: str) -> tuple:
    dialog = create_secret_input_dialog(parent, title, prompt)
    accepted = dialog.exec_() == QDialog.Accepted
    value = dialog.textValue() if accepted else ""
    dialog.setTextValue("")
    dialog.deleteLater()
    return value, accepted


def show_input_warning(parent: QWidget, message: str) -> None:
    QMessageBox.warning(parent, "输入错误", message)


def confirm_action(parent: QWidget, title: str, message: str) -> bool:
    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return reply == QMessageBox.Yes
