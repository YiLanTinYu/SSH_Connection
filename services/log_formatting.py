"""Format main-window log messages without depending on Qt widgets."""

from __future__ import annotations

import html
import re
from datetime import datetime

from utils.ipv6_utils import IPv6Utils


_BRACKETED_IP = re.compile(r"\[([0-9a-fA-F:.]+)\]")


def current_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def normalize_log_addresses(text: str) -> str:
    def replace(match):
        display = IPv6Utils.format_ipv6_for_display(match.group(1))
        if display.startswith("[") and display.endswith("]"):
            return display
        return f"[{display}]"

    return _BRACKETED_IP.sub(replace, text)


def log_message_color(text: str) -> str:
    lowered = text.lower()
    if "成功" in text or "success" in lowered or text.startswith("✔"):
        return "#3FB950"
    if (
        "失败" in text
        or "fail" in lowered
        or "error" in lowered
        or text.startswith("✘")
    ):
        return "#F85149"
    if "警告" in text or "warn" in lowered or "[L2探测]" in text:
        return "#D29922"
    return "#C9D1D9"


def format_info_html(text: str, timestamp: str | None = None) -> str:
    stamp = timestamp or current_timestamp()
    return f'<span style="color:#58A6FF;">[{stamp}] {html.escape(text)}</span>'


def format_log_html(text: str, timestamp: str | None = None) -> str:
    normalized = normalize_log_addresses(text)
    stamp = timestamp or current_timestamp()
    color = log_message_color(normalized)
    return (
        f'<span style="color:{color};">'
        f'[{stamp}] {html.escape(normalized)}</span>'
    )
