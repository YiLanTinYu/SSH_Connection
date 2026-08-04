#!/usr/bin/env python3
"""Report generated or sensitive artifacts before creating a release."""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


BLOCKED_PATTERNS = (
    "logs/*",
    "dist/*",
    "srbuild/*",
    "outputs/*",
    "captures/*",
    "test_data/*/*.json",
    "test_data/*/*.log",
    "test_data/*_encrypted.xlsx",
    "test_data/六台交换机同名脚本测试设备.xlsx",
    "*.pcap",
    "*.pcapng",
    "*.cfg",
    "nuitka-crash-report.xml",
)


def normalize_path(value: str) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def blocked_reason(path: str) -> str:
    normalized = normalize_path(path)
    name = Path(normalized).name.lower()
    for pattern in BLOCKED_PATTERNS:
        if fnmatch.fnmatch(normalized.lower(), pattern.lower()):
            if name.endswith("_encrypted.xlsx"):
                return "加密设备表不应进入发布提交"
            if name.endswith((".pcap", ".pcapng")):
                return "抓包文件可能包含敏感网络数据"
            if name.endswith(".cfg") or normalized.startswith("test_data/"):
                return "设备配置或运行备份不应进入发布提交"
            return "运行生成内容不应进入发布提交"
    return ""


def classify_paths(paths: Iterable[str]) -> List[Tuple[str, str]]:
    issues = []
    for path in sorted({normalize_path(item) for item in paths if item}):
        reason = blocked_reason(path)
        if reason:
            issues.append((path, reason))
    return issues


def review_reason(path: str) -> str:
    normalized = normalize_path(path).lower()
    if (
        normalized.startswith("test_data/")
        and normalized.endswith(".xlsx")
        and not normalized.endswith("_encrypted.xlsx")
    ):
        return "请人工确认仅包含虚拟设备和虚拟凭据"
    return ""


def review_paths(paths: Iterable[str]) -> List[Tuple[str, str]]:
    reviews = []
    for path in sorted({normalize_path(item) for item in paths if item}):
        reason = review_reason(path)
        if reason:
            reviews.append((path, reason))
    return reviews


def repository_paths(root: Path) -> List[str]:
    process = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return [path for path in process.stdout.split("\0") if path.strip()]


def main() -> int:
    root = Path(__file__).resolve().parent
    try:
        paths = repository_paths(root)
        issues = classify_paths(paths)
        reviews = review_paths(paths)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"发布检查无法读取 Git 文件列表: {exc}", file=sys.stderr)
        return 2

    if issues:
        print("发布检查未通过：")
        for path, reason in issues:
            print(f"- {path}: {reason}")
        print("请移出、删除或加入 .gitignore 后再创建发布版本。")
        return 1

    print("发布检查通过：未发现必须排除的运行或敏感文件。")
    if reviews:
        print("以下文件仍需人工确认：")
        for path, reason in reviews:
            print(f"- {path}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
