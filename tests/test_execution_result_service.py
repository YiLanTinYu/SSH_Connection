from services.execution_results import (
    execution_audit_status,
    result_status_text,
    summarize_connections,
    upsert_execution_result,
)


def _result(ip, connected, port=22, **extra):
    return {
        "device_info": {"ip": ip, "port": port},
        "is_connected": connected,
        **extra,
    }


def test_upsert_execution_result_replaces_same_device_and_keeps_others():
    old = _result("192.0.2.1", False)
    other = _result("192.0.2.2", True)
    new = _result("192.0.2.1", True, brand_detected="h3c")
    assert upsert_execution_result([old, other], new) == [other, new]


def test_result_status_text_handles_brand_and_truncates_errors():
    assert result_status_text(_result("192.0.2.1", True, brand_detected="h3c")) == (
        "✔ 成功  h3c"
    )
    failed = _result("192.0.2.1", False, error_message="x" * 40)
    assert result_status_text(failed) == "✘ " + "x" * 30 + "..."


def test_connection_summary_and_audit_status():
    results = [
        _result("192.0.2.1", True),
        _result("192.0.2.2", False, error_message="用户取消"),
    ]
    summary = summarize_connections(results)
    assert (summary.total, summary.success, summary.failure) == (2, 1, 1)
    assert summary.success_rate == 50.0
    assert "成功率: 50.0%" in summary.message()
    assert execution_audit_status(results) == "cancelled"
    assert execution_audit_status([results[0]]) == "completed"
