from __future__ import annotations

import json
import re
from typing import Any

from backend.config import AI_MODE, MAX_LLM_RPD, MAX_LLM_RPM
from backend.db.database import Database
from backend.schemas.ai_schema import (
    UnifiedAIResponse,
    UnifiedPlan,
    UnifiedRisk,
    UnifiedSafety,
    UnifiedSymptoms,
)
from backend.schemas.risk_schema import HistoricalAssessment
from backend.schemas.symptom_schema import StructuredCheckIn
from backend.services.explainability import Explainability
from backend.services.guardrails import Guardrails
from backend.services.llm_client import LLMClient
from backend.services.planner import Planner
from backend.services.rag_engine import RAGEngine
from backend.services.risk_engine import RiskEngine
from backend.services.symptom_extractor import SymptomExtractor


UNIFIED_SYSTEM_PROMPT = """You are NeuroGuard AI, a conservative concussion recovery decision-support assistant.
Return only the requested JSON schema. Do not diagnose, prescribe medication, minimize danger, or advise ignoring clinicians.
Use the supplied local risk baseline and retrieved evidence. If danger signs appear, set safety.safe=false, provide an urgent alert,
set risk_level=high, and use stage 1. Recommendations must be exactly three concise strings."""


UNIFIED_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "symptoms": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "headache": {"type": "integer", "minimum": 0, "maximum": 10},
                "dizziness": {"type": "boolean"},
                "fatigue": {"type": "string", "enum": ["low", "medium", "high"]},
                "sleep_quality": {"type": "string", "enum": ["good", "poor"]},
                "mood": {"type": "string", "enum": ["calm", "anxious", "depressed"]},
            },
            "required": ["headache", "dizziness", "fatigue", "sleep_quality", "mood"],
        },
        "risk": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "risk_level": {"type": "string", "enum": ["low", "moderate", "high"]},
                "score": {"type": "number", "minimum": 0, "maximum": 100},
            },
            "required": ["risk_level", "score"],
        },
        "plan": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "stage": {"type": "integer", "minimum": 1, "maximum": 5},
                "recommendations": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 3,
                    "items": {"type": "string"},
                },
            },
            "required": ["stage", "recommendations"],
        },
        "explanation": {"type": "string"},
        "safety": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "safe": {"type": "boolean"},
                "alert": {"type": ["string", "null"]},
            },
            "required": ["safe", "alert"],
        },
    },
    "required": ["symptoms", "risk", "plan", "explanation", "safety"],
}


