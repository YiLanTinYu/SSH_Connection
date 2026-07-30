"""Health-check profile selector and editor."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.health_profiles import (
    DEFAULT_PROFILE_NAME,
    HealthProfileStore,
    normalize_custom_commands,
)
from utils.device_diagnostics import HEALTH_CHECK_ITEMS, HEALTH_CHECK_ITEM_IDS


class HealthProfileDialog(QDialog):
    def __init__(self, parent=None, store=None):
        super().__init__(parent)
        flags = self.windowFlags()
        flags &= ~Qt.WindowContextHelpButtonHint
        flags |= Qt.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        self.setWindowTitle("一键设备巡检方案")
        self.resize(820, 680)
        self.setMinimumSize(680, 560)
        self.store = store or HealthProfileStore(HEALTH_CHECK_ITEM_IDS)
        self._profiles = {}
        self._selected_options = {}
        self._build_ui()
        self._reload_profiles()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("巡检方案"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self._load_selected_profile)
        profile_row.addWidget(self.profile_combo, 1)
        self.save_button = QPushButton("保存方案")
        self.delete_button = QPushButton("删除方案")
        self.save_button.clicked.connect(self._save_profile)
        self.delete_button.clicked.connect(self._delete_profile)
        profile_row.addWidget(self.save_button)
        profile_row.addWidget(self.delete_button)
        layout.addLayout(profile_row)

        builtin_group = QGroupBox("内置巡检项目")
        builtin_layout = QGridLayout(builtin_group)
        self.item_checks = {}
        for index, item in enumerate(HEALTH_CHECK_ITEMS):
            checkbox = QCheckBox(item["label"])
            checkbox.setChecked(True)
            checkbox.setToolTip(
                f"H3C：{item['commands']['h3c']}\n"
                f"Huawei：{item['commands']['huawei']}"
            )
            self.item_checks[item["id"]] = checkbox
            builtin_layout.addWidget(checkbox, index // 2, index % 2)
        layout.addWidget(builtin_group)

        custom_group = QGroupBox("品牌自定义查询命令")
        custom_layout = QVBoxLayout(custom_group)
        self.brand_tabs = QTabWidget()
        self.custom_editors = {}
        for brand, label in (("h3c", "H3C / Comware"), ("huawei", "Huawei VRP")):
            page = QWidget()
            page_layout = QFormLayout(page)
            editor = QPlainTextEdit()
            editor.setPlaceholderText("每行一条 display 查询命令")
            editor.setTabChangesFocus(True)
            self.custom_editors[brand] = editor
            page_layout.addRow(editor)
            self.brand_tabs.addTab(page, label)
        custom_layout.addWidget(self.brand_tabs)
        raw_note = QLabel("自定义命令仅保留原始输出，不参与自动健康判定。")
        raw_note.setObjectName("hint_text")
        custom_layout.addWidget(raw_note)
        layout.addWidget(custom_group, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.button(QDialogButtonBox.Ok).setText("开始巡检")
        self.buttons.button(QDialogButtonBox.Cancel).setText("取消")
        self.buttons.accepted.connect(self._accept_profile)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _default_profile(self):
        return {
            "builtin_items": list(HEALTH_CHECK_ITEM_IDS),
            "custom_commands": {"h3c": [], "huawei": []},
        }

    def _reload_profiles(self, selected_name=DEFAULT_PROFILE_NAME):
        self._profiles = {
            DEFAULT_PROFILE_NAME: self._default_profile(),
            **self.store.load(),
        }
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self._profiles)
        index = self.profile_combo.findText(selected_name)
        self.profile_combo.setCurrentIndex(max(0, index))
        self.profile_combo.blockSignals(False)
        self._load_selected_profile(self.profile_combo.currentText())

    def _load_selected_profile(self, name):
        profile = self._profiles.get(name, self._default_profile())
        selected = set(profile.get("builtin_items", []))
        for item_id, checkbox in self.item_checks.items():
            checkbox.setChecked(item_id in selected)
        custom = profile.get("custom_commands", {})
        for brand, editor in self.custom_editors.items():
            editor.setPlainText("\n".join(custom.get(brand, [])))
        self.delete_button.setEnabled(name != DEFAULT_PROFILE_NAME)

    def _collect_profile(self):
        selected = [
            item_id for item_id, checkbox in self.item_checks.items()
            if checkbox.isChecked()
        ]
        custom = {}
        for brand, editor in self.custom_editors.items():
            custom[brand] = normalize_custom_commands(
                editor.toPlainText().splitlines()
            )
        if not selected and not any(custom.values()):
            raise ValueError("请至少选择一个内置巡检项目或添加一条自定义命令")
        return {
            "builtin_items": selected,
            "custom_commands": custom,
        }

    def _save_profile(self):
        try:
            profile = self._collect_profile()
        except ValueError as exc:
            QMessageBox.warning(self, "巡检方案", str(exc))
            return
        current = self.profile_combo.currentText()
        default_name = "" if current == DEFAULT_PROFILE_NAME else current
        name, accepted = QInputDialog.getText(
            self, "保存巡检方案", "方案名称：", text=default_name
        )
        if not accepted:
            return
        try:
            self.store.save(name, profile)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        self._reload_profiles(str(name).strip())

    def _delete_profile(self):
        name = self.profile_combo.currentText()
        if name == DEFAULT_PROFILE_NAME:
            return
        answer = QMessageBox.question(
            self,
            "删除巡检方案",
            f"确定删除巡检方案“{name}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.store.delete(name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "删除失败", str(exc))
            return
        self._reload_profiles()

    def _accept_profile(self):
        try:
            profile = self._collect_profile()
        except ValueError as exc:
            QMessageBox.warning(self, "巡检方案", str(exc))
            return
        profile["profile_name"] = self.profile_combo.currentText()
        self._selected_options = profile
        self.accept()

    def selected_options(self) -> dict:
        return dict(self._selected_options)
