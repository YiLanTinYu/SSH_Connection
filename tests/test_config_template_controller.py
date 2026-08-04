import json

from controllers.config_template_controller import ConfigTemplateController


def test_config_template_controller_loads_combines_and_persists(tmp_path):
    store_path = tmp_path / "operation_templates.json"
    first = tmp_path / "first.cfg"
    second = tmp_path / "second.txt"
    first.write_text("sysname SW1", encoding="utf-8")
    second.write_text("display version", encoding="utf-8")
    builtin = [{"name": "内置开局", "path": "builtin://start", "builtin": True}]
    controller = ConfigTemplateController(
        str(store_path),
        builtin_provider=lambda: builtin,
    )

    assert controller.load() == []
    added, skipped = controller.add([str(first), str(first), str(second)])
    assert added == [str(first), str(second)]
    assert skipped == [str(first)]
    assert controller.all_templates()[0] == builtin[0]
    assert len(controller.all_templates()) == 3
    assert json.loads(store_path.read_text(encoding="utf-8"))[0]["name"] == "first.cfg"

    reloaded = ConfigTemplateController(str(store_path), lambda: builtin)
    assert len(reloaded.load()) == 2
    assert reloaded.read(str(first)) == "sysname SW1"


def test_config_template_controller_removes_without_deleting_source(tmp_path):
    store_path = tmp_path / "templates.json"
    source = tmp_path / "keep.cfg"
    source.write_text("vlan 10", encoding="utf-8")
    controller = ConfigTemplateController(str(store_path), lambda: [])
    controller.add([str(source)])

    assert controller.remove(str(source)) == []
    assert source.exists()
    assert json.loads(store_path.read_text(encoding="utf-8")) == []
