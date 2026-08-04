"""Status-bar ownership for the main window."""

from PyQt5.QtWidgets import QLabel, QProgressBar, QStatusBar


class MainWindowStatusController:
    def __init__(self, window, app_name: str, version: str, author: str):
        self.window = window
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setMinimumHeight(42)
        window.setStatusBar(self.status_bar)

        self.status_label = QLabel(
            f"{app_name}  |  版本 v{version}  |  作者：{author}"
        )
        self.status_label.setContentsMargins(4, 4, 4, 4)
        self.status_label.setStyleSheet(
            "color: rgba(255,255,255,0.75); background: transparent;"
        )
        self.status_bar.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedSize(120, 12)
        self.progress_bar.setTextVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.device_count_label = QLabel("设备数: 0")
        self.device_count_label.setContentsMargins(4, 4, 4, 4)
        self.device_count_label.setStyleSheet(
            "color: rgba(255,255,255,0.75); background: transparent; "
            "margin-right: 8px;"
        )
        self.status_bar.addPermanentWidget(self.device_count_label)

    def set_status(self, text: str) -> None:
        self.device_count_label.setText(text)

    def show_progress(self) -> None:
        self.progress_bar.setVisible(True)

    def hide_progress(self) -> None:
        self.progress_bar.setVisible(False)

    def update_device_count(self, count: int) -> None:
        self.device_count_label.setText(f"设备数: {count}")
