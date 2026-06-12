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
5. 命令文件品牌感知翻译：运行时自动将 H3C 命令转换为目标品牌语法
6. 线程调度：借鉴 w-sw-ssh 分批调度思路，用 ThreadPoolExecutor 实现更优雅的版本
"""

import paramiko
import re
import threading
from typing import Dict, List, Optional, Callable
import queue
import time
from datetime import datetime
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ipv6_utils import IPv6Utils, IPVersion, IPv6AddressValidator


# ──────────────────────────────────────────────────────────
# 提示符正则（借鉴 w-sw-ssh，兼容 Cisco/H3C/Huawei/Ruijie/TP-Link）
# 行末锚定，匹配 >, #, ], $, % 结尾的提示符
# ──────────────────────────────────────────────────────────
PROMPT_REGEX = re.compile(
    r'(\r|\n).?[<>\[\]a-zA-Z0-9~@*/\\_\-\(\)]+(>|%|#|\$|\]) *$'
)

# IP / MAC 地址正则（用于二层上联口探测）
RE_IPV4    = re.compile(r'\s?[1-9]\d{0,2}(\.\d{1,3}){3}\s?')
RE_MAC_STD = re.compile(r'\s?([\da-f]{4}[.\-]){2}[\da-f]{4}\s?', re.IGNORECASE)
RE_MAC_COL = re.compile(r'\s?([\da-f]{2}:){5}[\da-f]{2}\s?',     re.IGNORECASE)


class SSHConnection:
    """SSH 连接类（单台设备）"""

    def __init__(self, device_info, logger=None):
        self.device_info    = device_info
        self.logger         = logger
        self.client         = None
        self._shell         = None          # 持久交互式 shell
        self.is_connected   = False
        self.brand_detected = None
        self.model_detected = None          # 设备型号（借鉴 w-sw-ssh）
        self.error_message  = None
        self.command_results: List[Dict] = []
        self.ip_version     = IPVersion.UNKNOWN
        self.ipv6_validator = IPv6AddressValidator()
        self._print_lock    = threading.Lock()

        if hasattr(device_info, 'ip') and device_info.ip:
            self.ip_version = IPv6Utils.get_ip_version(device_info.ip)

    # ──────────────────────────────────────────────────────
    # 连接入口
    # ──────────────────────────────────────────────────────
    def connect(self) -> bool:
        """建立 SSH 连接（支持 IPv4 / IPv6）"""
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
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_address = self._get_connect_address()

            # 3. 连接（明确禁用 agent/key，强制密码认证）
            self.client.connect(
                hostname     = connect_address,
                port         = self.device_info.port,
                username     = self.device_info.username,
                password     = self.device_info.password,
                timeout      = 30,
                allow_agent  = False,
                look_for_keys= False,
            )
            self.is_connected = True

            conn_type = "IPv6" if self.ip_version == IPVersion.IPv6 else "IPv4"
            if self.logger:
                self.logger.log_operation(f"使用 {conn_type} 连接到 {connect_address}")

            # 4. 建立持久 shell，等待首个提示符
            self._shell = self.client.invoke_shell(width=200, height=50)
            self._shell.settimeout(15)
            self._read_until_prompt(timeout=10)

            # 5. 禁用分页（先用通用命令，识别品牌后会按品牌重发）
            self._send_no_page_generic()

            # 6. 自动识别品牌和型号（借鉴 w-sw-ssh 两步识别）
            self._detect_brand_and_model()

            # 7. 按识别品牌精确禁用分页
            self._send_no_page_by_brand()

            if self.logger:
                self.logger.log_connection_success(self.device_info)

            return True

        except paramiko.AuthenticationException as e:
            self.error_message = f"认证失败: {e}"
        except paramiko.SSHException as e:
            self.error_message = f"SSH 连接失败: {e}"
        except Exception as e:
            self.error_message = f"连接失败: {e}"

        self.is_connected = False
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
        while time.time() < deadline:
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
        for cmd in ['screen-length 0 temporary', 'terminal length 0']:
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
        if not self.is_connected or not self._shell:
            return "未连接"
        try:
            self._shell.send(command + '\n')
            time.sleep(sleep_time)
            output = self._read_until_prompt(timeout=15)

            self.command_results.append({
                'command':   command,
                'output':    output,
                'timestamp': datetime.now().isoformat(),
            })
            return output
        except Exception as e:
            error_msg = f"命令执行失败: {e}"
            self.command_results.append({
                'command':   command,
                'output':    error_msg,
                'timestamp': datetime.now().isoformat(),
            })
            return error_msg

    def execute_commands(self, commands: List[str],
                         progress_cb: Optional[Callable] = None) -> List[Dict]:
        """
        批量执行命令列表，支持品牌感知翻译（借鉴 w-sw-ssh cmd_prefix 机制）
        """
        from config.device_commands import translate_command_for_brand
        results = []
        brand   = self.brand_detected or 'h3c'

        for cmd in commands:
            # 自动翻译为目标品牌命令（H3C → Cisco 等）
            actual_cmd = translate_command_for_brand(cmd, brand)
            if progress_cb:
                if actual_cmd != cmd:
                    progress_cb(f"  [{self.device_info.ip}] 执行: {actual_cmd}  (译自: {cmd})")
                else:
                    progress_cb(f"  [{self.device_info.ip}] 执行: {actual_cmd}")

            output = self.execute_command(actual_cmd)

            if progress_cb and output:
                preview = '\n'.join(output.strip().splitlines()[:3])
                if preview:
                    progress_cb(f"  [{self.device_info.ip}] 输出:\n{preview}")

            results.append({'command': actual_cmd, 'output': output})

        return results

    # ──────────────────────────────────────────────────────
    # 保存配置（借鉴 w-sw-ssh uf_save）
    # ──────────────────────────────────────────────────────
    def save_config(self, progress_cb: Optional[Callable] = None) -> bool:
        """
        保存设备配置。
        各品牌 save 命令从 DEVICE_COMMANDS 字典获取，消除分散的 if-else。
        """
        from config.device_commands import get_command
        brand    = self.brand_detected or 'h3c'
        save_cmd = get_command(brand, 'save_config')
        if not save_cmd:
            return False

        if progress_cb:
            progress_cb(f"  [{self.device_info.ip}] 保存配置: {repr(save_cmd)}")

        try:
            # 支持多步命令（\r 分隔）
            for sub_cmd in save_cmd.split('\r'):
                if sub_cmd.strip():
                    self._shell.send(sub_cmd + '\n')
                    time.sleep(0.5)
            self._read_until_prompt(timeout=15)
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
                ip = m.group(0).strip()
                if not ip.startswith('0.'):
                    return ip
        return ''

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
        return {
            'device_info':    self.device_info.to_dict(),
            'is_connected':   self.is_connected,
            'brand_detected': self.brand_detected,
            'model_detected': self.model_detected,
            'error_message':  self.error_message,
            'command_results': self.command_results,
            'ip_version':     self.ip_version.value if self.ip_version else 0,
            'ip_version_name': (
                'IPv6' if self.ip_version == IPVersion.IPv6
                else 'IPv4' if self.ip_version == IPVersion.IPv4
                else 'Unknown'
            ),
        }


class SSHManager:
    """
    SSH 连接管理器

    线程调度优化（借鉴 w-sw-ssh 分批模型 + ThreadPoolExecutor）：
    - 原 w-sw-ssh：手工 start/join 批次，最后一批的慢设备会阻塞整批
    - 本版本：ThreadPoolExecutor + as_completed，任一设备完成即释放线程槽位
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
        # 扩展选项（对应 w-sw-ssh --save 和 --l2_sw）
        self.save_after_exec   = False
        self.detect_l2_uplink  = False
        self._lock = threading.Lock()

    def _load_commands(self) -> List[str]:
        """
        加载命令文件（优先自定义文件，其次默认 SSH_command.txt）。
        每行一条命令，# 开头为注释，空行忽略。
        """
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

    # ──────────────────────────────────────────────────────
    # 单设备处理逻辑（由线程池并发调用）
    # ──────────────────────────────────────────────────────
    def _process_device(self, device_info) -> SSHConnection:
        """连接单台设备并执行所有任务"""
        connection = SSHConnection(device_info, self.logger)
        self._notify(f"正在连接 {device_info.ip}...")

        success = connection.connect()

        if success:
            brand = connection.brand_detected or device_info.brand or 'unknown'
            model = connection.model_detected or ''
            desc  = f"{brand}  {model}".strip() if model else brand
            self._notify(f"✔ {device_info.ip} 连接成功  (品牌: {desc})")

            # 执行业务命令（品牌感知翻译）
            commands = self._load_commands()
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

        result_info = connection.get_connection_info()
        connection.disconnect()
        connection.is_connected = result_info.get('is_connected', False)

        with self._lock:
            self.connections.append(connection)

        # 建议2：每台设备完成后立即通知 UI 更新状态列（无需等待全批完成）
        if self.device_done_callback:
            try:
                self.device_done_callback(result_info)
            except Exception:
                pass

        return connection

    # ──────────────────────────────────────────────────────
    # 启动与等待（ThreadPoolExecutor，动态调度）
    # ──────────────────────────────────────────────────────
    def start_connections(self) -> bool:
        if self.is_running:
            return False
        self.is_running = True
        self.connections.clear()
        return True

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Process all devices concurrently and always reset running state."""
        devices = getattr(self, '_device_infos', [])
        if not devices:
            self.is_running = False
            return True

        try:
            with ThreadPoolExecutor(max_workers=self.max_connections) as executor:
                futures = {
                    executor.submit(self._process_device, dev): dev
                    for dev in devices
                }
                for future in as_completed(futures, timeout=timeout):
                    dev = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        self._notify(f"X {dev.ip} processing error: {e}")
            return True
        finally:
            self.is_running = False

    def stop_connections(self):
        self.is_running = False
        for conn in self.connections:
            conn.disconnect()

    def get_results(self) -> List[Dict]:
        return [conn.get_connection_info() for conn in self.connections]

    def get_successful_connections(self) -> List[SSHConnection]:
        return [c for c in self.connections if c.is_connected]

    def get_failed_connections(self) -> List[SSHConnection]:
        return [c for c in self.connections if not c.is_connected]

    def execute_command_on_all(self, command: str) -> Dict:
        """在所有已连接设备上执行同一命令"""
        results = {}
        for conn in self.get_successful_connections():
            results[conn.device_info.ip] = conn.execute_command(command)
        return results
