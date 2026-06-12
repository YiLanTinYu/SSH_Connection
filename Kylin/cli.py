#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
交换机 SSH 自动化运维工具 — 命令行入口 (CLI 模式)

适用场景：
  - 银河麒麟 V10 / 无图形界面的 Linux 服务器
  - CI/CD 自动化脚本
  - 批量巡检任务

用法示例：
  # 从 JSON 文件批量导入设备
  python cli.py --devices devices.json

  # 从 Excel 文件批量导入设备
  python cli.py --excel device_template.xlsx

  # 命令行直接指定单台设备
  python cli.py --ip 192.168.1.1 --username admin --password Admin@123 --brand h3c

  # 指定命令文件 + 保存配置 + 探测上联口
  python cli.py --devices devices.json --cmd SSH_command.txt --save --l2

  # 指定并发数
  python cli.py --devices devices.json --workers 10

  # 输出结果到 JSON 文件
  python cli.py --devices devices.json --output result.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Optional

# ── 注入 telnetlib 兼容层（Python 3.11+ netmiko 依赖）──────────────────
# netmiko 4.x 在 Python 3.13 上仍尝试 import telnetlib（已从标准库移除）
# 无论版本一律注入，安全无副作用
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

try:
    import telnetlib  # noqa: F401  # Python <= 3.12 原生存在
except ImportError:
    import telnetlib_compat as telnetlib  # type: ignore
    sys.modules['telnetlib'] = telnetlib  # type: ignore


# ── 项目模块 ───────────────────────────────────────────────────────────
from config.device_config import DeviceInfo, DeviceConfigManager
from core.ssh_manager_simple import SSHManager
from utils.logger import ConnectionLogger


# ══════════════════════════════════════════════════════════════════════
# ANSI 彩色输出（麒麟终端支持 ANSI，Windows 兼容降级）
# ══════════════════════════════════════════════════════════════════════
_USE_COLOR = sys.stdout.isatty() and os.name != 'nt'


def _c(text: str, code: str) -> str:
    return f'\033[{code}m{text}\033[0m' if _USE_COLOR else text


def _green(t):  return _c(t, '32')
def _red(t):    return _c(t, '31')
def _yellow(t): return _c(t, '33')
def _cyan(t):   return _c(t, '36')
def _bold(t):   return _c(t, '1')


def _ts() -> str:
    return datetime.now().strftime('%H:%M:%S')


def _print(msg: str, level: str = 'info'):
    """带时间戳的格式化输出"""
    ts = _ts()
    if level == 'ok':
        prefix = _green(f'[{ts}] [OK]  ')
    elif level == 'err':
        prefix = _red(f'[{ts}] [ERR] ')
    elif level == 'warn':
        prefix = _yellow(f'[{ts}] [WARN]')
    elif level == 'head':
        prefix = _cyan(f'[{ts}] [----]')
    else:
        prefix = f'[{ts}]      '
    print(prefix + ' ' + msg, flush=True)


