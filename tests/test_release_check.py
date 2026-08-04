from release_check import (
    blocked_reason,
    classify_paths,
    normalize_path,
    review_paths,
)

from pathlib import Path


def test_release_check_normalizes_windows_paths():
    assert normalize_path(r".\test_data\SW1\SW1.cfg") == (
        "test_data/SW1/SW1.cfg"
    )


def test_release_check_flags_sensitive_runtime_artifacts():
    paths = [
        "README.md",
        "test_data/SW1/SW1.cfg",
        "test_data/devices_encrypted.xlsx",
        "test_data/六台交换机同名脚本测试设备.xlsx",
        "captures/session.pcapng",
    ]
    issues = classify_paths(paths)
    assert [path for path, _reason in issues] == [
        "captures/session.pcapng",
        "test_data/SW1/SW1.cfg",
        "test_data/devices_encrypted.xlsx",
        "test_data/六台交换机同名脚本测试设备.xlsx",
    ]
    assert blocked_reason("README.md") == ""
    assert blocked_reason("test_data/per_device_scripts/SW1.txt") == ""


def test_release_check_requires_manual_review_for_plain_device_workbooks():
    reviews = review_paths([
        "test_data/virtual_devices.xlsx",
        "device_template.xlsx",
        "test_data/virtual_devices_encrypted.xlsx",
    ])
    assert reviews == [
        (
            "test_data/virtual_devices.xlsx",
            "请人工确认仅包含虚拟设备和虚拟凭据",
        )
    ]


def test_nuitka_build_stages_refactored_packages_and_dynamic_compat_module():
    build_script = (
        Path(__file__).resolve().parents[1] / "build.bat"
    ).read_text(encoding="utf-8")

    assert '"%PROJECT_DIR%\\controllers"' in build_script
    assert '"%PROJECT_DIR%\\services"' in build_script
    assert '--include-module=telnetlib_compat' in build_script
    assert 'import ui.main_window' in build_script
