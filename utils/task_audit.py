#!/usr/bin/env python3
"""Persistent, secret-free audit history for batch execution tasks."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional


def default_audit_path() -> str:
    overridden = os.environ.get("AOMT_TASK_HISTORY_PATH", "").strip()
    if overridden:
        return os.path.abspath(os.path.expanduser(overridden))
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return os.path.join(base, "AOMT", "task_history.db")


def preview_fingerprint(entries: Iterable[dict]) -> str:
    payload = [
        {
            "name": item.get("name", ""),
            "ip": item.get("ip", ""),
            "source": item.get("source", ""),
            "commands": list(item.get("commands", []) or []),
        }
        for item in entries
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class TaskAuditStore:
    def __init__(self, path: Optional[str] = None):
        self.path = os.path.abspath(path or default_audit_path())
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL DEFAULT '',
                    operator_name TEXT NOT NULL DEFAULT '',
                    task_type TEXT NOT NULL,
                    source_label TEXT NOT NULL DEFAULT '',
                    source_hash TEXT NOT NULL DEFAULT '',
                    target_count INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'running',
                    options_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS task_devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    device_name TEXT NOT NULL DEFAULT '',
                    ip TEXT NOT NULL DEFAULT '',
                    port INTEGER NOT NULL DEFAULT 22,
                    brand TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    duration_seconds REAL NOT NULL DEFAULT 0,
                    error_message TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_started_at
                    ON tasks(started_at DESC);
                CREATE INDEX IF NOT EXISTS idx_task_devices_task_id
                    ON task_devices(task_id);
                """
            )

    def start_task(
        self,
        task_type: str,
        source_label: str,
        source_hash: str,
        devices,
        options=None,
    ) -> int:
        started_at = datetime.now().isoformat(timespec="seconds")
        safe_options = dict(options or {})
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO tasks (
                    started_at, operator_name, task_type, source_label,
                    source_hash, target_count, options_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    started_at,
                    getpass.getuser(),
                    str(task_type or "batch_command"),
                    str(source_label or ""),
                    str(source_hash or ""),
                    len(devices),
                    json.dumps(safe_options, ensure_ascii=False, sort_keys=True),
                ),
            )
            task_id = int(cursor.lastrowid)
            db.executemany(
                """
                INSERT INTO task_devices (
                    task_id, device_name, ip, port, brand
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        task_id,
                        str(getattr(device, "name", "") or ""),
                        str(getattr(device, "ip", "") or ""),
                        int(getattr(device, "port", 22) or 22),
                        str(getattr(device, "brand", "") or ""),
                    )
                    for device in devices
                ],
            )
        return task_id

    def finish_task(self, task_id: int, results, status: str = "completed"):
        result_list = list(results or [])
        success = sum(bool(item.get("task_success")) for item in result_list)
        with self._connect() as db:
            task = db.execute(
                "SELECT target_count FROM tasks WHERE id = ?",
                (int(task_id),),
            ).fetchone()
        original_target_count = int(task["target_count"]) if task else 0
        target_count = max(original_target_count, len(result_list))
        failure = max(0, target_count - success)
        with self._connect() as db:
            for result in result_list:
                device = result.get("device_info", {}) or {}
                db.execute(
                    """
                    UPDATE task_devices
                    SET model = ?, status = ?, duration_seconds = ?,
                        error_message = ?
                    WHERE task_id = ? AND ip = ? AND port = ?
                    """,
                    (
                        str(result.get("model_detected", "") or ""),
                        "success" if result.get("task_success") else "failed",
                        float(result.get("duration_seconds") or 0),
                        str(result.get("error_message", "") or ""),
                        int(task_id),
                        str(device.get("ip", "") or ""),
                        int(device.get("port", 22) or 22),
                    ),
                )
            db.execute(
                """
                UPDATE tasks
                SET finished_at = ?, target_count = ?, success_count = ?,
                    failure_count = ?, status = ?
                WHERE id = ?
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    target_count,
                    success,
                    failure,
                    str(status or "completed"),
                    int(task_id),
                ),
            )

    def list_tasks(self, limit: int = 500) -> List[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM tasks ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def task_detail(self, task_id: int) -> dict:
        with self._connect() as db:
            task = db.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (int(task_id),),
            ).fetchone()
            devices = db.execute(
                """
                SELECT * FROM task_devices
                WHERE task_id = ? ORDER BY id
                """,
                (int(task_id),),
            ).fetchall()
        return {
            "task": dict(task) if task else {},
            "devices": [dict(row) for row in devices],
        }
