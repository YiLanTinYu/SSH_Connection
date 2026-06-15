#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
设备信息配置模块
支持手动输入和Excel批量导入
支持IPv4和IPv6地址
"""

from typing import List, Dict, Optional
import os
import json
import sys
from openpyxl import Workbook, load_workbook

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ipv6_utils import IPv6Utils, IPVersion, IPv6AddressValidator


class DeviceInfo:
    """设备信息类（支持IPv4和IPv6）"""
    
    def __init__(self, brand: str = '', ip: str = '', port: int = 22, 
                 username: str = '', password: str = '', name: str = ''):
        self.brand = brand
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.name = name or f"{brand}_{ip}"
        
        # IPv6相关属性
        self.ip_version = IPVersion.UNKNOWN
        self.ipv6_validator = IPv6AddressValidator()
        
        # 验证IP地址并记录版本
        if ip:
            self.ip_version = IPv6Utils.get_ip_version(ip)
    
    def validate_ip_address(self) -> tuple:
        """
        验证IP地址
        
        Returns:
            tuple: (是否有效, 错误信息)
        """
        if not self.ip:
            return False, "IP地址不能为空"
        
        return self.ipv6_validator.validate_for_ssh(self.ip)
    
    def get_ip_info(self) -> dict:
        """
        获取IP地址的详细信息
        
        Returns:
            dict: IP地址信息
        """
        return IPv6Utils.get_ip_address_info(self.ip)
    
    def get_display_address(self) -> str:
        """
        获取用于显示的地址格式
        
        Returns:
            str: 显示格式的地址
        """
        return IPv6Utils.format_ipv6_for_display(self.ip)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.name,
            'brand': self.brand,
            'ip': self.ip,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'ip_version': self.ip_version.value if self.ip_version else 0,
            'ip_version_name': 'IPv6' if self.ip_version == IPVersion.IPv6 else 'IPv4' if self.ip_version == IPVersion.IPv4 else 'Unknown',
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DeviceInfo':
        """从字典创建"""
        device = cls(
            brand=data.get('brand', ''),
            ip=data.get('ip', ''),
            port=data.get('port', 22),
            username=data.get('username', ''),
            password=data.get('password', ''),
            name=data.get('name', ''),
        )
        
        # 恢复IP版本信息
        if 'ip_version' in data:
            version = data['ip_version']
            if version == 6:
                device.ip_version = IPVersion.IPv6
            elif version == 4:
                device.ip_version = IPVersion.IPv4
        
        return device
    
    def __str__(self) -> str:
        ip_display = self.get_display_address()
        version_info = f" [{self.ip_version.value}]" if self.ip_version != IPVersion.UNKNOWN else ""
        return f"DeviceInfo({self.name}, {ip_display}:{self.port}{version_info})"
    
    def __repr__(self) -> str:
        return self.__str__()


class DeviceConfigManager:
    """设备配置管理器"""
    
    def __init__(self):
        self.devices: List[DeviceInfo] = []
        self.last_import_skipped_count = 0
        self.last_import_skipped = []

    @staticmethod
    def _device_key(ip: str, port: int = 22) -> tuple:
        ip = str(ip or '').strip()
        version = IPv6Utils.get_ip_version(ip)
        if version == IPVersion.IPv6:
            ip = IPv6Utils.remove_ipv6_scope_id(ip)
            ip = IPv6Utils.normalize_ipv6(ip).lower()
        else:
            ip = ip.lower()
        return ip, int(port or 22)

    def has_device(self, ip: str, port: int = 22) -> bool:
        key = self._device_key(ip, port)
        return any(self._device_key(device.ip, device.port) == key for device in self.devices)
    
    def add_device(self, device: DeviceInfo):
        """Add one device, skipping duplicate IP+port entries."""
        if self.has_device(device.ip, device.port):
            return False
        self.devices.append(device)
        return True
    
    def add_device_manual(self, brand: str, ip: str, port: int = 22, 
                          username: str = '', password: str = '', name: str = ''):
        """手动添加设备"""
        device = DeviceInfo(brand, ip, port, username, password, name)
        self.add_device(device)
    
    @staticmethod
    def _clean_excel_value(value, default: str = '') -> str:
        """Return a safe string for Excel cells, treating NaN/blank as default."""
        if value is None:
            return default
        value = str(value).strip()
        if value.lower() in ('nan', 'none'):
            return default
        return value

    @staticmethod
    def _clean_excel_port(value, default: int = 22) -> int:
        """Normalize an Excel port cell and validate the TCP port range."""
        if value is None or str(value).strip() == '':
            return default
        try:
            port = int(float(value))
        except (TypeError, ValueError):
            raise ValueError('port must be a number between 1 and 65535')
        if not 1 <= port <= 65535:
            raise ValueError('port must be between 1 and 65535')
        return port

    def import_from_excel(self, file_path: str) -> tuple:
        """Import devices from Excel with required-field and IP validation."""
        success_count = 0
        error_count = 0
        errors = []
        self.last_import_skipped_count = 0
        self.last_import_skipped = []
        
        try:
            workbook = load_workbook(file_path, read_only=True, data_only=True)
            sheet = workbook.active
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                errors.append("Excel file is empty")
                return 0, 0, errors

            headers = [self._clean_excel_value(value).lower() for value in rows[0]]
            data_rows = rows[1:]
            required_columns = ['ip', 'username', 'password']
            missing_columns = [col for col in required_columns if col not in headers]
            
            if missing_columns:
                errors.append(f"Excel file missing required columns: {missing_columns}")
                return 0, len(data_rows), errors

            header_index = {name: index for index, name in enumerate(headers) if name}
            
            for index, values in enumerate(data_rows):
                row_no = index + 2
                row = {
                    name: values[col_index] if col_index < len(values) else None
                    for name, col_index in header_index.items()
                }
                try:
                    brand = self._clean_excel_value(row.get('brand'), 'h3c').lower()
                    ip = self._clean_excel_value(row.get('ip'))
                    port = self._clean_excel_port(row.get('port'), 22)
                    username = self._clean_excel_value(row.get('username'))
                    password = self._clean_excel_value(row.get('password'))
                    name = self._clean_excel_value(row.get('name'))

                    if not ip:
                        raise ValueError('ip is required')
                    if not username:
                        raise ValueError('username is required')
                    if not password:
                        raise ValueError('password is required')

                    device = DeviceInfo(brand, ip, port, username, password, name)
                    is_valid, error_msg = device.validate_ip_address()
                    if not is_valid:
                        raise ValueError(f'invalid IP address: {error_msg}')

                    if not self.add_device(device):
                        self.last_import_skipped_count += 1
                        self.last_import_skipped.append(f"Row {row_no}: duplicate {ip}:{port}")
                        continue
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {row_no} import failed: {str(e)}")
                    
        except Exception as e:
            errors.append(f"Excel file read failed: {str(e)}")
            error_count = 1
        
        return success_count, error_count, errors

    def export_to_excel(self, file_path: str) -> bool:
        """
        导出设备信息到Excel
        
        Args:
            file_path: 输出文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            workbook = Workbook()
            sheet = workbook.active
            headers = ['name', 'brand', 'ip', 'port', 'username', 'password', 'ip_version', 'ip_version_name']
            sheet.append(headers)
            for device in self.devices:
                data = device.to_dict()
                sheet.append([data.get(header, '') for header in headers])
            workbook.save(file_path)
            return True
        except Exception as e:
            print(f"导出失败: {str(e)}")
            return False
    
    def save_to_json(self, file_path: str) -> bool:
        """保存到JSON文件"""
        try:
            data = [device.to_dict() for device in self.devices]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存失败: {str(e)}")
            return False
    
    def load_from_json(self, file_path: str) -> bool:
        """从JSON文件加载"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.devices = [DeviceInfo.from_dict(item) for item in data]
            return True
        except Exception as e:
            print(f"加载失败: {str(e)}")
            return False
    
    def get_devices(self) -> List[DeviceInfo]:
        """获取所有设备"""
        return self.devices
    
    def clear_devices(self):
        """清空设备列表"""
        self.devices.clear()
    
    def remove_device(self, index: int):
        """移除指定设备"""
        if 0 <= index < len(self.devices):
            self.devices.pop(index)
    
    def get_device_count(self) -> int:
        """获取设备数量"""
        return len(self.devices)
    
    def create_template_excel(self, file_path: str) -> bool:
        """创建设备信息模板Excel"""
        try:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "devices"
            sheet.append(['name', 'brand', 'ip', 'port', 'username', 'password'])
            sheet.append(['设备1', 'h3c', '192.168.1.1', 22, 'admin', 'password1'])
            sheet.append(['设备2', 'huawei', '192.168.1.2', 22, 'admin', 'password2'])
            workbook.save(file_path)
            return True
        except Exception as e:
            print(f"创建模板失败: {str(e)}")
            return False
