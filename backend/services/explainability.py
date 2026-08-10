from __future__ import annotations

from backend.config import DISCLAIMER
from backend.schemas.risk_schema import RiskAssessment
from backend.schemas.symptom_schema import SymptomSignals


class Explainability:
    STAGE_CONTEXT = {
        1: "Early recovery prioritizes relative rest, sleep, evaluation, and avoiding re-injury while the brain and nervous system settle.",
        2: "Return-to-learn guidance reduces cognitive load and uses short, tolerable periods of school or work with breaks.",
        3: "Symptom-limited aerobic activity uses gradual exertion while monitoring whether symptoms return or meaningfully worsen.",
        4: "Work- or sport-specific progression increases task demand without contact or collision exposure until clinically cleared.",
        5: "Full return still includes monitoring because recurrence with exertion should prompt a pause and reassessment.",
    }

    def explain(
        self,
        symptoms: SymptomSignals,
        risk: RiskAssessment,
        guidelines: list[str],
        stage: int | None = None,
    ) -> str:
        factors = ", ".join(risk.factors) if risk.factors else "no major symptom risk factors detected"
        evidence = " ".join(guidelines[:2]) if guidelines else "general conservative recovery principles"
        stage_context = self.STAGE_CONTEXT.get(stage, "Recovery stage should be advanced gradually and guided by symptoms and cognitive function.")
        return (
            f"The estimated risk is {risk.risk_level} with a score of {risk.score}/100. "
            f"The main contributing factors were {factors}; the observed trend is {risk.trend}. "
            f"The recommended recovery stage is based on this principle: {stage_context} "
            f"The conservative plan is grounded in: {evidence}. {DISCLAIMER}"
        )
