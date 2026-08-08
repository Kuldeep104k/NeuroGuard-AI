from __future__ import annotations

from backend.config import DISCLAIMER
from backend.schemas.risk_schema import RiskAssessment
from backend.schemas.symptom_schema import SymptomSignals


class Explainability:
    def explain(self, symptoms: SymptomSignals, risk: RiskAssessment, guidelines: list[str]) -> str:
        factors = ", ".join(risk.factors) if risk.factors else "no major symptom risk factors detected"
        evidence = " ".join(guidelines[:2]) if guidelines else "general conservative recovery principles"
        return (
            f"The estimated risk is {risk.risk_level} with a score of {risk.score}/100. "
            f"The main contributing factors were {factors}; the observed trend is {risk.trend}. "
            f"The conservative plan is grounded in: {evidence}. {DISCLAIMER}"
        )
