from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.config import DATABASE_PATH
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

    def log(self, log: AssessmentLog) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO assessments (input_text, symptoms_json, risk_json, plan_json, safe_json, explanation) VALUES (?, ?, ?, ?, ?, ?)",
                (log.input_text, log.symptoms_json, log.risk_json, log.plan_json, log.safe_json, log.explanation),
            )

    def log_response(self, input_text: str, response: dict) -> None:
        self.log(AssessmentLog(input_text=input_text, symptoms_json=json.dumps(response["symptoms"]), risk_json=json.dumps(response["risk"]), plan_json=json.dumps(response["plan"]), safe_json=json.dumps(response["safe"]), explanation=response["explanation"]))
