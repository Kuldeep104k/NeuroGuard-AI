from __future__ import annotations

from backend.config import DISCLAIMER
from backend.schemas.plan_schema import RecoveryPlan
from backend.schemas.risk_schema import RiskAssessment
from backend.schemas.symptom_schema import SymptomSignals
from backend.services.llm_client import LLMClient
from backend.services.rag_engine import RAGEngine


PLANNER_SYSTEM_PROMPT = """You create conservative concussion recovery guidance. You are not a doctor.
Use only the provided symptoms, risk, and retrieved guidelines. Recommend staged recovery (1-5),
avoid diagnosis and medication instructions, include escalation guidance, and return JSON matching RecoveryPlan."""


STAGES = {
    1: ("Rest and stabilization", ["Rest physically and cognitively; keep activity below the level that worsens symptoms.", "Prioritize regular sleep and hydration."], ["Avoid driving, sports, and high-risk activity.", "Limit screens and other stimulating activity early in recovery."]),
    2: ("Light daily activity", ["Try short, light daily tasks only if symptoms remain stable.", "Take frequent rest breaks."], ["Stop and step back if symptoms worsen.", "Avoid strenuous exercise and contact activity."]),
    3: ("Moderate activity", ["Gradually increase light aerobic or routine activity while monitoring symptoms.", "Keep increases small and spaced out."], ["Avoid contact, collision, or fall-risk activities."]),
    4: ("Sport or work-specific activity", ["Reintroduce more demanding, non-contact activity gradually.", "Use professional guidance for return-to-work or return-to-play decisions."], ["Do not progress while symptoms return or worsen."]),
    5: ("Full activity", ["Resume full activity only after symptoms have resolved and a qualified clinician has cleared the transition when appropriate.", "Continue monitoring for recurrence."], ["Avoid high-risk activity if symptoms return."]),
}


class Planner:
    def __init__(self, llm: LLMClient | None = None, rag: RAGEngine | None = None) -> None:
        self.llm = llm or LLMClient()
        self.rag = rag or RAGEngine()

    def create(self, symptoms: SymptomSignals, risk: RiskAssessment) -> RecoveryPlan:
        evidence = self.rag.retrieve(" ".join(risk.factors) + " " + symptoms.raw_text)
        stage = 1 if risk.risk_level == "high" else 2 if risk.risk_level == "moderate" else 4
        prompt = f"Symptoms: {symptoms.model_dump()}\nRisk: {risk.model_dump()}\nGuidelines: {evidence}"
        result = self.llm.complete_json(PLANNER_SYSTEM_PROMPT, prompt)
        if result:
            try:
                return RecoveryPlan.model_validate({**result, "disclaimer": DISCLAIMER, "source_guidelines": evidence})
            except Exception:
                pass
        name, recommendations, restrictions = STAGES[stage]
        return RecoveryPlan(
            stage=stage,
            stage_name=name,
            recommendations=recommendations,
            restrictions=restrictions,
            monitoring=["Track symptoms daily and note any worsening.", "Progress only when the current activity is tolerated without symptom worsening."],
            escalation="Seek medical attention for severe headache, vomiting, worsening symptoms, new neurological symptoms, or any concern about safety.",
            disclaimer=DISCLAIMER,
            source_guidelines=evidence,
        )
