#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
IPv6地址验证和解析工具模块
提供IPv6/IPv4地址的验证、解析和转换功能
"""

import re
import socket
import ipaddress
from typing import Optional, Tuple, Union
from enum import Enum


class IPVersion(Enum):
    """IP版本枚举"""
    IPv4 = 4
    IPv6 = 6
    UNKNOWN = 0


class IPv6Utils:
    """IPv6工具类"""
    
    # IPv6地址正则表达式
    IPV6_PATTERN = re.compile(
        r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|'
        r'^::1$|'
        r'^::$|'
        r'^([0-9a-fA-F]{1,4}:){1,7}:$|'
        r'^:([0-9a-fA-F]{1,4}:){1,7}$|'
        r'^([0-9a-fA-F]{1,4}:){0,6}([0-9a-fA-F]{1,4}){0,1}$'
    )
    
    # IPv4地址正则表达式
    IPV4_PATTERN = re.compile(
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    
    @staticmethod
    def is_valid_ipv6(address: str) -> bool:
        """
        验证IPv6地址格式
        
        Args:
            address: 要验证的地址字符串
            
        Returns:
            bool: 是否为有效的IPv6地址
        """
        try:
            ipaddress.IPv6Address(address)
            return True
        except ipaddress.AddressValueError:
            return False
    
    @staticmethod
    def is_valid_ipv4(address: str) -> bool:
        """
        验证IPv4地址格式
        
        Args:
            address: 要验证的地址字符串
            
        Returns:
            bool: 是否为有效的IPv4地址
        """
        try:
            ipaddress.IPv4Address(address)
            return True
        except ipaddress.AddressValueError:
            return False
    
    @staticmethod
    def is_valid_ip(address: str) -> bool:
        """
        验证IP地址格式（IPv4或IPv6）
        
        Args:
            address: 要验证的地址字符串
            
        Returns:
            bool: 是否为有效的IP地址
        """
        return IPv6Utils.is_valid_ipv4(address) or IPv6Utils.is_valid_ipv6(address)
    
    @staticmethod
    def get_ip_version(address: str) -> IPVersion:
        """
        获取IP地址版本
        
        Args:
            address: IP地址字符串
            
        Returns:
            IPVersion: IP版本枚举
        """
        if IPv6Utils.is_valid_ipv4(address):
            return IPVersion.IPv4
        elif IPv6Utils.is_valid_ipv6(address):
            return IPVersion.IPv6
        else:
            return IPVersion.UNKNOWN
    
    @staticmethod
    def normalize_ipv6(address: str) -> str:
        """
        规范化IPv6地址（压缩格式）
        
        Args:
            address: IPv6地址字符串
            
        Returns:
            str: 规范化后的IPv6地址
        """
        try:
            ipv6 = ipaddress.IPv6Address(address)
            return str(ipv6.compressed)
        except ipaddress.AddressValueError:
            return address
    
    @staticmethod
    def expand_ipv6(address: str) -> str:
        """
        扩展IPv6地址（完整格式）
        
        Args:
            address: IPv6地址字符串
            
        Returns:
            str: 扩展后的IPv6地址
        """
        try:
            ipv6 = ipaddress.IPv6Address(address)
            return str(ipv6.exploded)
        except ipaddress.AddressValueError:
            return address
    
    @staticmethod
    def get_socket_family(address: str) -> socket.AddressFamily:
        """
        根据IP地址获取socket地址族
        
        Args:
            address: IP地址字符串
            
        Returns:
            socket.AddressFamily: socket地址族
        """
        version = IPv6Utils.get_ip_version(address)
        if version == IPVersion.IPv6:
            return socket.AF_INET6
        elif version == IPVersion.IPv4:
            return socket.AF_INET
        else:
            raise ValueError(f"无效的IP地址: {address}")
    
    @staticmethod
    def is_ipv6_link_local(address: str) -> bool:
        """
        判断是否为IPv6链路本地地址
        
        Args:
            address: IPv6地址字符串
            
        Returns:
            bool: 是否为链路本地地址
        """
        try:
            ipv6 = ipaddress.IPv6Address(address)
            return ipv6.is_link_local
        except ipaddress.AddressValueError:
            return False
    
    @staticmethod
    def is_ipv6_loopback(address: str) -> bool:
        """
        判断是否为IPv6回环地址
        
        Args:
            address: IPv6地址字符串
            
        Returns:
            bool: 是否为回环地址
        """
        try:
            ipv6 = ipaddress.IPv6Address(address)
            return ipv6.is_loopback
        except ipaddress.AddressValueError:
            return False
    
    @staticmethod
    def is_ipv6_private(address: str) -> bool:
        """
        判断是否为IPv6私有地址
        
        Args:
            address: IPv6地址字符串
            
        Returns:
            bool: 是否为私有地址
        """
        try:
            ipv6 = ipaddress.IPv6Address(address)
            return ipv6.is_private
        except ipaddress.AddressValueError:
            return False
    
    @staticmethod
    def get_ipv6_scope_id(address: str) -> Optional[str]:
        """
        获取IPv6地址的scope ID（用于链路本地地址）
        
        Args:
            address: IPv6地址字符串（可能包含%interface）
            
        Returns:
            Optional[str]: scope ID，如果没有则返回None
        """
        if '%' in address:
            return address.split('%')[1]
        return None
    
    @staticmethod
    def remove_ipv6_scope_id(address: str) -> str:
        """
        移除IPv6地址的scope ID
        
        Args:
            address: IPv6地址字符串（可能包含%interface）
            
        Returns:
            str: 不包含scope ID的IPv6地址
        """
        if '%' in address:
            return address.split('%')[0]
        return address
    
    @staticmethod
    def format_ipv6_for_display(address: str) -> str:
        """
        格式化IPv6地址用于显示
        
        Args:
            address: IPv6地址字符串
            
        Returns:
            str: 格式化后的地址（添加方括号）
        """
        if IPv6Utils.is_valid_ipv6(address):
            return f"[{address}]"
        return address
    
    @staticmethod
    def parse_ipv6_from_display(display_address: str) -> str:
        """
        从显示格式解析IPv6地址
        
        Args:
            display_address: 显示格式的地址（可能包含方括号）
            
        Returns:
            str: 解析后的IPv6地址
        """
        address = display_address.strip()
        if address.startswith('[') and address.endswith(']'):
            return address[1:-1]
        return address
    
    @staticmethod
    def validate_ip_address(address: str) -> Tuple[bool, str]:
        """
        验证IP地址并返回详细信息
        
        Args:
            address: IP地址字符串
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not address:
            return False, "IP地址不能为空"
        
        version = IPv6Utils.get_ip_version(address)
        if version == IPVersion.UNKNOWN:
            return False, f"无效的IP地址格式: {address}"
        
        if version == IPVersion.IPv6:
            if IPv6Utils.is_ipv6_loopback(address):
                return True, "IPv6回环地址"
            elif IPv6Utils.is_ipv6_link_local(address):
                return True, "IPv6链路本地地址"
            elif IPv6Utils.is_ipv6_private(address):
                return True, "IPv6私有地址"
            else:
                return True, "IPv6全局地址"
        else:
            return True, "IPv4地址"
    
    @staticmethod
    def get_ip_address_info(address: str) -> dict:
        """
        获取IP地址的详细信息
        
        Args:
            address: IP地址字符串
            
        Returns:
            dict: IP地址信息字典
        """
        info = {
            'address': address,
            'version': IPVersion.UNKNOWN.value,
            'ip_version_name': 'Unknown',
            'is_valid': False,
            'is_loopback': False,
            'is_link_local': False,
            'is_private': False,
            'normalized': '',
            'display': '',
        }
        
        version = IPv6Utils.get_ip_version(address)
        if version == IPVersion.UNKNOWN:
            return info
        
        info['version'] = version.value
        info['is_valid'] = True
        
        if version == IPVersion.IPv6:
            info['ip_version_name'] = 'IPv6'
            try:
                ipv6 = ipaddress.IPv6Address(address)
                info['is_loopback'] = ipv6.is_loopback
                info['is_link_local'] = ipv6.is_link_local
                info['is_private'] = ipv6.is_private
                info['normalized'] = IPv6Utils.normalize_ipv6(address)
                info['display'] = IPv6Utils.format_ipv6_for_display(info['normalized'])
            except ipaddress.AddressValueError:
                pass
        else:
            info['ip_version_name'] = 'IPv4'
            try:
                ipv4 = ipaddress.IPv4Address(address)
                info['is_loopback'] = ipv4.is_loopback
                info['is_private'] = ipv4.is_private
                info['normalized'] = str(ipv4)
                info['display'] = info['normalized']
            except ipaddress.AddressValueError:
                pass
        
        return info


