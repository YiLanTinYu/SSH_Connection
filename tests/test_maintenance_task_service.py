from datetime import datetime
from pathlib import Path

from services.maintenance_tasks import (
    diagnostic_result_counts,
    diagnostic_task_definition,
    maintenance_task_definition,
    save_maintenance_log,
)


def test_task_definitions_keep_user_facing_labels_and_log_prefixes():
    assert maintenance_task_definition("port").label == "批量端口检测"
    assert maintenance_task_definition("backup").log_prefix == "config_backup"
    assert diagnostic_task_definition("health_check").label == "一键设备巡检"
    assert diagnostic_task_definition("unknown").log_prefix == "diagnostics"


def test_diagnostic_result_counts_preserve_results_and_failures():
    results = [{"task_success": True}, {"task_success": False}, {}]
    items, success, failure = diagnostic_result_counts(results)
    assert items == results
    assert (success, failure) == (1, 2)


def test_save_maintenance_log_uses_timestamp_and_collision_suffix(tmp_path: Path):
    stamp = datetime(2026, 8, 3, 12, 34)
    first = save_maintenance_log(str(tmp_path), "port", ["第一行"], stamp)
    second = save_maintenance_log(str(tmp_path), "port", ["第二行"], stamp)

    assert Path(first).name == "port202608031234.log"
    assert Path(second).name == "port202608031234_1.log"
    assert Path(first).read_text(encoding="utf-8").strip() == "第一行"
    assert Path(second).read_text(encoding="utf-8").strip() == "第二行"
