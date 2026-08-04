from services.log_formatting import (
    format_info_html,
    format_log_html,
    log_message_color,
    normalize_log_addresses,
)


def test_log_formatting_escapes_text_and_preserves_color_rules():
    assert format_info_html("<ready>", "10:20:30") == (
        '<span style="color:#58A6FF;">[10:20:30] &lt;ready&gt;</span>'
    )
    assert log_message_color("执行成功") == "#3FB950"
    assert log_message_color("connection failed") == "#F85149"
    assert log_message_color("警告") == "#D29922"
    assert log_message_color("连接中") == "#C9D1D9"


def test_log_formatting_normalizes_ipv6_and_escapes_message():
    text = normalize_log_addresses("SW1 [2026:0:0:0:0:0:0:30] <ok>")
    assert "[2026:0:0:0:0:0:0:30]" in text
    assert "[[" not in text
    rendered = format_log_html(text, "01:02:03")
    assert "[01:02:03]" in rendered
    assert "&lt;ok&gt;" in rendered
