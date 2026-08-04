from ui.theme import APP_STYLE, Theme


def test_theme_tokens_keep_expected_aomt_palette():
    assert Theme.PRIMARY == "#0369A1"
    assert Theme.ACCENT == "#0F9F8F"
    assert Theme.BG_MAIN == "#EEF3F4"
    assert Theme.TEXT_PRIMARY == "#18343C"
    assert Theme.ERROR == "#D95445"


def test_app_style_is_owned_by_theme_module():
    assert "QMenuBar" in APP_STYLE
    assert "font-size: 18px" in APP_STYLE