# ══════════════════════════════════════════════════════════════════════
# 参数解析
# ══════════════════════════════════════════════════════════════════════
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='python cli.py',
        description=_bold('交换机 SSH 自动化运维工具 — CLI 模式'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单台设备
  python cli.py --ip 192.168.1.1 -u admin -p Admin@123 --brand h3c

  # 批量（JSON）
  python cli.py --devices devices.json --save --l2

  # 批量（Excel）
  python cli.py --excel device_template.xlsx --cmd my_cmds.txt

  # 输出到文件
  python cli.py --devices devices.json --output result.json
        """,
    )

    # ── 设备来源（三选一）──────────────────────────────────────
    src = p.add_argument_group('设备来源（三选一）')
    src.add_argument('--devices', '-d', metavar='FILE.json',
                     help='设备列表 JSON 文件（格式见 --gen-template）')
    src.add_argument('--excel', '-e', metavar='FILE.xlsx',
                     help='设备列表 Excel 文件（与 device_template.xlsx 同格式）')
    src.add_argument('--ip', metavar='ADDR',
                     help='直接指定单台设备 IP（IPv4 或 IPv6）')

    # ── 单台设备参数 ────────────────────────────────────────────
    single = p.add_argument_group('单台设备参数（与 --ip 搭配使用）')
    single.add_argument('--port',     type=int, default=22, metavar='N',  help='SSH 端口（默认 22）')
    single.add_argument('--username', '-u', metavar='USER', help='登录用户名')
    single.add_argument('--password', '-p', metavar='PASS', help='登录密码')
    single.add_argument('--brand',    default='h3c',
                        choices=['h3c', 'huawei', 'ruijie', 'cisco', 'tplink'],
                        help='设备品牌（默认 h3c）')
    single.add_argument('--name',     default='', metavar='NAME', help='设备名称（可选）')

    # ── 运行选项 ────────────────────────────────────────────────
    opts = p.add_argument_group('运行选项')
    opts.add_argument('--cmd', metavar='FILE.txt',
                      help='命令文件路径（默认: SSH_command.txt）')
    opts.add_argument('--save', action='store_true',
                      help='执行命令后自动保存设备配置（同 w-sw-ssh --save）')
    opts.add_argument('--l2', action='store_true',
                      help='探测二层上联口（同 w-sw-ssh --l2_sw）')
    opts.add_argument('--workers', type=int, default=5, metavar='N',
                      help='最大并发连接数（默认 5）')
    opts.add_argument('--timeout', type=float, default=None, metavar='SEC',
                      help='整体超时秒数（默认无限等待）')

    # ── 输出选项 ────────────────────────────────────────────────
    out = p.add_argument_group('输出选项')
    out.add_argument('--output', '-o', metavar='FILE.json',
                     help='将连接结果写入 JSON 文件')
    out.add_argument('--quiet', '-q', action='store_true',
                     help='静默模式：仅输出摘要，不打印每条命令输出')
    out.add_argument('--gen-template', action='store_true',
                     help='生成设备 JSON 模板文件 devices_template.json 后退出')

    return p


# ══════════════════════════════════════════════════════════════════════
# 模板生成
# ══════════════════════════════════════════════════════════════════════
_JSON_TEMPLATE = [
    {
        "name": "核心交换机-1",
        "brand": "h3c",
        "ip": "192.168.1.1",
        "port": 22,
        "username": "admin",
        "password": "Admin@123"
    },
    {
        "name": "汇聚交换机-1",
        "brand": "huawei",
        "ip": "192.168.1.2",
        "port": 22,
        "username": "admin",
        "password": "Admin@123"
    },
    {
        "name": "接入交换机-IPv6",
        "brand": "cisco",
        "ip": "2001:db8::1",
        "port": 22,
        "username": "admin",
        "password": "Admin@123"
    }
]


def _gen_template():
    path = os.path.join(_HERE, 'devices_template.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(_JSON_TEMPLATE, f, ensure_ascii=False, indent=2)
    _print(f'模板已生成: {path}', 'ok')
    _print('字段说明: name(可选) brand ip port username password', 'info')


# ══════════════════════════════════════════════════════════════════════
# 设备加载
# ══════════════════════════════════════════════════════════════════════
def _load_from_json(path: str) -> List[DeviceInfo]:
    """从 JSON 文件加载设备列表"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError('JSON 文件根节点必须是数组 []')
    devices = []
    for i, item in enumerate(data):
        try:
            d = DeviceInfo(
                brand=str(item.get('brand', 'h3c')),
                ip=str(item.get('ip', '')),
                port=int(item.get('port', 22)),
                username=str(item.get('username', '')),
                password=str(item.get('password', '')),
                name=str(item.get('name', '')),
            )
            if not d.ip:
                raise ValueError('ip 字段不能为空')
            if not d.username:
                raise ValueError('username 字段不能为空')
            if not d.password:
                raise ValueError('password 字段不能为空')
            devices.append(d)
        except Exception as e:
            _print(f'JSON 第 {i+1} 条记录跳过: {e}', 'warn')
    return devices


def _load_from_excel(path: str) -> List[DeviceInfo]:
    """从 Excel 文件加载设备列表（复用 DeviceConfigManager）"""
    mgr = DeviceConfigManager()
    ok, fail, errors = mgr.import_from_excel(path)
    for err in errors:
        _print(err, 'warn')
    return mgr.get_devices()


def _build_devices(args) -> List[DeviceInfo]:
    """根据参数构建设备列表"""
    if args.devices:
        path = os.path.abspath(args.devices)
        if not os.path.isfile(path):
            _print(f'设备文件不存在: {path}', 'err')
            sys.exit(1)
        devices = _load_from_json(path)
        _print(f'从 JSON 加载 {len(devices)} 台设备: {path}', 'info')
        return devices

    if args.excel:
        path = os.path.abspath(args.excel)
        if not os.path.isfile(path):
            _print(f'Excel 文件不存在: {path}', 'err')
            sys.exit(1)
        devices = _load_from_excel(path)
        _print(f'从 Excel 加载 {len(devices)} 台设备: {path}', 'info')
        return devices

    if args.ip:
        if not args.username:
            _print('使用 --ip 时必须指定 --username', 'err')
            sys.exit(1)
        if not args.password:
            _print('使用 --ip 时必须指定 --password', 'err')
            sys.exit(1)
        d = DeviceInfo(
            brand=args.brand,
            ip=args.ip,
            port=args.port,
            username=args.username,
            password=args.password,
            name=args.name or f'{args.brand}_{args.ip}',
        )
        return [d]

    _print('请通过 --devices / --excel / --ip 指定设备来源，或 -h 查看帮助', 'err')
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════
# 进度回调（CLI 彩色输出）
# ══════════════════════════════════════════════════════════════════════
def _make_progress_cb(quiet: bool):
    def _cb(msg: str):
        if quiet:
            # 静默模式只打印连接成功/失败摘要
            if msg.startswith('✔') or msg.startswith('✘') or msg.startswith('正在连接'):
                _print(msg, 'ok' if '✔' in msg else ('err' if '✘' in msg else 'info'))
        else:
            if msg.startswith('✔'):
                _print(msg, 'ok')
            elif msg.startswith('✘'):
                _print(msg, 'err')
            elif msg.startswith('正在连接'):
                _print(msg, 'info')
            elif '[L2探测]' in msg:
                _print(msg, 'warn')
            else:
                _print(msg, 'info')
    return _cb


# ══════════════════════════════════════════════════════════════════════
# 结果打印
# ══════════════════════════════════════════════════════════════════════
def _print_summary(results: list):
    total   = len(results)
    success = sum(1 for r in results if r.get('is_connected'))
    failure = total - success
    rate    = (success / total * 100) if total else 0.0

    print()
    print(_bold(_cyan('=' * 60)))
    print(_bold(_cyan('  连接结果摘要')))
    print(_bold(_cyan('=' * 60)))
    print(f'  总设备数  : {total}')
    print(f'  成功      : {_green(str(success))}')
    print(f'  失败      : {_red(str(failure))}')
    print(f'  成功率    : {rate:.1f}%')
    print(_bold(_cyan('=' * 60)))

    if failure:
        print()
        print(_bold(_red('  失败设备列表:')))
        for r in results:
            if not r.get('is_connected'):
                ip  = r.get('device_info', {}).get('ip', '?')
                err = r.get('error_message', '未知错误')
                print(f'    {_red("✘")} {ip:40s}  {err}')

    print()


def _print_results_detail(results: list):
    """打印每台设备的命令执行结果"""
    for r in results:
        if not r.get('is_connected'):
            continue
        ip    = r.get('device_info', {}).get('ip', '?')
        brand = r.get('brand_detected', '?')
        model = r.get('model_detected', '')
        cmds  = r.get('command_results', [])
        print()
        print(_bold(_cyan(f'  ── 设备: {ip}  品牌: {brand}  型号: {model} ──')))
        for cr in cmds:
            cmd    = cr.get('command', '')
            output = cr.get('output', '').strip()
            print(f'  {_yellow("$")} {cmd}')
            for line in output.splitlines()[:20]:   # 最多显示 20 行
                print(f'    {line}')
            if len(output.splitlines()) > 20:
                print(f'    ... (共 {len(output.splitlines())} 行，已截断)')


# ══════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════
def run(args=None):
    parser = _build_parser()
    ns = parser.parse_args(args)

    # 生成模板并退出
    if ns.gen_template:
        _gen_template()
        return

    # ── 横幅 ──────────────────────────────────────────────────
    print()
    print(_bold(_cyan('╔══════════════════════════════════════════════════╗')))
    print(_bold(_cyan('║   交换机 SSH 自动化运维工具  v2.0  CLI 模式      ║')))
    print(_bold(_cyan('╚══════════════════════════════════════════════════╝')))
    print()

    # ── 加载设备 ──────────────────────────────────────────────
    devices = _build_devices(ns)
    if not devices:
        _print('未加载到任何设备，退出', 'err')
        sys.exit(1)

    _print(f'共 {len(devices)} 台设备，并发数: {ns.workers}', 'head')
    if ns.save:
        _print('已启用: 执行后保存配置', 'info')
    if ns.l2:
        _print('已启用: 探测二层上联口', 'info')

    # ── 命令文件 ──────────────────────────────────────────────
    cmd_file: Optional[str] = None
    if ns.cmd:
        cmd_file = os.path.abspath(ns.cmd)
        if not os.path.isfile(cmd_file):
            _print(f'命令文件不存在: {cmd_file}', 'err')
            sys.exit(1)
        _print(f'命令文件: {cmd_file}', 'info')
    else:
        default_cmd = os.path.join(_HERE, 'SSH_command.txt')
        if os.path.isfile(default_cmd):
            _print(f'使用默认命令文件: SSH_command.txt', 'info')
        else:
            _print('未找到 SSH_command.txt，将执行 display version', 'warn')

    # ── 初始化管理器 ──────────────────────────────────────────
    logger = ConnectionLogger()
    manager = SSHManager(max_connections=ns.workers, logger=logger)
    manager.command_file    = cmd_file
    manager.save_after_exec = ns.save
    manager.detect_l2_uplink = ns.l2
    manager.set_progress_callback(_make_progress_cb(ns.quiet))

    # ── 执行连接 ──────────────────────────────────────────────
    _print('开始连接...', 'head')
    print()
    t_start = time.time()

    manager.add_devices(devices)
    manager.start_connections()
    manager.wait_for_completion(timeout=ns.timeout)

    elapsed = time.time() - t_start
    _print(f'全部完成，耗时 {elapsed:.1f} 秒', 'head')

    # ── 结果汇总 ──────────────────────────────────────────────
    results = manager.get_results()
    _print_summary(results)

    if not ns.quiet:
        _print_results_detail(results)

    # ── 写入 JSON 结果 ─────────────────────────────────────────
    if ns.output:
        out_path = os.path.abspath(ns.output)
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            _print(f'结果已写入: {out_path}', 'ok')
        except Exception as e:
            _print(f'结果写入失败: {e}', 'err')

    # ── 日志摘要 ──────────────────────────────────────────────
    summary = logger.get_log_summary()
    log_dir = os.path.abspath(logger.log_dir)
    _print(f'日志目录: {log_dir}', 'info')
    _print(
        f'日志记录 → 成功: {summary["success_count"]}  '
        f'失败: {summary["failure_count"]}  '
        f'成功率: {summary["success_rate"]:.1f}%',
        'info'
    )

    # 返回退出码（有失败设备时非 0）
    failed = sum(1 for r in results if not r.get('is_connected'))
    sys.exit(failed)


# ══════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    run()
