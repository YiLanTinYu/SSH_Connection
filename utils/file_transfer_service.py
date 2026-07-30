#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Embedded FTP and TFTP services used by the maintenance tools."""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


EventCallback = Callable[[str], None]


class TransferServiceError(RuntimeError):
    """Raised when a transfer service cannot be configured or started."""


def available_transfer_backends():
    """Return backend availability without importing optional packages eagerly."""
    result = {}
    try:
        import pyftpdlib  # noqa: F401

        result["ftp"] = True
    except ImportError:
        result["ftp"] = False
    try:
        import partftpy  # noqa: F401

        result["tftp"] = True
    except ImportError:
        result["tftp"] = False
    return result


def discover_local_addresses():
    """Return stable, non-loopback local addresses suitable for binding."""
    addresses = set()
    try:
        candidates = socket.getaddrinfo(
            socket.gethostname(),
            None,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
    except socket.gaierror:
        candidates = []

    for family, _socktype, _proto, _canonname, sockaddr in candidates:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        value = str(sockaddr[0]).split("%", 1)[0]
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if address.is_loopback or address.is_unspecified or address.is_link_local:
            continue
        addresses.add(str(address))

    return sorted(
        addresses,
        key=lambda value: (
            ipaddress.ip_address(value).version,
            int(ipaddress.ip_address(value)),
        ),
    )


def normalize_shared_directory(path):
    root = Path(path).expanduser().resolve()
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise TransferServiceError(f"共享路径不是文件夹：{root}")
    return str(root)


def _relative_display(path, root):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except (OSError, ValueError):
        return os.path.basename(str(path))


@dataclass(frozen=True)
class FTPServiceConfig:
    root: str
    bind_host: str = "0.0.0.0"
    port: int = 21
    username: str = "aomt"
    password: str = ""
    allow_upload: bool = False
    passive_port_start: int = 50000
    passive_port_end: int = 50020

    def validate(self):
        root = normalize_shared_directory(self.root)
        if not self.username.strip():
            raise TransferServiceError("FTP 用户名不能为空")
        if not self.password:
            raise TransferServiceError("FTP 密码不能为空")
        if not 0 <= int(self.port) <= 65535:
            raise TransferServiceError("FTP 端口必须在 0～65535 之间")
        start = int(self.passive_port_start)
        end = int(self.passive_port_end)
        if not (1 <= start <= end <= 65535):
            raise TransferServiceError("FTP 被动端口范围无效")
        return FTPServiceConfig(
            root=root,
            bind_host=self.bind_host.strip() or "0.0.0.0",
            port=int(self.port),
            username=self.username.strip(),
            password=self.password,
            allow_upload=bool(self.allow_upload),
            passive_port_start=start,
            passive_port_end=end,
        )


@dataclass(frozen=True)
class TFTPServiceConfig:
    root: str
    bind_host: str = "0.0.0.0"
    port: int = 69
    allow_upload: bool = False

    def validate(self):
        root = normalize_shared_directory(self.root)
        if not 0 <= int(self.port) <= 65535:
            raise TransferServiceError("TFTP 端口必须在 0～65535 之间")
        return TFTPServiceConfig(
            root=root,
            bind_host=self.bind_host.strip() or "0.0.0.0",
            port=int(self.port),
            allow_upload=bool(self.allow_upload),
        )


class FTPTransferService:
    def __init__(
        self,
        config: FTPServiceConfig,
        event_callback: Optional[EventCallback] = None,
    ):
        self.config = config.validate()
        self.event_callback = event_callback or (lambda _message: None)
        self.bound_host = ""
        self.bound_port = 0
        self._server = None
        self._thread = None
        self._running = threading.Event()

    @property
    def is_running(self):
        return self._running.is_set()

    def _emit(self, message):
        self.event_callback(str(message))

    def start(self):
        if self.is_running:
            return
        try:
            from pyftpdlib.authorizers import DummyAuthorizer
            from pyftpdlib.handlers import FTPHandler
            from pyftpdlib.servers import FTPServer
        except ImportError as exc:
            raise TransferServiceError(
                "缺少 FTP 组件 pyftpdlib，请重新安装项目依赖"
            ) from exc

        service = self
        config = self.config
        authorizer = DummyAuthorizer()
        permissions = "elr"
        if config.allow_upload:
            permissions += "aw"
        authorizer.add_user(
            config.username,
            config.password,
            config.root,
            perm=permissions,
        )

        class AOMTFTPHandler(FTPHandler):
            def on_connect(self):
                service._emit(
                    f"FTP 客户端已连接：{self.remote_ip}:{self.remote_port}"
                )

            def on_disconnect(self):
                service._emit(f"FTP 客户端已断开：{self.remote_ip}")

            def on_login(self, username):
                service._emit(
                    f"FTP 登录成功：{self.remote_ip}，用户 {username}"
                )

            def on_login_failed(self, username, password):
                service._emit(
                    f"FTP 登录失败：{self.remote_ip}，用户 {username}"
                )

            def on_file_sent(self, file):
                name = _relative_display(file, config.root)
                service._emit(f"FTP 下载完成：{name} → {self.remote_ip}")

            def on_file_received(self, file):
                name = _relative_display(file, config.root)
                service._emit(f"FTP 上传完成：{self.remote_ip} → {name}")

            def on_incomplete_file_sent(self, file):
                name = _relative_display(file, config.root)
                service._emit(f"FTP 下载中断：{name} → {self.remote_ip}")

            def on_incomplete_file_received(self, file):
                name = _relative_display(file, config.root)
                service._emit(f"FTP 上传中断：{self.remote_ip} → {name}")

        AOMTFTPHandler.authorizer = authorizer
        AOMTFTPHandler.banner = "AOMT FTP service ready"
        AOMTFTPHandler.passive_ports = range(
            config.passive_port_start,
            config.passive_port_end + 1,
        )

        try:
            self._server = FTPServer(
                (config.bind_host, config.port),
                AOMTFTPHandler,
            )
        except OSError as exc:
            raise TransferServiceError(
                f"FTP 端口 {config.bind_host}:{config.port} 无法监听：{exc}"
            ) from exc

        address = self._server.socket.getsockname()
        self.bound_host = str(address[0])
        self.bound_port = int(address[1])
        self._thread = threading.Thread(
            target=self._serve,
            name="AOMT-FTP-Server",
            daemon=True,
        )
        self._running.set()
        self._thread.start()
        mode = "允许上传" if config.allow_upload else "只读下载"
        self._emit(
            f"FTP 服务已启动：{self.bound_host}:{self.bound_port}，{mode}"
        )

    def _serve(self):
        try:
            self._server.serve_forever(
                timeout=0.2,
                blocking=True,
                handle_exit=False,
            )
        except Exception as exc:
            if self._running.is_set():
                self._emit(f"FTP 服务异常：{exc}")
        finally:
            self._running.clear()

    def stop(self):
        server = self._server
        self._running.clear()
        if server is not None:
            try:
                server.close_all()
            except OSError:
                pass
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)
        self._server = None
        self._thread = None
        self._emit("FTP 服务已停止")


