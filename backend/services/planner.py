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
    1: ("Relative rest and medical evaluation", ["For the first 24-48 hours, use relative rest: continue essential daily activities as tolerated and take breaks when symptoms increase.", "Arrange professional medical evaluation for a possible concussion and prioritize regular sleep."], ["Avoid sports, driving when attention or reaction time is impaired, and fall/collision risk.", "Reduce screen and demanding cognitive activity early, but do not isolate in a dark room all day."]),
    2: ("Return to learning and light activity", ["Resume short, manageable school, work, or daily tasks with breaks and temporary accommodations as needed.", "Take brief, light walks if symptoms do not meaningfully worsen."], ["Stop or reduce activity if symptoms return or worsen.", "Avoid sports, heavy exertion, and fall/collision risk."]),
    3: ("Symptom-limited aerobic activity", ["Gradually increase light aerobic activity such as walking or stationary cycling while monitoring symptoms.", "Advance only when the current level is tolerated and symptoms return to baseline after activity."], ["Avoid contact, collision, and fall-risk activities.", "If symptoms increase more than mildly or remain elevated, step back and seek clinical guidance."]),
    4: ("Work- or sport-specific non-contact activity", ["Reintroduce more demanding non-contact work or sport-specific activity in small steps.", "Use a qualified healthcare professional to guide return-to-work or return-to-play decisions."], ["Do not progress when symptoms recur or worsen.", "No contact, collision, or high-risk activity until medically cleared."]),
    5: ("Full return with monitoring", ["Resume full regular activity only when symptom-free at rest and with exertion, following appropriate professional clearance.", "Continue monitoring for recurrence and maintain safe activity habits."], ["Stop and seek reassessment if symptoms return."]),
}


class Planner:
    def __init__(self, llm: LLMClient | None = None, rag: RAGEngine | None = None) -> None:
        self.llm = llm or LLMClient()
        self.rag = rag or RAGEngine()

    def create(self, symptoms: SymptomSignals, risk: RiskAssessment, day: int | None = None) -> RecoveryPlan:
        evidence_documents = self.rag.retrieve_documents(" ".join(risk.factors) + " " + symptoms.raw_text)
        evidence = [self.rag.format_citation(document) for document in evidence_documents]
        stage = self._select_stage(symptoms, risk, day)
        prompt = f"Symptoms: {symptoms.model_dump()}\nRisk: {risk.model_dump()}\nRecovery day: {day}\nGuidelines with sources: {evidence}"
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

    @property
    def mode(self) -> str:
        return "local"

    @staticmethod
    def _select_stage(symptoms: SymptomSignals, risk: RiskAssessment, day: int | None) -> int:
        if risk.risk_level == "high" or symptoms.worsening or symptoms.vomiting or symptoms.severe_headache:
            return 1
        if day is None:
            return 2 if risk.risk_level == "moderate" else 3 if symptoms.symptom_count else 5
        if day <= 2:
            return 1
        if day <= 4:
            return 2
        if day <= 7:
            return 5 if symptoms.symptom_count == 0 else 3 if symptoms.symptom_count == 1 else 2
        if symptoms.symptom_count:
            return 4
        return 5
