import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QMessageBox

import ui.main_window as main_window


def _create_window(monkeypatch):
    monkeypatch.setattr(main_window, "ConnectionLogger", lambda: object())
    return main_window.MainWindow()


def test_main_menu_contains_every_declared_menu_and_action(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = _create_window(monkeypatch)
    try:
        expected_menu_keys = [
            menu_key
            for menu_key, _title, _entries in window.MENU_DEFINITIONS
        ]
        expected_titles = [
            title
            for _menu_key, title, _entries in window.MENU_DEFINITIONS
        ]

        assert list(window.main_menus) == expected_menu_keys
        assert [
            action.text() for action in window.menuBar().actions()
        ] == expected_titles
        assert set(window.menu_actions) == set(
            window.menu_action_routes()
        )

        for menu_key, _title, entries in window.MENU_DEFINITIONS:
            expected_action_text = [
                entry[1] for entry in entries if entry is not None
            ]
            actual_action_text = [
                action.text()
                for action in window.main_menus[menu_key].actions()
                if not action.isSeparator()
            ]
            assert actual_action_text == expected_action_text
        app.processEvents()
    finally:
        window.close()


def test_main_window_title_does_not_repeat_version(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = _create_window(monkeypatch)
    try:
        assert window.windowTitle() == main_window.APP_SHORT_NAME
        assert main_window.APP_VERSION not in window.windowTitle()
        app.processEvents()
    finally:
        window.close()


def test_main_menu_uses_readable_font_size(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = _create_window(monkeypatch)
    try:
        style = window.styleSheet()
        assert re.search(
            r"QMenuBar\s*\{[^}]*font-size:\s*18px",
            style,
            re.DOTALL,
        )
        assert re.search(
            r"QMenu\s*\{[^}]*font-size:\s*18px",
            style,
            re.DOTALL,
        )
        app.processEvents()
    finally:
        window.close()


def test_every_main_menu_action_routes_to_its_declared_handler(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = _create_window(monkeypatch)
    calls = []
    try:
        routes = window.menu_action_routes()
        for handler_name in set(routes.values()):
            monkeypatch.setattr(
                window,
                handler_name,
                lambda name=handler_name: calls.append(name),
            )

        for action_key, handler_name in routes.items():
            calls.clear()
            window.menu_actions[action_key].trigger()
            app.processEvents()
            assert calls == [handler_name], action_key
    finally:
        window.close()


def test_view_menu_switches_pages_and_restores_layout(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = _create_window(monkeypatch)
    try:
        page_actions = {
            "view.devices": "devices",
            "view.tasks": "tasks",
            "view.tools": "tools",
            "view.templates": "templates",
        }
        for action_key, page_key in page_actions.items():
            window.menu_actions[action_key].trigger()
            app.processEvents()
            assert window._left_panel.current_page_key() == page_key
            assert window._left_panel.is_expanded()

        window.menu_actions["view.toggle_sidebar"].trigger()
        assert not window._left_panel.is_expanded()
        window.menu_actions["view.toggle_sidebar"].trigger()
        assert window._left_panel.is_expanded()

        window.menu_actions["view.restore_layout"].trigger()
        assert not window._left_panel.is_expanded()
        assert window._main_splitter.sizes()[0] <= (
            main_window.CollapsibleSidebar.COLLAPSED_WIDTH + 2
        )
    finally:
        window.close()


def test_add_device_menu_focuses_device_form(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = _create_window(monkeypatch)
    try:
        window.show()
        app.processEvents()
        window.menu_actions["view.tasks"].trigger()
        window.menu_actions["device.add"].trigger()
        app.processEvents()

        assert window._left_panel.current_page_key() == "devices"
        assert window._left_panel.is_expanded()
        assert window.name_input.hasFocus()
    finally:
        window.close()


def test_help_menu_opens_readme_and_about_dialog(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = _create_window(monkeypatch)
    opened_urls = []
    about_calls = []
    try:
        monkeypatch.setattr(
            main_window.QDesktopServices,
            "openUrl",
            lambda url: opened_urls.append(url) or True,
        )
        monkeypatch.setattr(
            QMessageBox,
            "about",
            lambda *args: about_calls.append(args),
        )

        window.menu_actions["help.guide"].trigger()
        window.menu_actions["help.about"].trigger()
        app.processEvents()

        assert len(opened_urls) == 1
        assert isinstance(opened_urls[0], QUrl)
        assert opened_urls[0].isLocalFile()
        assert opened_urls[0].toLocalFile().endswith("USER_GUIDE.md")
        assert len(about_calls) == 1
        assert about_calls[0][1] == "关于 AOMT"
        assert f"v{main_window.APP_VERSION}" in about_calls[0][2]
    finally:
        window.close()
