"""IPv4 and IPv6 subnet calculator dialog."""

from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from utils.maintenance_tools import calculate_subnet


class SubnetCalculatorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("IPv4 / IPv6 子网计算器")
        self.resize(720, 560)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("输入带前缀长度的地址"))
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText(
            "例如：192.168.10.20/24 或 2001:db8::20/64"
        )
        layout.addWidget(self.address_input)

        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        layout.addWidget(self.result_view)

        button_row = QHBoxLayout()
        self.calculate_button = QPushButton("计算")
        self.calculate_button.setObjectName("btn_primary")
        self.close_button = QPushButton("关闭")
        self.close_button.setObjectName("btn_neutral")
        button_row.addWidget(self.calculate_button)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self.calculate_button.clicked.connect(self.calculate)
        self.address_input.returnPressed.connect(self.calculate)
        self.close_button.clicked.connect(self.accept)
        self.address_input.setFocus()

    def calculate(self) -> None:
        try:
            rows = calculate_subnet(self.address_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "地址输入错误", str(exc))
            return
        width = max(len(label) for label, _value in rows)
        self.result_view.setPlainText(
            "\n".join(
                f"{label.ljust(width)} : {value}"
                for label, value in rows
            )
        )