class _PartFTPyLogHandler(logging.Handler):
    def __init__(self, callback, root):
        super().__init__(logging.INFO)
        self.callback = callback
        self.root = root

    def emit(self, record):
        message = record.getMessage()
        translated = self._translate(message)
        if translated:
            self.callback(translated)

    def _translate(self, message):
        match = re.search(r"Opening file (.+) for reading", message)
        if match:
            name = _relative_display(match.group(1), self.root)
            return f"TFTP 开始下载：{name}"
        match = re.search(r"Opening file (.+) for writing", message)
        if match:
            name = _relative_display(match.group(1), self.root)
            return f"TFTP 开始上传：{name}"
        match = re.search(r"(\S+) done: (.+)", message)
        if match:
            return f"TFTP 传输完成：客户端 {match.group(1)}，{match.group(2)}"
        if "File not found:" in message:
            return "TFTP 文件不存在：" + message.split("File not found:", 1)[1].strip()
        if record_level_is_warning(message):
            return f"TFTP 提示：{message}"
        return ""


def record_level_is_warning(message):
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in ("error", "failed", "timeout", "denied", "not permitted")
    )


class TFTPTransferService:
    def __init__(
        self,
        config: TFTPServiceConfig,
        event_callback: Optional[EventCallback] = None,
    ):
        self.config = config.validate()
        self.event_callback = event_callback or (lambda _message: None)
        self.bound_host = ""
        self.bound_port = 0
        self._server = None
        self._thread = None
        self._error = None
        self._logger = logging.getLogger("partftpy")
        self._log_handler = _PartFTPyLogHandler(
            self.event_callback,
            self.config.root,
        )

    @property
    def is_running(self):
        return bool(
            self._server is not None
            and getattr(self._server, "is_running", None)
            and self._server.is_running.is_set()
        )

    def _emit(self, message):
        self.event_callback(str(message))

    def _open_upload(self, path, _context):
        if not self.config.allow_upload:
            self._emit("TFTP 上传被拒绝：当前服务为只读模式")
            return None
        root = Path(self.config.root).resolve()
        target = Path(path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            self._emit("TFTP 上传被拒绝：目标路径超出共享目录")
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        self._emit(f"TFTP 开始上传：{_relative_display(target, root)}")
        return open(target, "wb")

    def start(self):
        if self.is_running:
            return
        try:
            from partftpy.TftpServer import TftpServer
        except ImportError as exc:
            raise TransferServiceError(
                "缺少 TFTP 组件 partftpy，请重新安装项目依赖"
            ) from exc

        config = self.config
        upload_open = self._open_upload if config.allow_upload else (
            lambda _path, _context: None
        )
        try:
            family = ipaddress.ip_address(config.bind_host).version
        except ValueError:
            family = 4
        address_family = socket.AF_INET6 if family == 6 else socket.AF_INET
        self._server = TftpServer(
            config.root,
            upload_open=upload_open,
        )
        self._error = None
        self._logger.addHandler(self._log_handler)
        if self._logger.level == logging.NOTSET or self._logger.level > logging.INFO:
            self._logger.setLevel(logging.INFO)
        self._thread = threading.Thread(
            target=self._serve,
            args=(address_family,),
            name="AOMT-TFTP-Server",
            daemon=True,
        )
        self._thread.start()

        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self.is_running:
                self.bound_host = config.bind_host
                self.bound_port = int(self._server.listenport)
                mode = "允许上传" if config.allow_upload else "只读下载"
                self._emit(
                    f"TFTP 服务已启动：{self.bound_host}:{self.bound_port}，{mode}"
                )
                return
            if self._error is not None:
                break
            time.sleep(0.02)

        self.stop()
        if self._error is not None:
            raise TransferServiceError(
                f"TFTP 端口 {config.bind_host}:{config.port} 无法监听："
                f"{self._error}"
            ) from self._error
        raise TransferServiceError("TFTP 服务启动超时")

    def _serve(self, address_family):
        try:
            self._server.listen(
                self.config.bind_host,
                self.config.port,
                timeout=0.25,
                retries=3,
                af_family=address_family,
            )
        except Exception as exc:
            self._error = exc
            self._emit(f"TFTP 服务异常：{exc}")

    def stop(self):
        server = self._server
        if server is not None:
            try:
                server.stop(now=True)
            except (AttributeError, OSError):
                pass
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)
        try:
            self._logger.removeHandler(self._log_handler)
        except (ValueError, AttributeError):
            pass
        self._server = None
        self._thread = None
        self._emit("TFTP 服务已停止")
