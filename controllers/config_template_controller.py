"""Coordinate built-in and user configuration template state."""

from config.builtin_templates import get_builtin_templates
from services.config_templates import (
    add_user_templates,
    load_user_templates,
    read_template_text,
    remove_user_template,
    save_user_templates,
)


class ConfigTemplateController:
    def __init__(self, store_path: str, builtin_provider=get_builtin_templates):
        self.store_path = store_path
        self.builtin_provider = builtin_provider
        self.user_templates = []

    def load(self):
        self.user_templates = load_user_templates(self.store_path)
        return list(self.user_templates)

    def replace_user_templates(self, templates) -> None:
        self.user_templates = [dict(item) for item in templates]

    def save(self) -> None:
        save_user_templates(self.store_path, self.user_templates)

    def all_templates(self):
        return list(self.builtin_provider()) + [
            {**item, "builtin": False}
            for item in self.user_templates
        ]

    def add(self, file_paths):
        updated, added, skipped = add_user_templates(
            self.user_templates,
            file_paths,
        )
        self.user_templates = updated
        if added:
            self.save()
        return list(added), list(skipped)

    def remove(self, file_path: str):
        self.user_templates = remove_user_template(
            self.user_templates,
            file_path,
        )
        self.save()
        return list(self.user_templates)

    @staticmethod
    def read(file_path: str) -> str:
        return read_template_text(file_path)
