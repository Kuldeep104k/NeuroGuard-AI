from __future__ import annotations

import re

from backend.config import DISCLAIMER
from backend.schemas.plan_schema import SafetyStatus
from backend.schemas.symptom_schema import SymptomSignals


UNSAFE_PATTERNS = (
    r"ignore (your )?doctor",
    r"self[- ]diagnos",
    r"you have no need to see",
    r"stop (taking|your) medication",
    r"push through (the )?pain",
    r"unsafe to drive",
    r"ignore (all )?(previous|prior) instructions",
    r"reveal (your )?(system|hidden) prompt",
    r"bypass (your )?safety",
    r"pretend you are",
)


class Guardrails:
    def assess(
        self,
        symptoms: SymptomSignals,
        generated_text: str = "",
        input_text: str = "",
    ) -> SafetyStatus:
        emergency_reasons: list[str] = []
        if symptoms.severe_headache and (symptoms.worsening or symptoms.headache):
            emergency_reasons.append("severe headache that is worsening or does not go away")
        if symptoms.repeated_vomiting or symptoms.vomiting:
            emergency_reasons.append("repeated vomiting")
        if symptoms.seizure:
            emergency_reasons.append("seizure or convulsion")
        if symptoms.loss_of_consciousness:
            emergency_reasons.append("loss of consciousness")
        if symptoms.unable_to_wake:
            emergency_reasons.append("inability to wake or stay awake")
        if symptoms.confusion:
            emergency_reasons.append("confusion or inability to recognize people or places")
        if symptoms.slurred_speech:
            emergency_reasons.append("slurred speech")
        if symptoms.weakness_or_numbness:
            emergency_reasons.append("weakness, numbness, or decreased coordination")
        if symptoms.unequal_pupils:
            emergency_reasons.append("unequal pupils or double vision")
        if symptoms.unusual_behavior:
            emergency_reasons.append("unusual behavior, agitation, or restlessness")
        if symptoms.worsening and "worsening condition" not in emergency_reasons:
            emergency_reasons.append("worsening condition")

        combined_text = f"{input_text}\n{generated_text}".lower()
        blocked = sorted({pattern for pattern in UNSAFE_PATTERNS if re.search(pattern, combined_text)})
        emergency = bool(emergency_reasons)
        escalation = None
        if emergency:
            escalation = (
                "Emergency warning signs may be present. Stop normal recovery activities and seek "
                "urgent medical assessment now. Call local emergency services if symptoms are severe, "
                "rapidly worsening, or the person cannot safely travel."
            )
        return SafetyStatus(
            safe=not blocked,
            emergency=emergency,
            normal_plan_suppressed=emergency,
            blocked_reasons=blocked,
            escalation_message=escalation,
            disclaimer=DISCLAIMER,
        )

    def sanitize(self, text: str) -> str:
        for pattern in UNSAFE_PATTERNS:
            text = re.sub(
                pattern,
                "contact a qualified healthcare professional",
                text,
                flags=re.IGNORECASE,
            )
        return text
