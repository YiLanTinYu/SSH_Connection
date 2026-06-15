#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
交换机SSH自动化运维工具 - 主程序入口
"""

import sys
import os
import traceback

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Python 3.14+ 移除了 telnetlib，使用兼容层
if sys.version_info >= (3, 14):
    import telnetlib_compat as telnetlib
    sys.modules['telnetlib'] = telnetlib

def _runtime_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _write_startup_error() -> str:
    log_path = os.path.join(_runtime_dir(), 'startup_error.log')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
    return log_path


def run_app():
    try:
        from ui.main_window import main
        main()
    except Exception:
        log_path = _write_startup_error()
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "程序启动失败",
                f"程序启动失败，错误日志已生成:\n{log_path}",
            )
        except Exception:
            pass
        raise

if __name__ == '__main__':
    run_app()
