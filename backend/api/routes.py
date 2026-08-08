from __future__ import annotations

from fastapi import APIRouter

from backend.db.database import Database
from backend.schemas.plan_schema import AnalyzeRequest, AnalyzeResponse
from backend.schemas.risk_schema import HistoricalAssessment
from backend.services.explainability import Explainability
from backend.services.guardrails import Guardrails
from backend.services.planner import Planner
from backend.services.rag_engine import RAGEngine
from backend.services.risk_engine import RiskEngine
from backend.services.symptom_extractor import SymptomExtractor


router = APIRouter()
extractor = SymptomExtractor()
risk_engine = RiskEngine()
rag = RAGEngine()
planner = Planner(rag=rag)
guardrails = Guardrails()
explainability = Explainability()
database = Database()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "neuroguard-ai"}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    symptoms = extractor.extract(request.input_text)
    history = [HistoricalAssessment.model_validate(item) for item in request.history]
    risk = risk_engine.assess(symptoms, history)
    plan = planner.create(symptoms, risk)
    generated = " ".join(plan.recommendations + plan.restrictions + [plan.escalation])
    safe = guardrails.assess(symptoms, generated)
    if safe.emergency and safe.escalation_message:
        plan.recommendations = [safe.escalation_message]
    plan.recommendations = [guardrails.sanitize(item) for item in plan.recommendations]
    evidence = rag.retrieve(request.input_text)
    explanation = explainability.explain(symptoms, risk, evidence)
    response = AnalyzeResponse(symptoms=symptoms.model_dump(), risk=risk.model_dump(), plan=plan.model_dump(), safe=safe.model_dump(), explanation=explanation)
    database.log_response(request.input_text, response.model_dump())
    return response
