"""Persistence and file handling for user configuration templates."""

import json
import os


def load_user_templates(store_path: str) -> list:
    if not os.path.exists(store_path):
        return []
    with open(store_path, "r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, list):
        return []
    return [
        item
        for item in data
        if isinstance(item, dict) and item.get("path")
    ]


def save_user_templates(store_path: str, templates) -> None:
    os.makedirs(os.path.dirname(store_path), exist_ok=True)
    with open(store_path, "w", encoding="utf-8") as stream:
        json.dump(list(templates), stream, ensure_ascii=False, indent=2)


def add_user_templates(templates, file_paths) -> tuple:
    updated = [dict(item) for item in templates]
    existing = {
        os.path.normcase(os.path.abspath(item.get("path", "")))
        for item in updated
    }
    added = []
    skipped = []
    for file_path in file_paths:
        absolute = os.path.abspath(file_path)
        key = os.path.normcase(absolute)
        if key in existing:
            skipped.append(absolute)
            continue
        updated.append({"name": os.path.basename(absolute), "path": absolute})
        existing.add(key)
        added.append(absolute)
    return updated, added, skipped


def remove_user_template(templates, file_path: str) -> list:
    target = os.path.normcase(os.path.abspath(file_path))
    return [
        dict(item)
        for item in templates
        if os.path.normcase(os.path.abspath(item.get("path", ""))) != target
    ]


def read_template_text(file_path: str) -> str:
    last_error = None
    for encoding in ("utf-8", "gbk", "gb18030"):
        try:
            with open(file_path, "r", encoding=encoding) as stream:
                return stream.read()
        except (OSError, UnicodeError) as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return ""
