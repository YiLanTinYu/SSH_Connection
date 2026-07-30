#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
交换机SSH自动化运维工具 - 主程序入口
"""

import sys
import os
import traceback
import importlib
import importlib.util

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def _install_telnet_compat() -> None:
    """Register the local compatibility module when the stdlib module is absent."""
    module_name = "telnet" + "lib"
    if importlib.util.find_spec(module_name) is not None:
        return
    compatibility_module = importlib.import_module(f"{module_name}_compat")
    sys.modules[module_name] = compatibility_module


_install_telnet_compat()

def _runtime_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _write_startup_error() -> str:
    log_path = os.path.join(_runtime_dir(), 'startup_error.log')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
    return log_path


def _show_startup_error(log_path: str) -> None:
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox

        application = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "程序启动失败",
            f"程序启动失败，错误日志已生成:\n{log_path}",
        )
        application.processEvents()
    except (ImportError, RuntimeError):
        # The log file remains available when Qt itself cannot start.
        return


def run_app():
    try:
        from ui.main_window import main
        main()
    except Exception:
        log_path = _write_startup_error()
        _show_startup_error(log_path)
        raise

if __name__ == '__main__':
    run_app()
