"""Main menu construction and route mapping."""

from PyQt5.QtWidgets import QAction


def menu_action_routes(definitions) -> dict:
    routes = {}
    for _menu_key, _title, entries in definitions:
        for entry in entries:
            if entry is not None:
                action_key, _text, handler_name = entry
                routes[action_key] = handler_name
    return routes


def build_main_menu(window, definitions, dispatcher) -> tuple:
    menu_bar = window.menuBar()
    menu_bar.setNativeMenuBar(False)
    menu_bar.clear()
    menus = {}
    actions = {}

    for menu_key, title, entries in definitions:
        menu = menu_bar.addMenu(title)
        menu.setObjectName(f"main_menu_{menu_key}")
        menus[menu_key] = menu
        for entry in entries:
            if entry is None:
                menu.addSeparator()
                continue
            action_key, text, handler_name = entry
            action = QAction(text, window)
            action.setObjectName(
                "menu_action_" + action_key.replace(".", "_")
            )
            action.triggered.connect(
                lambda checked=False, name=handler_name: dispatcher(name)
            )
            menu.addAction(action)
            actions[action_key] = action
    return menus, actions
