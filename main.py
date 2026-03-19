#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
交换机SSH自动化运维工具 - 主程序入口
"""

import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Python 3.14+ 移除了 telnetlib，使用兼容层
if sys.version_info >= (3, 14):
    import telnetlib_compat as telnetlib
    sys.modules['telnetlib'] = telnetlib

from ui.main_window import main

if __name__ == '__main__':
    main()
