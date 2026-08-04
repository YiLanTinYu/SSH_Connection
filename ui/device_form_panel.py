"""Device creation form panel."""

from typing import Callable, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class DeviceFormPanel(QGroupBox):
    """Collect device connection fields without owning persistence logic."""

    add_requested = pyqtSignal()
    browse_private_key_requested = pyqtSignal()
    auth_method_changed = pyqtSignal()

    def __init__(
        self,
        form_label_factory: Optional[Callable[[str], QLabel]] = None,
        parent=None,
    ):
        super().__init__("添加设备", parent)
        self._form_label_factory = form_label_factory or self._default_form_label
        self._build_ui()
        self._connect_signals()
        self.update_auth_fields()

    @staticmethod
    def _default_form_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("field_label")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return label

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)
        form.setColumnMinimumWidth(0, 0)
        form.setColumnStretch(0, 0)
        form.setColumnStretch(1, 1)

        def add_form_row(row_index, label_text, widget):
            label = self._form_label_factory(label_text)
            widget.setSizePolicy(
                QSizePolicy.Expanding,
                widget.sizePolicy().verticalPolicy(),
            )
            form.addWidget(label, row_index, 0)
            form.addWidget(widget, row_index, 1)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如：SW1")
        add_form_row(0, "名 称:", self.name_input)

        self.brand_combo = QComboBox()
        self.brand_combo.addItems(["H3C", "Huawei"])
        add_form_row(1, "品 牌:", self.brand_combo)

        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("例如：核心交换机")
        add_form_row(2, "分 组:", self.group_input)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("例如：机房A,核心")
        add_form_row(3, "标 签:", self.tags_input)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.1  或  2001:db8::1")
        add_form_row(4, "IP 地址:", self.ip_input)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        add_form_row(5, "端 口:", self.port_spin)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("admin")
        add_form_row(6, "用户名:", self.username_input)

        self.auth_method_combo = QComboBox()
        self.auth_method_combo.addItem("密码认证", "password")
        self.auth_method_combo.addItem("私钥认证", "key")
        add_form_row(7, "认 证:", self.auth_method_combo)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_label = self._form_label_factory("密 码:")
        form.addWidget(self.password_label, 8, 0)
        form.addWidget(self.password_input, 8, 1)

        self.private_key_row = QWidget()
        key_layout = QHBoxLayout(self.private_key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(6)
        self.private_key_input = QLineEdit()
        self.private_key_input.setPlaceholderText("选择 OpenSSH/PEM 私钥")
        self.private_key_button = QPushButton("…")
        self.private_key_button.setFixedWidth(42)
        self.private_key_button.setToolTip("选择 SSH 私钥文件")
        key_layout.addWidget(self.private_key_input, 1)
        key_layout.addWidget(self.private_key_button)
        self.private_key_label = self._form_label_factory("私 钥:")
        form.addWidget(self.private_key_label, 9, 0)
        form.addWidget(self.private_key_row, 9, 1)

        self.key_passphrase_input = QLineEdit()
        self.key_passphrase_input.setEchoMode(QLineEdit.Password)
        self.key_passphrase_input.setPlaceholderText("私钥无口令可留空")
        self.key_passphrase_label = self._form_label_factory("口 令:")
        form.addWidget(self.key_passphrase_label, 10, 0)
        form.addWidget(self.key_passphrase_input, 10, 1)

        self.host_key_policy_combo = QComboBox()
        self.host_key_policy_combo.addItem("首次信任，后续校验", "tofu")
        self.host_key_policy_combo.addItem("严格校验", "strict")
        self.host_key_policy_combo.addItem("不校验（不推荐）", "insecure")
        add_form_row(11, "主机键:", self.host_key_policy_combo)

        layout.addLayout(form)
        self.add_btn = QPushButton("添加设备")
        self.add_btn.setObjectName("btn_primary")
        layout.addWidget(self.add_btn)

    def _connect_signals(self) -> None:
        self.auth_method_combo.currentIndexChanged.connect(
            self._on_auth_method_changed
        )
        self.private_key_button.clicked.connect(
            self.browse_private_key_requested.emit
        )
        self.add_btn.clicked.connect(self.add_requested.emit)

    def _on_auth_method_changed(self, _index: int) -> None:
        self.update_auth_fields()
        self.auth_method_changed.emit()

    def update_auth_fields(self) -> None:
        use_key = self.auth_method_combo.currentData() == "key"
        self.password_label.setVisible(not use_key)
        self.password_input.setVisible(not use_key)
        self.private_key_label.setVisible(use_key)
        self.private_key_row.setVisible(use_key)
        self.key_passphrase_label.setVisible(use_key)
        self.key_passphrase_input.setVisible(use_key)
