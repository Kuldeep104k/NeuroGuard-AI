from __future__ import annotations

from collections.abc import Iterable

from backend.schemas.risk_schema import HistoricalAssessment, RiskAssessment
from backend.schemas.symptom_schema import SymptomSignals


class RiskEngine:
    """Conservative, explainable symptom scoring with optional history trend detection."""

    def assess(self, symptoms: SymptomSignals, history: Iterable[HistoricalAssessment] = ()) -> RiskAssessment:
        weights = {
            "severe_headache": 45, "vomiting": 40, "worsening": 30, "dizziness": 12,
            "balance_problems": 12, "cognitive_difficulty": 12, "headache": 10,
            "nausea": 8, "fatigue": 5, "sleep_problems": 5, "light_sensitivity": 5,
            "noise_sensitivity": 5, "seizure": 100, "loss_of_consciousness": 100,
            "confusion": 80, "weakness_or_numbness": 100, "slurred_speech": 100,
            "unequal_pupils": 100, "unable_to_wake": 100, "unusual_behavior": 80,
            "repeated_vomiting": 100,
        }
        score = min(100, sum(weight for name, weight in weights.items() if getattr(symptoms, name)))
        factors = [name.replace("_", " ") for name, weight in weights.items() if getattr(symptoms, name) and weight >= 8]
        prior = list(history)
        trend = "stable"
        if prior:
            previous = prior[-1].score
            if score > previous + 5:
                trend = "worsening"
                score = min(100, score + 10)
                factors.append("worsening trend compared with history")
            elif score < previous - 5:
                trend = "improving"
        if symptoms.severity == "severe" or any(
            getattr(symptoms, name)
            for name in (
                "seizure", "loss_of_consciousness", "weakness_or_numbness",
                "slurred_speech", "unequal_pupils", "unable_to_wake",
                "repeated_vomiting",
            )
        ):
            score = max(score, 70)
        level = "high" if score >= 50 else "moderate" if score >= 20 else "low"
        return RiskAssessment(risk_level=level, score=round(float(score), 1), factors=factors, trend=trend)
