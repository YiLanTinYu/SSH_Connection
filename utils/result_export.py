#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Export structured AOMT execution results."""

import csv
import json
from datetime import datetime
from typing import Dict, Iterable, List

from openpyxl import Workbook


SUMMARY_HEADERS = [
    "设备名称", "分组", "标签", "IP 地址", "品牌", "型号",
    "状态", "开始时间", "结束时间", "总耗时(秒)",
    "连接准备耗时(秒)", "任务执行耗时(秒)", "命令数", "错误",
]
DETAIL_HEADERS = [
    "设备名称", "IP 地址", "命令序号", "命令", "输出", "执行时间", "耗时(秒)",
]


def _safe_cell(value):
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def summary_row(result: Dict) -> List:
    device = result.get("device_info", {}) or {}
    return [
        device.get("name", ""),
        device.get("group", ""),
        device.get("tags", ""),
        device.get("ip", ""),
        result.get("brand_detected") or device.get("brand", ""),
        result.get("model_detected", ""),
        "成功" if result.get("task_success") else "失败",
        result.get("started_at", ""),
        result.get("finished_at", ""),
        result.get("duration_seconds", ""),
        result.get("connection_duration_seconds", ""),
        result.get("operation_duration_seconds", ""),
        len(result.get("command_results", []) or []),
        result.get("error_message", "") or "",
    ]


def detail_rows(result: Dict) -> Iterable[List]:
    device = result.get("device_info", {}) or {}
    for index, item in enumerate(result.get("command_results", []) or [], start=1):
        yield [
            device.get("name", ""),
            device.get("ip", ""),
            index,
            item.get("command", ""),
            item.get("output", ""),
            item.get("timestamp", ""),
            item.get("duration_seconds", ""),
        ]


def export_results_csv(results: List[Dict], file_path: str) -> None:
    """Export one flat CSV containing a summary row followed by command rows."""
    headers = SUMMARY_HEADERS + ["命令序号", "命令", "输出", "命令时间", "命令耗时(秒)"]
    with open(file_path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        for result in results:
            summary = summary_row(result)
            commands = list(detail_rows(result))
            if not commands:
                writer.writerow([_safe_cell(value) for value in summary])
                continue
            for detail in commands:
                writer.writerow([
                    *[_safe_cell(value) for value in summary],
                    detail[2],
                    _safe_cell(detail[3]),
                    _safe_cell(detail[4]),
                    detail[5],
                    detail[6],
                ])


def export_results_xlsx(results: List[Dict], file_path: str) -> None:
    workbook = Workbook()
    summary = workbook.active
    summary.title = "执行摘要"
    summary.append(SUMMARY_HEADERS)
    for result in results:
        summary.append([_safe_cell(value) for value in summary_row(result)])

    details = workbook.create_sheet("命令明细")
    details.append(DETAIL_HEADERS)
    for result in results:
        for row in detail_rows(result):
            details.append([_safe_cell(value) for value in row])
    workbook.save(file_path)


def export_results_json(results: List[Dict], file_path: str) -> None:
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "results": results,
    }
    with open(file_path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
