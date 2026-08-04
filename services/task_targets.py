"""Shared target synchronization for device jobs and maintenance tools."""

from typing import List


def sync_temporary_task_devices(
    manager,
    selected_devices: List,
    removed_devices=None,
) -> List:
    removed_ids = {id(device) for device in (removed_devices or [])}
    if removed_ids:
        for index in range(len(manager.get_devices()) - 1, -1, -1):
            device = manager.get_devices()[index]
            if id(device) in removed_ids:
                manager.remove_device(index)

    managed_by_key = {
        manager._device_key(device.ip, device.port): device
        for device in manager.get_devices()
    }
    synchronized = []
    for device in selected_devices:
        if getattr(device, "_aomt_ping_only", False):
            synchronized.append(device)
            continue
        key = manager._device_key(device.ip, device.port)
        managed = managed_by_key.get(key)
        if managed is None and getattr(device, "_aomt_temporary", False):
            if manager.add_device(device):
                managed_by_key[key] = device
                managed = device
        synchronized.append(managed or device)
    return synchronized


def valid_custom_task_targets(manager, targets: List) -> List:
    current_ids = {id(device) for device in manager.get_devices()}
    return [
        device
        for device in targets
        if getattr(device, "_aomt_ping_only", False)
        or id(device) in current_ids
    ]


def task_devices_for_mode(devices: List, mode: str = "") -> List:
    if mode == "ping":
        return list(devices)
    return [
        device
        for device in devices
        if not getattr(device, "_aomt_ping_only", False)
    ]


def describe_task_targets(scope: str, devices: List) -> str:
    if scope == "custom":
        ping_only = sum(
            bool(getattr(device, "_aomt_ping_only", False))
            for device in devices
        )
        detail = f"自定义目标：{len(devices)} 个"
        if ping_only:
            detail += f"（其中 Ping 网段地址 {ping_only} 个）"
        return detail
    labels = {
        "all": "全部设备",
        "filtered": "当前筛选结果",
        "selected": "设备表选中行",
    }
    return f"{labels.get(scope, '设备范围')}：{len(devices)} 台"
