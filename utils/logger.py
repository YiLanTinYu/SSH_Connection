#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
日志记录模块
支持成功和失败日志分开保存
支持IPv4和IPv6连接信息记录
"""

import os
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ipv6_utils import IPv6Utils, IPVersion


class ConnectionLogger:
    """连接日志记录器"""
    
    def __init__(self, log_dir: str = 'logs'):
        self.log_dir = log_dir
        self.success_logger = None
        self.failure_logger = None
        self.operation_logger = None
        
        # 创建日志目录
        self._create_log_directory()
        
        # 初始化日志记录器
        self._init_loggers()
    
    def _create_log_directory(self):
        """创建日志目录"""
        # 确保日志目录存在
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        # 创建成功和失败子目录
        Path(os.path.join(self.log_dir, 'success')).mkdir(exist_ok=True)
        Path(os.path.join(self.log_dir, 'failure')).mkdir(exist_ok=True)
    
    def _init_loggers(self):
        """初始化日志记录器"""
        # 获取当前日期时间
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 成功连接日志
        success_log_file = os.path.join(self.log_dir, 'success', f'success_{current_time}.log')
        self.success_logger = self._create_logger('success', success_log_file)
        
        # 失败连接日志
        failure_log_file = os.path.join(self.log_dir, 'failure', f'failure_{current_time}.log')
        self.failure_logger = self._create_logger('failure', failure_log_file)
        
        # 操作日志
        operation_log_file = os.path.join(self.log_dir, f'operation_{current_time}.log')
        self.operation_logger = self._create_logger('operation', operation_log_file)
    
    def _create_logger(self, name: str, log_file: str) -> logging.Logger:
        """创建日志记录器"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # 如果已经存在处理器，先清除
        if logger.handlers:
            logger.handlers.clear()
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        
        return logger
    
    def log_connection_success(self, device_info):
        """
        记录成功连接（支持IPv4和IPv6）
        
        Args:
            device_info: 设备信息对象
        """
        # 获取IP版本信息
        ip_version = device_info.ip_version.value if hasattr(device_info, 'ip_version') and device_info.ip_version else 0
        version_name = 'IPv6' if ip_version == 6 else 'IPv4' if ip_version == 4 else 'Unknown'
        
        # 使用显示格式记录IPv6地址
        display_ip = device_info.get_display_address() if hasattr(device_info, 'get_display_address') else device_info.ip
        
        log_message = (
            f"设备名称: {device_info.name} | "
            f"IP: {display_ip} | "
            f"IP版本: {version_name} | "
            f"端口: {device_info.port} | "
            f"品牌: {device_info.brand} | "
            f"状态: 连接成功"
        )
        
        if self.success_logger:
            self.success_logger.info(log_message)
        
        if self.operation_logger:
            self.operation_logger.info(f"[SUCCESS] {log_message}")
    
    def log_connection_failure(self, device_info, error_message: str):
        """
        记录连接失败（支持IPv4和IPv6）
        
        Args:
            device_info: 设备信息对象
            error_message: 错误信息
        """
        # 获取IP版本信息
        ip_version = device_info.ip_version.value if hasattr(device_info, 'ip_version') and device_info.ip_version else 0
        version_name = 'IPv6' if ip_version == 6 else 'IPv4' if ip_version == 4 else 'Unknown'
        
        # 使用显示格式记录IPv6地址
        display_ip = device_info.get_display_address() if hasattr(device_info, 'get_display_address') else device_info.ip
        
        log_message = (
            f"设备名称: {device_info.name} | "
            f"IP: {display_ip} | "
            f"IP版本: {version_name} | "
            f"端口: {device_info.port} | "
            f"品牌: {device_info.brand} | "
            f"状态: 连接失败 | "
            f"失败原因: {error_message}"
        )
        
        if self.failure_logger:
            self.failure_logger.error(log_message)
        
        if self.operation_logger:
            self.operation_logger.error(f"[FAILURE] {log_message}")
    
    def log_operation(self, message: str, level: str = 'info'):
        """
        记录操作日志
        
        Args:
            message: 日志消息
            level: 日志级别 (info, warning, error)
        """
        if not self.operation_logger:
            return
        
        if level.lower() == 'info':
            self.operation_logger.info(message)
        elif level.lower() == 'warning':
            self.operation_logger.warning(message)
        elif level.lower() == 'error':
            self.operation_logger.error(message)
    
    def log_command_execution(self, device_info, command: str, output: str):
        """
        记录命令执行
        
        Args:
            device_info: 设备信息对象
            command: 执行的命令
            output: 命令输出
        """
        log_message = (
            f"设备: {device_info.name} ({device_info.ip}) | "
            f"命令: {command}"
        )
        
        if self.operation_logger:
            self.operation_logger.info(f"[COMMAND] {log_message}")
            # 记录命令输出（截断过长的输出）
            output_preview = output[:500] + "..." if len(output) > 500 else output
            self.operation_logger.info(f"[OUTPUT] {output_preview}")
    
    def get_log_summary(self) -> dict:
        """
        获取日志摘要
        
        Returns:
            dict: 日志统计信息
        """
        success_count = 0
        failure_count = 0
        
        # 统计成功日志
        if self.success_logger and self.success_logger.handlers:
            success_handler = self.success_logger.handlers[0]
            if isinstance(success_handler, logging.FileHandler):
                try:
                    with open(success_handler.baseFilename, 'r', encoding='utf-8') as f:
                        success_count = len([line for line in f if '[SUCCESS]' in line or 'success' in line.lower()])
                except:
                    pass
        
        # 统计失败日志
        if self.failure_logger and self.failure_logger.handlers:
            failure_handler = self.failure_logger.handlers[0]
            if isinstance(failure_handler, logging.FileHandler):
                try:
                    with open(failure_handler.baseFilename, 'r', encoding='utf-8') as f:
                        failure_count = len([line for line in f if '[FAILURE]' in line or 'failure' in line.lower() or 'failed' in line.lower()])
                except:
                    pass
        
        return {
            'success_count': success_count,
            'failure_count': failure_count,
            'total_count': success_count + failure_count,
            'success_rate': (success_count / (success_count + failure_count) * 100) if (success_count + failure_count) > 0 else 0,
            'log_dir': self.log_dir,
        }
    
    def get_log_files(self) -> dict:
        """
        获取日志文件路径
        
        Returns:
            dict: 日志文件路径
        """
        log_files = {
            'success': [],
            'failure': [],
            'operation': [],
        }
        
        # 获取成功日志文件
        success_dir = os.path.join(self.log_dir, 'success')
        if os.path.exists(success_dir):
            log_files['success'] = [
                os.path.join(success_dir, f) 
                for f in os.listdir(success_dir) 
                if f.endswith('.log')
            ]
        
        # 获取失败日志文件
        failure_dir = os.path.join(self.log_dir, 'failure')
        if os.path.exists(failure_dir):
            log_files['failure'] = [
                os.path.join(failure_dir, f) 
                for f in os.listdir(failure_dir) 
                if f.endswith('.log')
            ]
        
        # 获取操作日志文件
        if os.path.exists(self.log_dir):
            log_files['operation'] = [
                os.path.join(self.log_dir, f) 
                for f in os.listdir(self.log_dir) 
                if f.endswith('.log') and not os.path.isdir(os.path.join(self.log_dir, f))
            ]
        
        return log_files
