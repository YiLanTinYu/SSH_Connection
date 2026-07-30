"""Persistent user profiles for vendor-specific health checks."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


DEFAULT_PROFILE_NAME = "标准巡检"
SUPPORTED_PROFILE_BRANDS = ("h3c", "huawei")
_UNSAFE_COMMAND = re.compile(r"[\r\n\x00]|;|&&|\|\|")


def get_health_profiles_path() -> str:
    overridden = os.environ.get("AOMT_HEALTH_PROFILES_PATH", "").strip()
    if overridden:
        return os.path.abspath(os.path.expanduser(overridden))
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return os.path.join(base, "AOMT", "health_check_profiles.json")


def normalize_custom_commands(commands) -> list[str]:
    normalized = []
    for raw in commands or []:
        command = " ".join(str(raw or "").strip().split())
        if not command:
            continue
        if _UNSAFE_COMMAND.search(str(raw)):
            raise ValueError(f"自定义命令包含不允许的连接符：{command}")
        if not command.lower().startswith("display "):
            raise ValueError(f"自定义巡检仅允许 display 查询命令：{command}")
        if command not in normalized:
            normalized.append(command)
    return normalized


def normalize_profile(data: dict, valid_item_ids) -> dict:
    payload = dict(data or {})
    valid_ids = set(valid_item_ids)
    selected = []
    for item_id in payload.get("builtin_items", []):
        item_id = str(item_id or "").strip()
        if item_id in valid_ids and item_id not in selected:
            selected.append(item_id)
    raw_custom = dict(payload.get("custom_commands", {}) or {})
    custom = {
        brand: normalize_custom_commands(raw_custom.get(brand, []))
        for brand in SUPPORTED_PROFILE_BRANDS
    }
    return {
        "builtin_items": selected,
        "custom_commands": custom,
    }


class HealthProfileStore:
    def __init__(self, valid_item_ids, file_path: str = ""):
        self.valid_item_ids = tuple(valid_item_ids)
        self.file_path = file_path or get_health_profiles_path()

    def load(self) -> dict[str, dict]:
        if not os.path.isfile(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as stream:
                payload = json.load(stream)
            raw_profiles = payload.get("profiles", payload)
            if not isinstance(raw_profiles, dict):
                return {}
            profiles = {}
            for raw_name, raw_profile in raw_profiles.items():
                name = str(raw_name or "").strip()
                if not name or name == DEFAULT_PROFILE_NAME:
                    continue
                try:
                    profiles[name] = normalize_profile(
                        raw_profile, self.valid_item_ids
                    )
                except (TypeError, ValueError):
                    continue
            return profiles
        except (OSError, json.JSONDecodeError, AttributeError):
            return {}

    def save(self, name: str, profile: dict):
        name = str(name or "").strip()
        if not name:
            raise ValueError("方案名称不能为空")
        if name == DEFAULT_PROFILE_NAME:
            raise ValueError("标准巡检是内置方案，不能覆盖")
        profiles = self.load()
        profiles[name] = normalize_profile(profile, self.valid_item_ids)
        self._write(profiles)

    def delete(self, name: str):
        if name == DEFAULT_PROFILE_NAME:
            raise ValueError("标准巡检是内置方案，不能删除")
        profiles = self.load()
        if name in profiles:
            del profiles[name]
            self._write(profiles)

    def _write(self, profiles: dict):
        directory = os.path.dirname(self.file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temp_path = self.file_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as stream:
            json.dump(
                {"version": 1, "profiles": profiles},
                stream,
                ensure_ascii=False,
                indent=2,
            )
        os.replace(temp_path, self.file_path)
