#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
SSH连接管理器
支持多品牌交换机自动识别和多线程连接
"""

from netmiko import ConnectHandler
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from typing import Dict, List, Optional, Callable
import threading
import queue
import time
from datetime import datetime


class SSHConnection:
    """SSH连接类"""
    
    def __init__(self, device_info, logger=None):
        self.device_info = device_info
        self.logger = logger
        self.connection = None
        self.is_connected = False
        self.brand_detected = None
        self.error_message = None
        self.command_results = []
        
    def connect(self) -> bool:
        """
        建立SSH连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 构建设备参数
            device_params = {
                'device_type': 'autodetect',  # 自动检测设备类型
                'ip': self.device_info.ip,
                'port': self.device_info.port,
                'username': self.device_info.username,
                'password': self.device_info.password,
                'timeout': 30,
                'session_timeout': 60,
            }
            
            # 尝试连接
            self.connection = ConnectHandler(**device_params)
            self.is_connected = True
            
            # 自动识别品牌
            self._detect_brand()
            
            if self.logger:
                self.logger.log_connection_success(self.device_info)
            
            return True
            
        except NetMikoTimeoutException as e:
            self.error_message = f"连接超时: {str(e)}"
            self.is_connected = False
            if self.logger:
                self.logger.log_connection_failure(self.device_info, self.error_message)
            return False
            
        except NetMikoAuthenticationException as e:
            self.error_message = f"认证失败: {str(e)}"
            self.is_connected = False
            if self.logger:
                self.logger.log_connection_failure(self.device_info, self.error_message)
            return False
            
        except Exception as e:
            self.error_message = f"连接失败: {str(e)}"
            self.is_connected = False
            if self.logger:
                self.logger.log_connection_failure(self.device_info, self.error_message)
            return False
    
    def _detect_brand(self):
        """自动识别设备品牌"""
        try:
            # 尝试执行 display version 或 show version
            version_output = self.connection.send_command('display version')
            if not version_output or 'Invalid' in version_output:
                version_output = self.connection.send_command('show version')
            
            # 根据输出识别品牌
            from config.device_commands import detect_brand
            self.brand_detected = detect_brand(version_output)
            
        except Exception as e:
            self.brand_detected = self.device_info.brand or 'h3c'
    
    def execute_command(self, command: str) -> str:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            
        Returns:
            str: 命令输出
        """
        if not self.is_connected or not self.connection:
            return "未连接"
        
        try:
            output = self.connection.send_command(command)
            self.command_results.append({
                'command': command,
                'output': output,
                'timestamp': datetime.now().isoformat(),
            })
            return output
        except Exception as e:
            error_msg = f"命令执行失败: {str(e)}"
            self.command_results.append({
                'command': command,
                'output': error_msg,
                'timestamp': datetime.now().isoformat(),
            })
            return error_msg
    
    def disconnect(self):
        """断开连接"""
        if self.connection:
            try:
                self.connection.disconnect()
            except:
                pass
        self.is_connected = False
    
    def get_connection_info(self) -> Dict:
        """获取连接信息"""
        return {
            'device_info': self.device_info.to_dict(),
            'is_connected': self.is_connected,
            'brand_detected': self.brand_detected,
            'error_message': self.error_message,
            'command_results': self.command_results,
        }


class SSHManager:
    """SSH连接管理器"""
    
    def __init__(self, max_connections: int = 5, logger=None):
        self.max_connections = max_connections
        self.logger = logger
        self.connections: List[SSHConnection] = []
        self.connection_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.active_threads = []
        self.is_running = False
        self.progress_callback = None
        
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def add_device(self, device_info):
        """添加设备到连接队列"""
        self.connection_queue.put(device_info)
    
    def add_devices(self, device_infos: List):
        """批量添加设备"""
        for device_info in device_infos:
            self.add_device(device_info)
    
    def _worker_thread(self):
        """工作线程"""
        while self.is_running:
            try:
                # 从队列获取设备（非阻塞）
                device_info = self.connection_queue.get(timeout=1)
                
                # 创建连接
                connection = SSHConnection(device_info, self.logger)
                
                # 更新进度
                if self.progress_callback:
                    self.progress_callback(f"正在连接 {device_info.ip}...")
                
                # 建立连接
                success = connection.connect()
                
                # 如果连接成功，执行默认命令
                if success:
                    from config.device_commands import get_command
                    default_cmd = get_command(connection.brand_detected, 'display_version')
                    connection.execute_command(default_cmd)
                
                # 保存结果
                self.results_queue.put(connection)
                self.connections.append(connection)
                
                # 更新进度
                if self.progress_callback:
                    status = "成功" if success else f"失败: {connection.error_message}"
                    self.progress_callback(f"{device_info.ip} 连接{status}")
                
            except queue.Empty:
                continue
            except Exception as e:
                if self.progress_callback:
                    self.progress_callback(f"连接异常: {str(e)}")
    
    def start_connections(self) -> bool:
        """
        开始连接所有设备
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_running:
            return False
        
        self.is_running = True
        self.connections.clear()
        
        # 创建工作线程
        thread_count = min(self.max_connections, self.connection_queue.qsize())
        
        for i in range(thread_count):
            thread = threading.Thread(target=self._worker_thread, daemon=True)
            thread.start()
            self.active_threads.append(thread)
        
        return True
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有连接完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否成功完成
        """
        start_time = time.time()
        
        while self.is_running:
            # 检查是否所有任务完成
            if self.connection_queue.empty():
                # 等待一段时间确保所有线程处理完当前任务
                time.sleep(2)
                
                # 检查是否超时
                if timeout and (time.time() - start_time) > timeout:
                    break
                
                # 如果没有更多任务，停止运行
                if self.connection_queue.empty():
                    break
            
            time.sleep(0.5)
        
        self.stop_connections()
        return True
    
    def stop_connections(self):
        """停止所有连接"""
        self.is_running = False
        
        # 断开所有连接
        for connection in self.connections:
            connection.disconnect()
        
        # 等待线程结束
        for thread in self.active_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.active_threads.clear()
    
    def get_results(self) -> List[Dict]:
        """获取所有连接结果"""
        return [conn.get_connection_info() for conn in self.connections]
    
    def get_successful_connections(self) -> List[SSHConnection]:
        """获取成功连接的设备"""
        return [conn for conn in self.connections if conn.is_connected]
    
    def get_failed_connections(self) -> List[SSHConnection]:
        """获取连接失败的设备"""
        return [conn for conn in self.connections if not conn.is_connected]
    
    def execute_command_on_all(self, command: str) -> Dict:
        """
        在所有已连接设备上执行命令
        
        Args:
            command: 要执行的命令
            
        Returns:
            Dict: 执行结果
        """
        results = {}
        
        for connection in self.get_successful_connections():
            output = connection.execute_command(command)
            results[connection.device_info.ip] = output
        
        return results
