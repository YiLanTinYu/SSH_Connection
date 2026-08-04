"""Normalization and summaries for batch SSH execution results."""

from dataclasses import dataclass


def result_device_key(result: dict) -> tuple:
    device = result.get("device_info", {}) or {}
    return device.get("ip", ""), int(device.get("port", 22) or 22)


def upsert_execution_result(results, result: dict) -> list:
    key = result_device_key(result)
    updated = [item for item in results if result_device_key(item) != key]
    updated.append(result)
    return updated


def result_status_text(result: dict) -> str:
    if result.get("is_connected", False):
        brand = result.get("brand_detected", "") or ""
        return f"✔ 成功  {brand}" if brand else "✔ 连接成功"
    error = result.get("error_message", "") or ""
    short_error = error[:30] + "..." if len(error) > 30 else error
    return f"✘ {short_error}"


@dataclass(frozen=True)
class ConnectionSummary:
    total: int
    success: int
    failure: int
    success_rate: float

    def message(self) -> str:
        return (
            "连接任务完成！\n\n"
            f"  总数: {self.total} 台\n"
            f"  成功: {self.success} 台\n"
            f"  失败: {self.failure} 台\n"
            f"  成功率: {self.success_rate:.1f}%"
        )


def summarize_connections(results, fallback_total: int = 0) -> ConnectionSummary:
    items = list(results or [])
    total = len(items) or int(fallback_total)
    success = sum(bool(item.get("is_connected")) for item in items)
    failure = max(0, total - success)
    rate = success / total * 100 if total else 0.0
    return ConnectionSummary(total, success, failure, rate)


def execution_audit_status(results) -> str:
    cancelled = any(
        "取消" in str(result.get("error_message", "") or "")
        for result in (results or [])
    )
    return "cancelled" if cancelled else "completed"
