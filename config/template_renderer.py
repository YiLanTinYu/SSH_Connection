"""Validation and rendering for parameterized configuration templates."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
INTERFACE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9./-]{1,63}$")
HOST_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,253}$")


class TemplateValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RenderedTemplate:
    commands: tuple[str, ...]
    preview: str
    manual_steps: tuple[str, ...]
    contains_secrets: bool
    secret_values: tuple[str, ...]


def render_template(template: dict, values: dict) -> RenderedTemplate:
    path = Path(template.get("path", ""))
    if not path.is_file():
        raise TemplateValidationError("模板文件不存在")

    normalized = {}
    sensitive_values = []
    for field in template.get("parameters", ()):
        name = field["name"]
        value = str(values.get(name, field.get("default", ""))).strip()
        normalized[name] = validate_template_value(field, value)
        if field.get("sensitive"):
            sensitive_values.append(normalized[name])

    content = path.read_text(encoding="utf-8-sig")
    required_tokens = set(TOKEN_RE.findall(content))
    missing = sorted(required_tokens - set(normalized))
    if missing:
        raise TemplateValidationError("模板缺少参数定义：" + ", ".join(missing))

    rendered = TOKEN_RE.sub(lambda match: normalized[match.group(1)], content)
    unresolved = TOKEN_RE.findall(rendered)
    if unresolved:
        raise TemplateValidationError("存在未替换参数：" + ", ".join(unresolved))

    commands = []
    manual_steps = []
    for raw_line in rendered.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# MANUAL:"):
            manual_steps.append(line.partition(":")[2].strip())
            continue
        if line.startswith("#"):
            continue
        commands.append(line)
    if not commands:
        raise TemplateValidationError("模板没有可执行命令")

    preview = "\n".join(commands)
    for secret in sorted(filter(None, sensitive_values), key=len, reverse=True):
        preview = preview.replace(secret, "********")
    return RenderedTemplate(
        tuple(commands),
        preview,
        tuple(manual_steps),
        bool(sensitive_values),
        tuple(filter(None, sensitive_values)),
    )


def validate_template_value(field: dict, value: str) -> str:
    label = field.get("label", field.get("name", "参数"))
    if field.get("required", True) and not value:
        raise TemplateValidationError(f"{label}不能为空")
    if any(ord(char) < 32 for char in value):
        raise TemplateValidationError(f"{label}不能包含换行或控制字符")

    kind = field.get("kind", "text")
    if kind == "identifier" and not SAFE_NAME_RE.fullmatch(value):
        raise TemplateValidationError(
            f"{label}只能包含字母、数字、点、下划线和连字符，长度不超过32"
        )
    if kind == "ipv4":
        try:
            value = str(ipaddress.IPv4Address(value))
        except ipaddress.AddressValueError as exc:
            raise TemplateValidationError(f"{label}不是有效 IPv4 地址") from exc
    if kind == "netmask":
        try:
            network = ipaddress.IPv4Network(f"0.0.0.0/{value}")
        except (ipaddress.NetmaskValueError, ValueError) as exc:
            raise TemplateValidationError(f"{label}不是连续的 IPv4 子网掩码") from exc
        value = str(network.netmask)
    if kind == "vlan":
        number = _bounded_int(label, value, 1, 4094)
        value = str(number)
    if kind == "minutes":
        number = _bounded_int(label, value, 1, 1440)
        value = str(number)
    if kind == "interface" and not INTERFACE_RE.fullmatch(value):
        raise TemplateValidationError(f"{label}不是有效的接口名称")
    if kind == "host":
        if not HOST_RE.fullmatch(value):
            raise TemplateValidationError(f"{label}不是有效的 IP 地址或主机名")
    if kind == "vlan_list":
        value = _normalize_vlan_list(label, value)
    if kind == "password":
        _validate_password(label, value)
    if kind == "description":
        if len(value) > 80 or value.startswith(("#", "?")):
            raise TemplateValidationError(f"{label}长度不能超过80，且不能以 # 或 ? 开头")
    return value


def _bounded_int(label: str, value: str, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise TemplateValidationError(f"{label}必须是整数") from exc
    if not minimum <= number <= maximum:
        raise TemplateValidationError(f"{label}范围应为 {minimum} 到 {maximum}")
    return number


def _normalize_vlan_list(label: str, value: str) -> str:
    tokens = value.replace(",", " ").split()
    if not tokens:
        raise TemplateValidationError(f"{label}不能为空")
    expect_number = True
    normalized = []
    for token in tokens:
        lower = token.lower()
        if expect_number:
            normalized.append(str(_bounded_int(label, token, 1, 4094)))
            expect_number = False
        elif lower == "to":
            normalized.append("to")
            expect_number = True
        else:
            normalized.append(str(_bounded_int(label, token, 1, 4094)))
    if expect_number:
        raise TemplateValidationError(f"{label}中的 to 后缺少 VLAN ID")
    return " ".join(normalized)


def _validate_password(label: str, value: str) -> None:
    if not 8 <= len(value) <= 63:
        raise TemplateValidationError(f"{label}长度应为8到63位")
    if any(char.isspace() for char in value):
        raise TemplateValidationError(f"{label}不能包含空白字符")
    if not re.fullmatch(r"[A-Za-z0-9!@#$%^&*()_+=.,:;-]+", value):
        raise TemplateValidationError(
            f"{label}包含不适合交换机非交互命令的字符"
        )
    categories = sum(
        (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
    )
    if categories < 3:
        raise TemplateValidationError(
            f"{label}至少包含大写字母、小写字母、数字、特殊字符中的三类"
        )
