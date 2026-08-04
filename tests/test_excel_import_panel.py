import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ui.excel_import_panel import ExcelImportPanel


def test_excel_import_panel_buttons_and_signals():
    app = QApplication.instance() or QApplication([])
    panel = ExcelImportPanel()
    events = []
    panel.import_requested.connect(lambda: events.append("import"))
    panel.encrypt_requested.connect(lambda: events.append("encrypt"))
    panel.template_requested.connect(lambda: events.append("template"))

    assert [
        panel.import_btn.text(),
        panel.encrypt_excel_btn.text(),
        panel.template_btn.text(),
    ] == ["导入 Excel 文件", "加密 Excel 认证信息", "下载 Excel 模板"]
    assert all(
        button.objectName() == "btn_outline"
        for button in (
            panel.import_btn,
            panel.encrypt_excel_btn,
            panel.template_btn,
        )
    )

    panel.import_btn.click()
    panel.encrypt_excel_btn.click()
    panel.template_btn.click()
    assert events == ["import", "encrypt", "template"]
    assert app is not None
