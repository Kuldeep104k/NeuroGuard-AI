from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.config import DATABASE_PATH, RETENTION_DAYS, STORE_RAW_INPUT
from backend.db.models import AssessmentLog


class Database:
    def __init__(self, path: Path = DATABASE_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_text TEXT NOT NULL,
                symptoms_json TEXT NOT NULL,
                risk_json TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                safe_json TEXT NOT NULL,
                explanation TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS llm_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
        self.delete_older_than(RETENTION_DAYS)

    def reserve_llm_call(self, max_rpm: int, max_rpd: int) -> bool:
        with sqlite3.connect(self.path, timeout=5.0) as connection:
            connection.execute("BEGIN IMMEDIATE")
            minute_count = connection.execute(
                "SELECT COUNT(*) FROM llm_usage WHERE created_at >= datetime('now', '-1 minute')"
            ).fetchone()[0]
            day_count = connection.execute(
                "SELECT COUNT(*) FROM llm_usage WHERE date(created_at) = date('now')"
            ).fetchone()[0]
            if minute_count >= max_rpm or day_count >= max_rpd:
                connection.rollback()
                return False
            connection.execute("INSERT INTO llm_usage DEFAULT VALUES")
            connection.commit()
            return True

    def log(self, log: AssessmentLog) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO assessments (input_text, symptoms_json, risk_json, plan_json, safe_json, explanation) VALUES (?, ?, ?, ?, ?, ?)",
                (log.input_text, log.symptoms_json, log.risk_json, log.plan_json, log.safe_json, log.explanation),
            )

    def log_response(self, input_text: str, response: dict) -> None:
        stored_input = input_text if STORE_RAW_INPUT else "[redacted by default]"
        symptoms = dict(response["symptoms"])
        symptoms.pop("raw_text", None)
        safety = response.get("safety", response.get("safe", {}))
        self.log(AssessmentLog(input_text=stored_input, symptoms_json=json.dumps(symptoms), risk_json=json.dumps(response["risk"]), plan_json=json.dumps(response["plan"]), safe_json=json.dumps(safety), explanation=response["explanation"]))

    def count(self) -> int:
        with sqlite3.connect(self.path) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM assessments").fetchone()[0])

    def delete_all(self) -> int:
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute("DELETE FROM assessments")
            connection.execute("DELETE FROM llm_usage")
            return int(cursor.rowcount)

    def usage_snapshot(self, max_rpm: int, max_rpd: int) -> dict[str, int]:
        with sqlite3.connect(self.path) as connection:
            minute_count = int(connection.execute(
                "SELECT COUNT(*) FROM llm_usage WHERE created_at >= datetime('now', '-1 minute')"
            ).fetchone()[0])
            day_count = int(connection.execute(
                "SELECT COUNT(*) FROM llm_usage WHERE date(created_at) = date('now')"
            ).fetchone()[0])
        return {
            "minute_used": minute_count,
            "minute_remaining": max(0, max_rpm - minute_count),
            "day_used": day_count,
            "day_remaining": max(0, max_rpd - day_count),
        }

    def delete_older_than(self, days: int) -> int:
        if days <= 0:
            return 0
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(
                "DELETE FROM assessments WHERE datetime(created_at) < datetime('now', ?)",
                (f"-{days} days",),
            )
            return int(cursor.rowcount)
