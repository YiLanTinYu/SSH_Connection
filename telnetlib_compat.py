#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
telnetlib 兼容层
为 Python 3.14+ 提供基本的 telnetlib 接口
支持IPv4和IPv6地址
"""

import socket
import time
from typing import Optional, Tuple
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.ipv6_utils import IPv6Utils, IPVersion


class Telnet:
    """Telnet 客户端类"""
    
    def __init__(self, host: Optional[str] = None, port: int = 23, timeout: float = 10.0):
        """
        初始化 Telnet 客户端
        
        Args:
            host: 主机地址（支持IPv4和IPv6）
            port: 端口号
            timeout: 超时时间（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.is_open = False
        self.ip_version = IPVersion.UNKNOWN
        
        # 识别IP版本
        if host:
            self.ip_version = IPv6Utils.get_ip_version(host)
    
    def open(self, host: str, port: int = 23, timeout: float = 10.0) -> None:
        """
        打开 Telnet 连接（支持IPv4和IPv6）
        
        Args:
            host: 主机地址（支持IPv4和IPv6）
            port: 端口号
            timeout: 超时时间（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        
        try:
            # 识别IP版本
            self.ip_version = IPv6Utils.get_ip_version(host)
            
            # 根据IP版本选择地址族
            if self.ip_version == IPVersion.IPv6:
                family = socket.AF_INET6
                # 规范化IPv6地址
                connect_host = IPv6Utils.normalize_ipv6(host)
            else:
                family = socket.AF_INET
                connect_host = host
            
            # 创建socket
            self.socket = socket.socket(family, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            # 连接
            self.socket.connect((connect_host, port))
            self.is_open = True
            
        except Exception as e:
            self.is_open = False
            raise OSError(f"无法连接到 {host}:{port} - {str(e)}")
    
    def close(self) -> None:
        """关闭连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.is_open = False
        self.socket = None
    
    def read_until(self, expected: str, timeout: Optional[float] = None) -> bytes:
        """
        读取直到遇到期望的字符串
        
        Args:
            expected: 期望的字符串
            timeout: 超时时间（秒）
            
        Returns:
            bytes: 读取的数据
        """
        if not self.is_open or not self.socket:
            raise OSError("连接未打开")
        
        timeout = timeout or self.timeout
        start_time = time.time()
        buffer = b''
        expected_bytes = expected.encode('utf-8')
        
        while True:
            try:
                # 检查超时
                if time.time() - start_time > timeout:
                    break
                
                # 接收数据
                data = self.socket.recv(4096)
                if not data:
                    break
                
                buffer += data
                
                # 检查是否包含期望的字符串
                if expected_bytes in buffer:
                    break
                
            except socket.timeout:
                break
            except Exception as e:
                raise OSError(f"读取数据失败: {str(e)}")
        
        return buffer
    
    def read_all(self) -> bytes:
        """
        读取所有可用数据
        
        Returns:
            bytes: 读取的数据
        """
        if not self.is_open or not self.socket:
            raise OSError("连接未打开")
        
        buffer = b''
        try:
            # 设置非阻塞模式
            self.socket.setblocking(False)
            
            while True:
                try:
                    data = self.socket.recv(4096)
                    if not data:
                        break
                    buffer += data
                except BlockingIOError:
                    break
                except Exception:
                    break
            
            # 恢复阻塞模式
            self.socket.setblocking(True)
            
        except Exception as e:
            raise OSError(f"读取数据失败: {str(e)}")
        
        return buffer
    
    def write(self, buffer: bytes) -> int:
        """
        写入数据
        
        Args:
            buffer: 要写入的数据
            
        Returns:
            int: 写入的字节数
        """
        if not self.is_open or not self.socket:
            raise OSError("连接未打开")
        
        try:
            return self.socket.send(buffer)
        except Exception as e:
            raise OSError(f"写入数据失败: {str(e)}")
    
    def read_very_eager(self) -> bytes:
        """
        立即读取所有可用数据
        
        Returns:
            bytes: 读取的数据
        """
        return self.read_all()
    
    def read_lazy(self) -> bytes:
        """
        懒惰读取数据
        
        Returns:
            bytes: 读取的数据
        """
        return self.read_all()
    
    def read_some(self) -> bytes:
        """
        读取一些数据
        
        Returns:
            bytes: 读取的数据
        """
        if not self.is_open or not self.socket:
            raise OSError("连接未打开")
        
        try:
            return self.socket.recv(4096)
        except socket.timeout:
            return b''
        except Exception as e:
            raise OSError(f"读取数据失败: {str(e)}")
    
    def get_socket(self) -> socket.socket:
        """
        获取底层 socket 对象
        
        Returns:
            socket.socket: socket 对象
        """
        return self.socket
    
    def set_debuglevel(self, level: int) -> None:
        """
        设置调试级别
        
        Args:
            level: 调试级别
        """
        pass  # 不实现调试功能


def create_telnet(host: Optional[str] = None, port: int = 23, timeout: float = 10.0) -> Telnet:
    """
    创建 Telnet 连接
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间（秒）
        
    Returns:
        Telnet: Telnet 客户端对象
    """
    return Telnet(host, port, timeout)


# 创建函数别名，兼容 netmiko 的使用
TelnetFactory = create_telnet
