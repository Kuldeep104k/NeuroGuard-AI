from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AssessmentLog:
    input_text: str
    symptoms_json: str
    risk_json: str
    plan_json: str
    safe_json: str
    explanation: str
    created_at: datetime | None = None
