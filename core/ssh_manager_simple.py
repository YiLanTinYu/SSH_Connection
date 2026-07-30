#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
SSH 连接管理器（paramiko 版）
支持 IPv4 / IPv6，兼容 Python 3.14+

优化说明（借鉴 w-sw-ssh 优秀设计）：
1. 提示符正则：移植 w-sw-ssh 的宽容正则，兼容所有主流厂商格式
2. 品牌识别：分两步 display version → show version，精确识别 H3C/Huawei/Cisco/Ruijie/TP-Link
3. 二层上联口探测：移植 w-sw-ssh uf_get_l2_uplink 三步链式查询
4. 保存配置：从 DEVICE_COMMANDS 字典获取各品牌 save 命令，消除 if-else 分散
5. 业务命令原样执行：不对用户脚本做未经验证的跨品牌改写
6. 线程调度：借鉴 w-sw-ssh 分批调度思路，用 ThreadPoolExecutor 实现更优雅的版本
"""

import paramiko
import ipaddress
import re
import threading
from typing import Dict, List, Optional, Callable
import queue
import time
from datetime import datetime
import sys
import os
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ipv6_utils import IPv6Utils, IPVersion, IPv6AddressValidator
from config.ssh_security import (
    HOST_KEY_INSECURE,
    build_connect_kwargs,
    configure_host_key_policy,
    normalize_host_key_policy,
    persist_host_keys,
)


# ──────────────────────────────────────────────────────────
# 提示符正则（借鉴 w-sw-ssh，兼容 Cisco/H3C/Huawei/Ruijie/TP-Link）
# 行末锚定，匹配 >, #, ], $, % 结尾的提示符
# ──────────────────────────────────────────────────────────
PROMPT_REGEX = re.compile(
    r'(\r|\n).?[<>\[\]a-zA-Z0-9~@*/\\_\-\(\)]+(>|%|#|\$|\]) *$'
)

# IP / MAC 地址正则（用于二层上联口探测）
RE_IPV4    = re.compile(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])')
RE_MAC_STD = re.compile(r'\s?([\da-f]{4}[.\-]){2}[\da-f]{4}\s?', re.IGNORECASE)
RE_MAC_COL = re.compile(r'\s?([\da-f]{2}:){5}[\da-f]{2}\s?',     re.IGNORECASE)
SAVE_CONFIRM_RE = re.compile(
    r'(\[y/n\]|\(y/n\)|continue\?|overwrite|confirm|are you sure)',
    re.IGNORECASE,
)


class SSHConnection:
    """SSH 连接类（单台设备）"""

    def __init__(self, device_info, logger=None, cancel_event=None):
        self.device_info    = device_info
        self.logger         = logger
        self.client         = None
        self._shell         = None          # 持久交互式 shell
        self.is_connected   = False
        self.task_success   = False
        self.brand_detected = None
        self.model_detected = None          # 设备型号（借鉴 w-sw-ssh）
        self.error_message  = None
        self.command_results: List[Dict] = []
        self.sensitive_values: List[str] = []
        self.ip_version     = IPVersion.UNKNOWN
        self.ipv6_validator = IPv6AddressValidator()
        self._print_lock    = threading.Lock()
        self.cancel_event   = cancel_event
        self.started_at     = datetime.now()
        self.finished_at    = None
        self.connection_duration_seconds = 0.0

        if hasattr(device_info, 'ip') and device_info.ip:
            self.ip_version = IPv6Utils.get_ip_version(device_info.ip)

    # ──────────────────────────────────────────────────────
    # 连接入口
    # ──────────────────────────────────────────────────────
    def connect(self) -> bool:
        """建立 SSH 连接（支持 IPv4 / IPv6）"""
        connection_started = time.monotonic()
        try:
            # 1. 验证 IP
            if hasattr(self.device_info, 'ip') and self.device_info.ip:
                is_valid, error_msg = self.ipv6_validator.validate_for_ssh(self.device_info.ip)
                if not is_valid:
                    self.error_message  = f"IP 地址验证失败: {error_msg}"
                    self.is_connected   = False
                    if self.logger:
                        self.logger.log_connection_failure(self.device_info, self.error_message)
                    return False

            # 2. 创建 SSH 客户端
            self.client = paramiko.SSHClient()
            host_key_policy = normalize_host_key_policy(
                getattr(self.device_info, 'host_key_policy', 'tofu')
            )
            known_hosts_path = configure_host_key_policy(
                self.client, host_key_policy
            )
            if self.logger and host_key_policy == HOST_KEY_INSECURE:
                self.logger.log_operation(
                    f"安全警告: {self.device_info.ip} 已关闭 SSH Host Key 校验。",
                    level='warning',
                )

            connect_address = self._get_connect_address()

            # 3. 按设备设置使用密码或私钥认证，不读取系统隐式凭据。
            connect_kwargs = build_connect_kwargs(
                self.device_info, connect_address
            )
            self.client.connect(**connect_kwargs)
            persist_host_keys(
                self.client, host_key_policy, known_hosts_path
            )
            self.is_connected = True
            self.task_success = True

            conn_type = "IPv6" if self.ip_version == IPVersion.IPv6 else "IPv4"
            if self.logger:
                self.logger.log_operation(f"使用 {conn_type} 连接到 {connect_address}")

            # 4. 建立持久 shell，等待首个提示符
            self._shell = self.client.invoke_shell(width=200, height=50)
            self._shell.settimeout(15)
            # Some VRP devices do not push a prompt until the client sends a
            # newline. Provoke it instead of waiting for the old 10 s timeout.
            self._shell.send('\n')
            self._read_until_prompt(timeout=3)

            # 5. 禁用分页（先用通用命令，识别品牌后会按品牌重发）
            self._send_no_page_generic()

            # 6. 自动识别品牌和型号（借鉴 w-sw-ssh 两步识别）
            self._detect_brand_and_model()

            # 7. 按识别品牌精确禁用分页
            self._send_no_page_by_brand()

            if self.logger:
                self.logger.log_connection_success(self.device_info)

            return True

        except paramiko.BadHostKeyException:
            self.error_message = (
                "SSH Host Key 与已保存记录不一致，连接已拒绝。"
                "请确认设备是否更换或存在中间人风险。"
            )
        except paramiko.AuthenticationException as e:
            self.error_message = f"认证失败: {e}"
        except paramiko.SSHException as e:
            self.error_message = f"SSH 连接失败: {e}"
        except Exception as e:
            self.error_message = f"连接失败: {e}"
        finally:
            self.connection_duration_seconds = round(
                max(0.0, time.monotonic() - connection_started), 3
            )

        self.is_connected = False
        self.task_success = False
        if self.logger:
            self.logger.log_connection_failure(self.device_info, self.error_message)
        return False

    # ──────────────────────────────────────────────────────
    # 内部辅助方法
    # ──────────────────────────────────────────────────────
    def _get_connect_address(self) -> str:
        """规范化 IPv6 地址"""
        if not hasattr(self.device_info, 'ip'):
            return ''
        address = self.device_info.ip
        if self.ip_version == IPVersion.IPv6:
            address = IPv6Utils.remove_ipv6_scope_id(address)
            address = IPv6Utils.normalize_ipv6(address)
        return address

    def _is_cancelled(self) -> bool:
        return bool(self.cancel_event and self.cancel_event.is_set())

    def _read_until_prompt(self, timeout: float = 10) -> str:
        """
        读取 shell 输出直到出现命令提示符或超时。

        使用 w-sw-ssh 的宽容正则，兼容所有主流厂商提示符格式：
        - Cisco:   Router>  Switch#
        - H3C:     <H3C>   [H3C]
        - Huawei:  <Huawei>
        - Ruijie:  ruijie#
        - TP-Link: Switch#
        自动处理 "---- More ----" / "--More--" 分页。
        """
        output  = ''
        deadline = time.time() + timeout
        while time.time() < deadline and not self._is_cancelled():
            try:
                if self._shell.recv_ready():
                    chunk   = self._shell.recv(8192).decode('utf-8', errors='ignore')
                    output += chunk

                    # 处理分页
                    if '---- More ----' in output or '--More--' in output:
                        self._shell.send(' ')
                        output = output.replace('---- More ----', '').replace('--More--', '')

                    # 检测提示符（使用 w-sw-ssh 正则）
                    if PROMPT_REGEX.search(output):
                        break
                    # 兼容：简单行末检测
                    stripped = output.rstrip()
                    if stripped and stripped[-1] in ('>', '#', ']', '$', '%'):
                        break
                else:
                    time.sleep(0.05)
            except Exception:
                break
        return output

    def _send_no_page_generic(self):
        """连接建立后立即发送通用禁用分页命令（品牌识别前）"""
        for cmd in ['screen-length disable', 'screen-length 0 temporary', 'terminal length 0']:
            try:
                self._shell.send(cmd + '\n')
                time.sleep(0.3)
                if self._shell.recv_ready():
                    self._shell.recv(4096)
            except Exception:
                pass

    def _send_no_page_by_brand(self):
        """品牌识别后，使用精确命令再次禁用分页"""
        if not self.brand_detected:
            return
        from config.device_commands import get_command
        cmd = get_command(self.brand_detected, 'nomore')
        if cmd:
            try:
                self._shell.send(cmd + '\n')
                time.sleep(0.3)
                if self._shell.recv_ready():
                    self._shell.recv(4096)
            except Exception:
                pass

    def _detect_brand_and_model(self):
        """
        两步品牌识别，借鉴 w-sw-ssh uf_get_vendor_model 逻辑：
        1. 尝试 display version（H3C/Huawei 语法）
        2. 若返回 Invalid/Unrecognized → 尝试 show version（Cisco/Ruijie/TP-Link）
        同时提取设备型号。
        """
        from config.device_commands import detect_brand

        # 步骤 1：H3C / Huawei 语法
        output = self.execute_command('display version')
        invalid = re.search(r'% Invalid|Unrecognized command|Error:', output or '', re.IGNORECASE)

        if not invalid and output and output.strip():
            brand = detect_brand(output)
            if brand in ('h3c', 'huawei'):
                self.brand_detected = brand
                self.model_detected = self._extract_model(output, brand)
                return

        # 步骤 2：Cisco / Ruijie / TP-Link 语法
        output2 = self.execute_command('show version')
        if output2 and output2.strip():
            brand = detect_brand(output2)
            if brand != 'unknown':
                self.brand_detected = brand
                self.model_detected = self._extract_model(output2, brand)
                return

        # 回退：使用 UI 中选择的品牌
        self.brand_detected = (
            getattr(self.device_info, 'brand', 'h3c') or 'h3c'
        ).lower()

    def _extract_model(self, version_output: str, brand: str) -> str:
        """
        从 version 输出提取设备型号（借鉴 w-sw-ssh 正则逻辑）
        """
        if not version_output:
            return ''
        patterns = {
            'h3c':    (r'^h3c.*uptime',   r' *uptime.*$'),
            'huawei': (r'^huawei.*uptime', r' *uptime.*$'),
            'cisco':  (r'^cisco.*processor', r' *\(.*$'),
            'ruijie': (r'^ruijie.*software', r' *software.*$'),
            'tplink': (r'^tp-link.*software', r' *software.*$'),
        }
        search_pat, sub_pat = patterns.get(brand, ('', ''))
        if not search_pat:
            return ''
        for line in version_output.split('\n'):
            line = line.strip()
            if re.search(search_pat, line, re.IGNORECASE):
                model = re.sub(sub_pat, '', line, flags=re.IGNORECASE)
                model = re.sub(r'^(cisco nexus|cisco|h3c|huawei|ruijie|tp-link)\s*',
                               '', model, flags=re.IGNORECASE)
                return model.strip()
        return ''

    # ──────────────────────────────────────────────────────
    # 命令执行
    # ──────────────────────────────────────────────────────
    def execute_command(self, command: str, sleep_time: float = 0.3) -> str:
        """在持久 shell 上执行单条命令并返回输出"""
        if self._is_cancelled():
            return "任务已取消"
        if not self.is_connected or not self._shell:
            return "未连接"
        command_started = time.monotonic()
        try:
            self._shell.send(command + '\n')
            time.sleep(sleep_time)
            output = self._read_until_prompt(timeout=15)

            self.command_results.append({
                'command':   self._redact(command),
                'output':    self._redact(output),
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': round(
                    time.monotonic() - command_started, 3
                ),
            })
            return output
        except Exception as e:
            error_msg = f"命令执行失败: {e}"
            self.command_results.append({
                'command':   self._redact(command),
                'output':    self._redact(error_msg),
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': round(
                    time.monotonic() - command_started, 3
                ),
            })
            return error_msg

    def execute_commands(self, commands: List[str],
                         progress_cb: Optional[Callable] = None) -> List[Dict]:
        """按脚本内容逐条原样执行命令。"""
        results = []

        for cmd in commands:
            if self._is_cancelled():
                if progress_cb:
                    progress_cb(f"  [{self.device_info.ip}] 任务已取消，停止执行后续命令")
                break
            if progress_cb:
                progress_cb(f"  [{self.device_info.ip}] 执行: {self._redact(cmd)}")

            output = self.execute_command(cmd)

            if progress_cb and output:
                preview = '\n'.join(output.strip().splitlines()[:3])
                if preview:
                    progress_cb(
                        f"  [{self.device_info.ip}] 输出:\n{self._redact(preview)}"
                    )

            results.append(
                {'command': self._redact(cmd), 'output': self._redact(output)}
            )

        return results

    def _redact(self, value: str) -> str:
        text = str(value or "")
        for secret in sorted(
            filter(None, self.sensitive_values),
            key=len,
            reverse=True,
        ):
            text = text.replace(secret, "********")
        return text

    # ──────────────────────────────────────────────────────
    # 保存配置（借鉴 w-sw-ssh uf_save）
    # ──────────────────────────────────────────────────────
    def save_config(self, progress_cb: Optional[Callable] = None) -> bool:
        """
        保存设备配置。
        各品牌 save 命令从 DEVICE_COMMANDS 字典获取，消除分散的 if-else。
        """
        from config.device_commands import get_command
        if self._is_cancelled():
            return False
        brand    = self.brand_detected or 'h3c'
        save_cmd = get_command(brand, 'save_config')
        if not save_cmd:
            return False

        if progress_cb:
            progress_cb(f"  [{self.device_info.ip}] 保存配置: {repr(save_cmd)}")

        try:
            # 支持多步命令（\r 分隔）
            normalized_cmd = save_cmd.replace('\r\n', '\r').replace('\n', '\r')
            for sub_cmd in normalized_cmd.split('\r'):
                sub_cmd = sub_cmd.strip()
                if sub_cmd:
                    if self._is_cancelled():
                        return False
                    self._shell.send(sub_cmd + '\n')
                    output = self._read_until_prompt(timeout=10)
                    if SAVE_CONFIRM_RE.search(output or ''):
                        self._shell.send('y\n')
                        self._read_until_prompt(timeout=10)
            if progress_cb:
                progress_cb(f"  [{self.device_info.ip}] 配置保存完成")
            return True
        except Exception as e:
            if progress_cb:
                progress_cb(f"  [{self.device_info.ip}] 保存配置失败: {e}")
            return False

    # ──────────────────────────────────────────────────────
    # 二层上联口探测（移植自 w-sw-ssh uf_get_l2_uplink）
    # 三步链式：默认路由 → 网关IP → ARP表 → 网关MAC → MAC表 → 上联端口
    # ──────────────────────────────────────────────────────
    def detect_l2_uplink(self,
                         progress_cb: Optional[Callable] = None) -> str:
        """
        探测二层交换机的上联口（移植自 w-sw-ssh uf_get_l2_uplink）。

        Returns:
            str: 上联口名称，如 'GigabitEthernet0/0/1'；失败返回空串
        """
        from config.device_commands import get_command, DEVICE_COMMANDS
        if self._is_cancelled():
            return ''
        brand = self.brand_detected or 'h3c'

        gw_ip_cmd     = get_command(brand, 'l2_gw_ip_cmd')
        gw_mac_cmd    = get_command(brand, 'l2_gw_mac_cmd')
        uplink_cmd    = get_command(brand, 'l2_uplink_cmd')
        mac_col_idx   = DEVICE_COMMANDS.get(brand, {}).get('l2_uplink_mac_col', 1)

        ip_addr = getattr(self.device_info, 'ip', '')

        def _log(msg):
            if progress_cb:
                progress_cb(f"  [{ip_addr}] [L2探测] {msg}")

        # ── 步骤 1：获取网关 IP ────────────────────────────
        _log(f"查询默认路由: {gw_ip_cmd}")
        out1 = self.execute_command(gw_ip_cmd)
        gw_ip = self._extract_ipv4(out1)
        if not gw_ip:
            _log("未找到网关 IP，探测终止")
            return ''
        _log(f"网关 IP: {gw_ip}")

        # ── 步骤 2：查 ARP 获得网关 MAC ───────────────────
        arp_cmd = gw_mac_cmd.replace('_GW_IP_', gw_ip)
        _log(f"查询 ARP: {arp_cmd}")
        out2  = self.execute_command(arp_cmd)
        gw_mac = self._extract_mac(out2)
        if not gw_mac:
            _log("未找到网关 MAC，探测终止")
            return ''
        _log(f"网关 MAC: {gw_mac}")

        # ── 步骤 3：查 MAC 地址表获得上联端口 ─────────────
        mac_cmd = uplink_cmd.replace('_GW_MAC_', gw_mac)
        _log(f"查询 MAC 表: {mac_cmd}")
        out3 = self.execute_command(mac_cmd)

        uplink = self._extract_uplink_port(out3, mac_cmd, gw_mac, mac_col_idx)
        if uplink:
            _log(f"上联口: {uplink}")
        else:
            _log("未能提取上联口名称")
        return uplink

    def _extract_ipv4(self, output: str) -> str:
        """从命令输出中提取第一个有效 IPv4 地址（排除 0.x.x.x）"""
        for line in output.split('\n'):
            m = RE_IPV4.search(line.strip())
            if m:
                ip = m.group(0)
                if self._is_valid_ipv4(ip):
                    return ip
        return ''

    @staticmethod
    def _is_valid_ipv4(ip: str) -> bool:
        try:
            parsed = ipaddress.ip_address(ip)
            return parsed.version == 4 and not ip.startswith('0.')
        except ValueError:
            return False

    def _extract_mac(self, output: str) -> str:
        """从命令输出中提取第一个 MAC 地址（xxxx.xxxx.xxxx 或 xx:xx:xx:xx:xx:xx）"""
        for line in output.split('\n'):
            line = line.strip()
            m = RE_MAC_STD.search(line) or RE_MAC_COL.search(line)
            if m:
                return m.group(0).strip()
        return ''

    def _extract_uplink_port(self, output: str, cmd: str,
                             mac: str, col_idx: int) -> str:
        """
        从 MAC 地址表输出中提取接口名称（借鉴 w-sw-ssh 列偏移逻辑）
        """
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 跳过命令回显行
            if cmd.split()[-1].lower() in line.lower():
                continue
            # 必须包含 MAC 地址
            if not (RE_MAC_STD.search(line) or RE_MAC_COL.search(line)):
                continue
            parts = line.split()
            if len(parts) > col_idx:
                return parts[col_idx]
        return ''

    # ──────────────────────────────────────────────────────
    # 断开连接
    # ──────────────────────────────────────────────────────
    def disconnect(self):
        """断开并清理资源"""
        if self._shell:
            try:
                self._shell.close()
            except Exception:
                pass
            self._shell = None
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        self.is_connected = False

    def get_connection_info(self) -> Dict:
        """获取连接结果字典"""
        finished_at = self.finished_at or datetime.now()
        total_duration = max(
            0.0, (finished_at - self.started_at).total_seconds()
        )
        connection_duration = min(
            total_duration,
            max(0.0, float(self.connection_duration_seconds or 0.0)),
        )
        return {
            'device_info':    self.device_info.to_dict(include_secrets=False),
            'is_connected':   self.task_success,
            'task_success':   self.task_success,
            'ssh_active':     self.is_connected,
            'brand_detected': self.brand_detected,
            'model_detected': self.model_detected,
            'error_message':  self.error_message,
            'command_results': self.command_results,
            'started_at': self.started_at.isoformat(timespec='seconds'),
            'finished_at': finished_at.isoformat(timespec='seconds'),
            'duration_seconds': round(total_duration, 3),
            'connection_duration_seconds': round(connection_duration, 3),
            'operation_duration_seconds': round(
                max(0.0, total_duration - connection_duration), 3
            ),
            'ip_version':     self.ip_version.value if self.ip_version else 0,
            'ip_version_name': (
                'IPv6' if self.ip_version == IPVersion.IPv6
                else 'IPv4' if self.ip_version == IPVersion.IPv4
                else 'Unknown'
            ),
        }

    def mark_finished(self):
        if self.finished_at is None:
            self.finished_at = datetime.now()


class SSHManager:
    """
    SSH 连接管理器

    线程调度优化（借鉴 w-sw-ssh 分批模型 + ThreadPoolExecutor）：
    - 原 w-sw-ssh：手工 start/join 批次，最后一批的慢设备会阻塞整批
    - 本版本：ThreadPoolExecutor + 动态补充任务，任一设备完成即释放线程槽位
    """

    def __init__(self, max_connections: int = 5, logger=None):
        self.max_connections = max_connections
        self.logger          = logger
        self.connections:   List[SSHConnection] = []
        self.is_running     = False
        self.progress_callback: Optional[Callable] = None
        # 建议2：逐设备完成回调（每台设备处理完立即调用，而非等全部完成）
        self.device_done_callback: Optional[Callable] = None
        self.command_file:  Optional[str] = None
        self.command_directory: Optional[str] = None
        self.command_lines: Optional[List[str]] = None
        self.command_label: str = ""
        self.required_brand: str = ""
        self.sensitive_values: List[str] = []
        # 扩展选项（对应 w-sw-ssh --save 和 --l2_sw）
        self.save_after_exec   = False
        self.detect_l2_uplink  = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._active_connections = set()

    def _load_commands(self) -> List[str]:
        """
        加载命令文件（优先自定义文件，其次默认 SSH_command.txt）。
        每行一条命令，# 开头为注释，空行忽略。
        """
        if self.command_lines is not None:
            return list(self.command_lines)
        if self.command_file and os.path.isfile(self.command_file):
            file_path = self.command_file
        else:
            root_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(root_dir, 'SSH_command.txt')

        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                commands = [
                    l.strip() for l in lines
                    if l.strip() and not l.strip().startswith('#')
                ]
                if commands:
                    return commands
            except Exception:
                pass

        return ['display version']

    @staticmethod
    def _safe_script_stem(value: str) -> str:
        """Convert a device value to a Windows-safe script filename stem."""
        return re.sub(r'[<>:"/\\|?*]+', '_', str(value or '').strip()).strip(' .')

    def resolve_command_file(self, device_info) -> Optional[str]:
        """Resolve a per-device script only by the exact device name."""
        if self.command_lines is not None:
            return self.command_label or "内存配置模板"
        if not self.command_directory:
            if self.command_file and os.path.isfile(self.command_file):
                return self.command_file
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_file = os.path.join(root_dir, 'SSH_command.txt')
            return default_file if os.path.isfile(default_file) else None

        script_dir = os.path.abspath(self.command_directory)
        if not os.path.isdir(script_dir):
            return None

        stem = self._safe_script_stem(getattr(device_info, 'name', ''))
        if not stem:
            return None
        candidate = f'{stem}.txt'

        try:
            files = {name.lower(): name for name in os.listdir(script_dir)}
        except OSError:
            return None
        actual_name = files.get(candidate.lower())
        if actual_name:
            path = os.path.join(script_dir, actual_name)
            if os.path.isfile(path):
                return path
        return None

    def _load_commands_for_device(self, device_info) -> tuple:
        if self.command_lines is not None:
            return list(self.command_lines), self.command_label or "内存配置模板"
        file_path = self.resolve_command_file(device_info)
        if not file_path:
            return [], None
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                commands = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            return commands, file_path
        except (OSError, UnicodeError) as e:
            self._notify(f"  [{device_info.ip}] 读取脚本失败: {e}")
            return [], file_path

    def set_progress_callback(self, callback: Callable):
        self.progress_callback = callback

    def set_device_done_callback(self, callback: Callable):
        """建议2：注册逐设备完成回调，每台设备处理完毕后立即在工作线程调用"""
        self.device_done_callback = callback

    def _notify(self, msg: str):
        """线程安全地发送进度通知"""
        if self.progress_callback:
            self.progress_callback(msg)

    def add_device(self, device_info):
        pass  # 设备通过 start_connections 直接传入

    def add_devices(self, device_infos: List):
        self._device_infos = list(device_infos)

    def _emit_device_done(self, result_info: Dict):
        if self.device_done_callback:
            try:
                self.device_done_callback(result_info)
            except Exception as e:
                if self.logger:
                    self.logger.log_operation(f"设备完成回调失败: {e}", level='error')

    def _record_cancelled_device(self, device_info, reason: str = "任务已取消"):
        connection = SSHConnection(device_info, self.logger, self._stop_event)
        connection.sensitive_values = list(self.sensitive_values)
        connection.error_message = reason
        connection.task_success = False
        connection.mark_finished()
        result_info = connection.get_connection_info()
        with self._lock:
            self.connections.append(connection)
        self._emit_device_done(result_info)
        return connection

    def _process_device_cancellable(self, device_info) -> SSHConnection:
        """Process one device with cancellation and visible error reporting."""
        connection = SSHConnection(device_info, self.logger, self._stop_event)
        connection.sensitive_values = list(self.sensitive_values)
        with self._lock:
            self._active_connections.add(connection)

        self._notify(f"正在连接 {device_info.ip}...")

        try:
            if self._stop_event.is_set():
                connection.error_message = "任务已取消"
                self._notify(f"  [{device_info.ip}] 任务已取消，跳过连接")
            else:
                success = connection.connect()

                if success:
                    brand = connection.brand_detected or device_info.brand or 'unknown'
                    model = connection.model_detected or ''
                    desc = f"{brand}  {model}".strip() if model else brand
                    self._notify(f"✔ {device_info.ip} 连接成功  (品牌: {desc})")

                    if self.required_brand and brand != self.required_brand:
                        connection.task_success = False
                        connection.error_message = (
                            f"模板仅适用于 {self.required_brand}，"
                            f"实际检测品牌为 {brand}"
                        )
                        self._notify(
                            f"  [{device_info.ip}] {connection.error_message}，"
                            "已阻止命令下发"
                        )
                        return connection

                    commands, command_path = self._load_commands_for_device(device_info)
                    if not commands:
                        connection.task_success = False
                        connection.error_message = "未找到可用脚本或脚本内容为空"
                        self._notify(f"  [{device_info.ip}] 未找到可用脚本或脚本内容为空，已跳过")
                        return connection
                    self._notify(f"  [{device_info.ip}] 使用脚本: {os.path.basename(command_path)}")
                    self._notify(f"  [{device_info.ip}] 开始执行命令，共 {len(commands)} 条...")
                    connection.execute_commands(commands, progress_cb=self.progress_callback)
                    if not self._stop_event.is_set():
                        self._notify(f"  [{device_info.ip}] 全部命令执行完毕")

                    if self.save_after_exec and not self._stop_event.is_set():
                        connection.save_config(progress_cb=self.progress_callback)

                    if self.detect_l2_uplink and not self._stop_event.is_set():
                        uplink = connection.detect_l2_uplink(progress_cb=self.progress_callback)
                        if uplink:
                            self._notify(f"  [{device_info.ip}] 上联口: {uplink}")
                else:
                    self._notify(f"✘ {device_info.ip} 连接失败: {connection.error_message}")
        except Exception as e:
            connection.task_success = False
            connection.error_message = f"处理失败: {e}"
            self._notify(f"✘ {device_info.ip} 处理失败: {e}")
            if self.logger:
                self.logger.log_operation(f"{device_info.ip} 处理失败: {e}", level='error')
        finally:
            connection.mark_finished()
            result_info = connection.get_connection_info()
            connection.disconnect()
            with self._lock:
                self._active_connections.discard(connection)
                self.connections.append(connection)
            self._emit_device_done(result_info)

        return connection

    # ──────────────────────────────────────────────────────
    # 单设备处理逻辑（由线程池并发调用）
    # ──────────────────────────────────────────────────────
    def _process_device(self, device_info) -> SSHConnection:
        """连接单台设备并执行所有任务"""
        connection = SSHConnection(device_info, self.logger)
        connection.sensitive_values = list(self.sensitive_values)
        self._notify(f"正在连接 {device_info.ip}...")

        success = connection.connect()

        if success:
            brand = connection.brand_detected or device_info.brand or 'unknown'
            model = connection.model_detected or ''
            desc  = f"{brand}  {model}".strip() if model else brand
            self._notify(f"✔ {device_info.ip} 连接成功  (品牌: {desc})")

            if self.required_brand and brand != self.required_brand:
                connection.task_success = False
                connection.error_message = (
                    f"模板仅适用于 {self.required_brand}，实际检测品牌为 {brand}"
                )
                self._notify(
                    f"  [{device_info.ip}] {connection.error_message}，已阻止命令下发"
                )
                connection.mark_finished()
                result_info = connection.get_connection_info()
                connection.disconnect()
                with self._lock:
                    self.connections.append(connection)
                self._emit_device_done(result_info)
                return connection

            # 业务命令严格按脚本原文执行
            commands, command_path = self._load_commands_for_device(device_info)
            if command_path:
                self._notify(f"  [{device_info.ip}] 使用脚本: {os.path.basename(command_path)}")
            self._notify(f"  [{device_info.ip}] 开始执行命令，共 {len(commands)} 条...")
            connection.execute_commands(commands, progress_cb=self.progress_callback)
            self._notify(f"  [{device_info.ip}] 全部命令执行完毕")

            # 保存配置（对应 w-sw-ssh --save）
            if self.save_after_exec:
                connection.save_config(progress_cb=self.progress_callback)

            # 二层上联口探测（对应 w-sw-ssh --l2_sw）
            if self.detect_l2_uplink:
                uplink = connection.detect_l2_uplink(progress_cb=self.progress_callback)
                if uplink:
                    self._notify(f"  [{device_info.ip}] 上联口: {uplink}")
        else:
            self._notify(f"✘ {device_info.ip} 连接失败: {connection.error_message}")

        connection.mark_finished()
        result_info = connection.get_connection_info()
        connection.disconnect()

        with self._lock:
            self.connections.append(connection)

        # 建议2：每台设备完成后立即通知 UI 更新状态列（无需等待全批完成）
        if self.device_done_callback:
            try:
                self.device_done_callback(result_info)
            except Exception as e:
                if self.logger:
                    self.logger.log_operation(f"设备完成回调失败: {e}", level='error')

        return connection

    # ──────────────────────────────────────────────────────
    # 启动与等待（ThreadPoolExecutor，动态调度）
    # ──────────────────────────────────────────────────────
    def start_connections(self) -> bool:
        if self.is_running:
            return False
        self.is_running = True
        self._stop_event.clear()
        self.connections.clear()
        self._active_connections.clear()
        return True

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Process all devices concurrently and always reset running state."""
        devices = getattr(self, '_device_infos', [])
        if not devices:
            self.is_running = False
            return True

        try:
            with ThreadPoolExecutor(max_workers=self.max_connections) as executor:
                next_index = 0
                futures = {}

                def submit_next():
                    nonlocal next_index
                    if self._stop_event.is_set() or next_index >= len(devices):
                        return False
                    dev = devices[next_index]
                    next_index += 1
                    futures[executor.submit(self._process_device_cancellable, dev)] = dev
                    return True

                for _ in range(min(self.max_connections, len(devices))):
                    submit_next()

                while futures:
                    done, _ = wait(futures, timeout=0.2, return_when=FIRST_COMPLETED)
                    if not done:
                        if self._stop_event.is_set():
                            for future in list(futures):
                                future.cancel()
                        continue

                    for future in done:
                        dev = futures.pop(future)
                        try:
                            if future.cancelled():
                                self._record_cancelled_device(dev)
                            else:
                                future.result()
                        except Exception as e:
                            self._notify(f"✘ {dev.ip} 处理异常: {e}")
                            if self.logger:
                                self.logger.log_operation(f"{dev.ip} 处理异常: {e}", level='error')

                    if not self._stop_event.is_set():
                        while len(futures) < self.max_connections and submit_next():
                            pass

                if self._stop_event.is_set() and next_index < len(devices):
                    for dev in devices[next_index:]:
                        self._record_cancelled_device(dev)
            return True
        finally:
            self.is_running = False

    def stop_connections(self):
        self.is_running = False
        self._stop_event.set()
        self._notify("正在停止连接任务...")
        with self._lock:
            active_connections = list(self._active_connections)
        for conn in active_connections:
            conn.disconnect()
        for conn in self.connections:
            conn.disconnect()

    def get_results(self) -> List[Dict]:
        return [conn.get_connection_info() for conn in self.connections]

    def get_successful_connections(self) -> List[SSHConnection]:
        return [c for c in self.connections if c.task_success]

    def get_failed_connections(self) -> List[SSHConnection]:
        return [c for c in self.connections if not c.task_success]

    def execute_command_on_all(self, command: str) -> Dict:
        """在所有已连接设备上执行同一命令"""
        results = {}
        for conn in self.get_successful_connections():
            results[conn.device_info.ip] = conn.execute_command(command)
        return results