class UnifiedAIEngine:
    """One-request orchestrator: local preprocessing plus at most one LLM call."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        database: Database | None = None,
        extractor: SymptomExtractor | None = None,
        risk_engine: RiskEngine | None = None,
        rag: RAGEngine | None = None,
        planner: Planner | None = None,
        guardrails: Guardrails | None = None,
        explainability: Explainability | None = None,
    ) -> None:
        self.llm = llm or LLMClient()
        self.database = database or Database()
        self.extractor = extractor or SymptomExtractor()
        self.risk_engine = risk_engine or RiskEngine()
        self.rag = rag or RAGEngine()
        self.planner = planner or Planner(rag=self.rag)
        self.guardrails = guardrails or Guardrails()
        self.explainability = explainability or Explainability()
        self.last_mode = "local"
        self.last_llm_calls = 0

    def analyze(
        self,
        input_text: str,
        history: list[HistoricalAssessment] | None = None,
        day: int | None = None,
        structured_answers: StructuredCheckIn | None = None,
    ) -> UnifiedAIResponse:
        history = history or []
        local_symptoms = self.extractor.extract(input_text, structured_answers=structured_answers)
        local_risk = self.risk_engine.assess(local_symptoms, history)
        evidence = self.rag.retrieve(" ".join(local_risk.factors) + " " + input_text)
        self.last_mode = "local"
        self.last_llm_calls = 0

        model_result = None
        # Local mode is the safe default: it never contacts a hosted model and
        # therefore cannot consume quota. Hosted inference must be explicitly
        # enabled with NEUROGUARD_AI_MODE=openai.
        if AI_MODE == "openai" and self.llm.available and self.database.reserve_llm_call(MAX_LLM_RPM, MAX_LLM_RPD):
            self.last_llm_calls = 1
            try:
                model_result = self.llm.complete_structured(
                    UNIFIED_SYSTEM_PROMPT,
                    self._user_prompt(
                        input_text,
                        local_symptoms.model_dump(),
                        local_risk.model_dump(),
                        day,
                        evidence,
                        structured_answers.model_dump(exclude_none=True) if structured_answers else {},
                    ),
                    UNIFIED_JSON_SCHEMA,
                )
            except Exception:
                # Custom/provider adapters must not be able to break the
                # safety path or trigger a retry. The reserved call is spent,
                # and the deterministic fallback is returned.
                model_result = None
            if model_result:
                try:
                    model_result = UnifiedAIResponse.model_validate(model_result)
                    self.last_mode = "openai"
                except Exception:
                    model_result = None

        response = model_result or self._fallback(input_text, local_symptoms, local_risk, evidence, day)
        return self._apply_deterministic_safety(response, input_text, local_symptoms, local_risk, evidence)

    @staticmethod
    def _user_prompt(
        input_text: str,
        symptoms: dict,
        risk: dict,
        day: int | None,
        evidence: list[str],
        structured_answers: dict,
    ) -> str:
        payload = {
            "report": input_text,
            "day": day,
            "local_signals": symptoms,
            "local_risk_baseline": risk,
            "retrieved_evidence": evidence[:3],
            "structured_answers": structured_answers,
        }
        return json.dumps(payload, separators=(",", ":"))

    def _fallback(self, input_text, symptoms, risk, evidence, day) -> UnifiedAIResponse:
        local_plan = self.planner.create(symptoms, risk, day)
        emergency = self.guardrails.assess(symptoms, input_text=input_text)
        if emergency.emergency and emergency.escalation_message:
            recommendations = [
                emergency.escalation_message,
                "Stop sports, exercise, driving, and other activities with re-injury risk.",
                "Contact local emergency services if the person is severely impaired or cannot travel safely.",
            ]
            stage = 1
        else:
            recommendations = (local_plan.recommendations + local_plan.restrictions + local_plan.monitoring)[:3]
            while len(recommendations) < 3:
                recommendations.append("Monitor symptoms and seek professional guidance before progressing.")
            stage = local_plan.stage
        fatigue = symptoms.fatigue_level or ("high" if symptoms.fatigue and symptoms.symptom_count >= 3 else "medium" if symptoms.fatigue else "low")
        mood = symptoms.mood or ("depressed" if any(term in input_text.lower() for term in ("hopeless", "depressed", "sad")) else "anxious" if any(term in input_text.lower() for term in ("anxious", "anxiety", "worried")) else "calm")
        explanation = self.explainability.explain(symptoms, risk, evidence, stage=stage)
        headache_level = symptoms.headache_level
        if headache_level is not None and input_text.strip() and symptoms.headache:
            headache_level = max(headache_level, 10 if symptoms.severe_headache else 5)
        return UnifiedAIResponse(
            symptoms=UnifiedSymptoms(
                headache=headache_level if headache_level is not None else 10 if symptoms.severe_headache else 5 if symptoms.headache else 0,
                dizziness=symptoms.dizziness,
                fatigue=fatigue,
                sleep_quality=symptoms.sleep_quality or ("poor" if symptoms.sleep_problems else "good"),
                mood=mood,
            ),
            risk=UnifiedRisk(risk_level=risk.risk_level, score=risk.score),
            plan=UnifiedPlan(stage=stage, recommendations=recommendations),
            explanation=explanation,
            safety=UnifiedSafety(
                safe=not emergency.emergency,
                alert=emergency.escalation_message if emergency.emergency else None,
            ),
        )

    def _apply_deterministic_safety(self, response, input_text, symptoms, local_risk, evidence):
        generated = json.dumps(response.model_dump(), separators=(",", ":"))
        safety = self.guardrails.assess(symptoms, generated, input_text)
        if safety.emergency and safety.escalation_message:
            response.risk = UnifiedRisk(risk_level="high", score=100)
            response.plan = UnifiedPlan(
                stage=1,
                recommendations=[
                    safety.escalation_message,
                    "Stop sports, exercise, driving, and other activities with re-injury risk.",
                    "Contact local emergency services if the person is severely impaired or cannot travel safely.",
                ],
            )
            response.safety = UnifiedSafety(safe=False, alert=safety.escalation_message)
        elif not safety.safe or not response.safety.safe:
            response.safety = UnifiedSafety(
                safe=False,
                alert=response.safety.alert or "The response was blocked by the safety layer. Seek qualified professional guidance.",
            )
        response.explanation = self._synchronize_explanation_score(response.explanation, response.risk.risk_level, response.risk.score)
        source_suffix = " Evidence: " + " | ".join(evidence[:3])
        if source_suffix not in response.explanation:
            response.explanation = response.explanation.rstrip() + source_suffix
        return response

    @staticmethod
    def _synchronize_explanation_score(explanation: str, risk_level: str, score: float) -> str:
        """Keep the human-readable explanation aligned with the final guarded result."""
        score_text = f"{score:g}"
        replacement = f"The estimated risk is {risk_level} with a score of {score_text}/100"
        pattern = r"The estimated risk is [a-z]+ with a score of [0-9]+(?:\.[0-9]+)?/100"
        synchronized, count = re.subn(pattern, replacement, explanation, count=1, flags=re.IGNORECASE)
        if count:
            return synchronized
        return f"{replacement}. {explanation.lstrip()}"
