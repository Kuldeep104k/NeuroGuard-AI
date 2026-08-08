from __future__ import annotations

import re

from backend.config import DISCLAIMER
from backend.schemas.plan_schema import SafetyStatus
from backend.schemas.symptom_schema import SymptomSignals


UNSAFE_PATTERNS = (
    r"ignore (your )?doctor", r"self[- ]diagnos", r"you have no need to see",
    r"stop (taking|your) medication", r"push through (the )?pain", r"unsafe to drive",
)


class Guardrails:
    def assess(self, symptoms: SymptomSignals, generated_text: str = "") -> SafetyStatus:
        emergency_reasons: list[str] = []
        if symptoms.severe_headache:
            emergency_reasons.append("severe headache after injury")
        if symptoms.vomiting:
            emergency_reasons.append("vomiting after injury")
        if symptoms.worsening:
            emergency_reasons.append("worsening condition")
        blocked = [pattern for pattern in UNSAFE_PATTERNS if re.search(pattern, generated_text.lower())]
        emergency = bool(emergency_reasons)
        escalation = None
        if emergency:
            escalation = "Seek urgent medical assessment now. If symptoms are severe, rapidly worsening, or you cannot safely travel, contact local emergency services."
        return SafetyStatus(
            safe=not blocked,
            emergency=emergency,
            blocked_reasons=blocked,
            escalation_message=escalation,
            disclaimer=DISCLAIMER,
        )

    def sanitize(self, text: str) -> str:
        for pattern in UNSAFE_PATTERNS:
            text = re.sub(pattern, "contact a qualified healthcare professional", text, flags=re.IGNORECASE)
        return text
