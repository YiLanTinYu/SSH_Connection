import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMainWindow

from ui.main_window_status import MainWindowStatusController


def test_status_controller_owns_labels_and_progress_visibility():
    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    controller = MainWindowStatusController(window, "AOMT", "1.0.0", "倚栏听雨")
    try:
        assert window.statusBar() is controller.status_bar
        assert "作者：倚栏听雨" in controller.status_label.text()
        assert controller.progress_bar.isHidden()

        controller.set_status("正在连接")
        assert controller.device_count_label.text() == "正在连接"
        controller.show_progress()
        assert not controller.progress_bar.isHidden()
        controller.hide_progress()
        assert controller.progress_bar.isHidden()
        controller.update_device_count(6)
        assert controller.device_count_label.text() == "设备数: 6"
    finally:
        window.close()
