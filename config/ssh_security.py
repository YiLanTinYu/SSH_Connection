#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""SSH authentication and Host Key policy helpers."""

import os
from pathlib import Path
from typing import Dict, Optional

import paramiko


HOST_KEY_TOFU = "tofu"
HOST_KEY_STRICT = "strict"
HOST_KEY_INSECURE = "insecure"
HOST_KEY_POLICIES = {HOST_KEY_TOFU, HOST_KEY_STRICT, HOST_KEY_INSECURE}


def get_known_hosts_path() -> str:
    """Return the per-user AOMT known-hosts file."""
    overridden = os.environ.get("AOMT_KNOWN_HOSTS_PATH", "").strip()
    if overridden:
        return os.path.abspath(os.path.expanduser(overridden))
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return os.path.join(base, "AOMT", "known_hosts")


def normalize_host_key_policy(value: str) -> str:
    policy = str(value or HOST_KEY_TOFU).strip().lower()
    aliases = {
        "首次信任": HOST_KEY_TOFU,
        "严格校验": HOST_KEY_STRICT,
        "不校验": HOST_KEY_INSECURE,
        "auto": HOST_KEY_TOFU,
        "reject": HOST_KEY_STRICT,
    }
    policy = aliases.get(policy, policy)
    return policy if policy in HOST_KEY_POLICIES else HOST_KEY_TOFU


def configure_host_key_policy(
    client: paramiko.SSHClient,
    policy: str,
    known_hosts_path: Optional[str] = None,
) -> str:
    """Configure system and AOMT Host Key stores on a Paramiko client."""
    normalized = normalize_host_key_policy(policy)
    path = known_hosts_path or get_known_hosts_path()
    if normalized != HOST_KEY_INSECURE:
        client.load_system_host_keys()
        if os.path.isfile(path):
            client.load_host_keys(path)

    if normalized == HOST_KEY_STRICT:
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return path


def persist_host_keys(
    client: paramiko.SSHClient,
    policy: str,
    known_hosts_path: Optional[str] = None,
) -> None:
    """Persist keys learned in TOFU mode; strict/insecure modes do not write."""
    if normalize_host_key_policy(policy) != HOST_KEY_TOFU:
        return
    path = known_hosts_path or get_known_hosts_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    client.save_host_keys(path)


def build_connect_kwargs(device, hostname: str) -> Dict:
    """Build Paramiko connect arguments without enabling implicit credentials."""
    auth_method = str(getattr(device, "auth_method", "password") or "password").lower()
    kwargs = {
        "hostname": hostname,
        "port": int(device.port),
        "username": device.username,
        "timeout": 30,
        "banner_timeout": 30,
        "auth_timeout": 30,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if auth_method == "key":
        key_path = os.path.abspath(os.path.expanduser(
            str(getattr(device, "private_key_path", "") or "").strip()
        ))
        if not key_path or not os.path.isfile(key_path):
            raise ValueError(f"SSH 私钥文件不存在: {key_path or '未填写'}")
        kwargs["key_filename"] = key_path
        passphrase = str(getattr(device, "private_key_passphrase", "") or "")
        if passphrase:
            kwargs["passphrase"] = passphrase
    else:
        password = str(getattr(device, "password", "") or "")
        if not password:
            raise ValueError("密码认证需要填写密码")
        kwargs["password"] = password
    return kwargs
