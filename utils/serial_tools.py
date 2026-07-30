#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Serial-port configuration, discovery and local profile storage."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import serial
from serial.tools import list_ports


@dataclass
class SerialConfig:
    port: str
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1
    flow_control: str = "none"
    timeout: float = 0.1
    encoding: str = "utf-8"
    line_ending: str = "cr"
    dtr: bool = True
    rts: bool = True
    profile_version: int = 2

    def validate(self):
        if not str(self.port or "").strip():
            raise ValueError("请选择串口")
        if not 50 <= int(self.baudrate) <= 4_000_000:
            raise ValueError("波特率必须在 50 到 4000000 之间")
        if int(self.bytesize) not in (5, 6, 7, 8):
            raise ValueError("数据位必须是 5、6、7 或 8")
        if self.parity not in ("N", "E", "O", "M", "S"):
            raise ValueError("不支持的校验方式")
        if float(self.stopbits) not in (1, 1.5, 2):
            raise ValueError("停止位必须是 1、1.5 或 2")
        if self.flow_control not in ("none", "rtscts", "xonxoff", "dsrdtr"):
            raise ValueError("不支持的流控方式")
        "".encode(self.encoding)
        return self

    @classmethod
    def from_dict(cls, data):
        allowed = cls.__dataclass_fields__
        values = {key: value for key, value in dict(data or {}).items() if key in allowed}
        return cls(**values).validate()


def discover_serial_ports() -> List[dict]:
    ports = []
    for info in sorted(list_ports.comports(), key=lambda item: item.device.lower()):
        ports.append({
            "device": info.device,
            "description": info.description or "",
            "manufacturer": info.manufacturer or "",
            "hwid": info.hwid or "",
        })
    return ports


def open_serial_connection(config: SerialConfig):
    config.validate()
    kwargs = {
        "baudrate": int(config.baudrate),
        "bytesize": int(config.bytesize),
        "parity": config.parity,
        "stopbits": float(config.stopbits),
        "timeout": float(config.timeout),
        "write_timeout": 2,
        "rtscts": config.flow_control == "rtscts",
        "xonxoff": config.flow_control == "xonxoff",
        "dsrdtr": config.flow_control == "dsrdtr",
    }
    connection = serial.serial_for_url(config.port, **kwargs)
    try:
        connection.dtr = bool(config.dtr)
        connection.rts = bool(config.rts)
    except (AttributeError, OSError, serial.SerialException):
        pass
    return connection


def get_serial_profiles_path() -> str:
    overridden = os.environ.get("AOMT_SERIAL_PROFILES_PATH", "").strip()
    if overridden:
        return os.path.abspath(os.path.expanduser(overridden))
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return os.path.join(base, "AOMT", "serial_profiles.json")


class SerialProfileStore:
    def __init__(self, file_path: str = ""):
        self.file_path = file_path or get_serial_profiles_path()

    def load(self) -> dict:
        if not os.path.isfile(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as stream:
                payload = json.load(stream)
            if not isinstance(payload, dict):
                return {}
            profiles = {}
            for name, data in payload.items():
                try:
                    raw_config = dict(data or {})
                    if "profile_version" not in raw_config:
                        # Version 1 defaulted to CRLF, which common switch
                        # Console ports interpret as two Enter actions.
                        if raw_config.get("line_ending", "crlf") == "crlf":
                            raw_config["line_ending"] = "cr"
                        raw_config["profile_version"] = 2
                    profiles[str(name)] = asdict(
                        SerialConfig.from_dict(raw_config)
                    )
                except (TypeError, ValueError):
                    continue
            return profiles
        except (OSError, json.JSONDecodeError):
            return {}

    def save_profile(self, name: str, config: SerialConfig):
        name = str(name or "").strip()
        if not name:
            raise ValueError("配置名称不能为空")
        profiles = self.load()
        profiles[name] = asdict(config.validate())
        self._write(profiles)

    def delete_profile(self, name: str):
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
            json.dump(profiles, stream, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.file_path)


LINE_ENDINGS = {
    "none": b"",
    "cr": b"\r",
    "lf": b"\n",
    "crlf": b"\r\n",
}


def friendly_serial_error(message: str, port: str = "") -> str:
    """Translate common Windows serial-open failures into actionable text."""
    text = str(message or "").strip()
    lowered = text.lower()
    label = str(port or "所选串口").strip()
    if (
        "permissionerror" in lowered
        or "access is denied" in lowered
        or "拒绝访问" in text
        or "errno 13" in lowered
    ):
        return (
            f"无法打开 {label}：串口正被其他程序占用，或当前账号没有访问权限。"
            "请关闭 SecureCRT、其他串口工具或重复打开的 AOMT 窗口后重试。"
        )
    if (
        "filenotfounderror" in lowered
        or "cannot find" in lowered
        or "系统找不到" in text
    ):
        return f"无法打开 {label}：串口已断开或端口号发生变化，请刷新串口列表。"
    return text or f"无法打开 {label}"