class IPv6AddressValidator:
    """IPv6地址验证器"""
    
    def __init__(self):
        self.utils = IPv6Utils()
    
    def validate_for_ssh(self, address: str) -> Tuple[bool, str]:
        """
        验证地址是否适合SSH连接
        
        Args:
            address: IP地址字符串
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        is_valid, message = IPv6Utils.validate_ip_address(address)
        if not is_valid:
            return False, message
        
        version = IPv6Utils.get_ip_version(address)
        if version == IPVersion.IPv6 and IPv6Utils.is_ipv6_link_local(address):
            return False, "链路本地地址需要指定网络接口"
        
        return True, "地址可用于SSH连接"
    
    def validate_for_telnet(self, address: str) -> Tuple[bool, str]:
        """
        验证地址是否适合Telnet连接
        
        Args:
            address: IP地址字符串
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        return self.validate_for_ssh(address)
    
    def get_connection_address(self, address: str, interface: Optional[str] = None) -> str:
        """
        获取用于连接的地址格式
        
        Args:
            address: IP地址字符串
            interface: 网络接口名称（用于链路本地地址）
            
        Returns:
            str: 连接地址
        """
        if IPv6Utils.is_valid_ipv6(address):
            if IPv6Utils.is_ipv6_link_local(address) and interface:
                return f"{address}%{interface}"
            return IPv6Utils.normalize_ipv6(address)
        return address


def create_ipv6_socket(address: str, port: int, timeout: float = 10.0) -> socket.socket:
    """
    创建支持IPv6的socket
    
    Args:
        address: IP地址字符串
        port: 端口号
        timeout: 超时时间
        
    Returns:
        socket.socket: 配置好的socket对象
    """
    family = IPv6Utils.get_socket_family(address)
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    return sock