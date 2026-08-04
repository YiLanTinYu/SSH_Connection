from ui.main_menu import menu_action_routes


def test_menu_action_routes_ignores_separators_and_maps_handlers():
    definitions = (
        (
            "file",
            "文件",
            (
                ("file.open", "打开", "open_file"),
                None,
                ("file.exit", "退出", "close"),
            ),
        ),
    )
    assert menu_action_routes(definitions) == {
        "file.open": "open_file",
        "file.exit": "close",
    }
