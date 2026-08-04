import json
from pathlib import Path

from services.config_templates import (
    add_user_templates,
    load_user_templates,
    read_template_text,
    remove_user_template,
    save_user_templates,
)


def test_template_store_filters_invalid_records_and_round_trips(tmp_path: Path):
    store = tmp_path / "templates.json"
    store.write_text(
        json.dumps([{"name": "有效", "path": "a.txt"}, {}, "bad"]),
        encoding="utf-8",
    )
    assert load_user_templates(str(store)) == [{"name": "有效", "path": "a.txt"}]

    save_user_templates(str(store), [{"name": "模板", "path": "b.cfg"}])
    assert load_user_templates(str(store)) == [{"name": "模板", "path": "b.cfg"}]


def test_template_add_remove_deduplicates_absolute_paths(tmp_path: Path):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.cfg"
    current = [{"name": first.name, "path": str(first)}]

    updated, added, skipped = add_user_templates(
        current,
        [str(first), str(second), str(second)],
    )

    assert added == [str(second.resolve())]
    assert len(skipped) == 2
    assert len(updated) == 2
    assert remove_user_template(updated, str(first)) == [updated[1]]


def test_read_template_text_supports_utf8_and_gbk(tmp_path: Path):
    utf8_file = tmp_path / "utf8.txt"
    gbk_file = tmp_path / "gbk.txt"
    utf8_file.write_text("display current-configuration", encoding="utf-8")
    gbk_file.write_bytes("配置模板".encode("gbk"))

    assert read_template_text(str(utf8_file)) == "display current-configuration"
    assert read_template_text(str(gbk_file)) == "配置模板"
