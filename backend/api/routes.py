from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Response

from backend.config import ADMIN_TOKEN, AI_MODE, MAX_LLM_RPD, MAX_LLM_RPM
from backend.db.database import Database
from backend.schemas.ai_schema import UnifiedAIResponse
from backend.schemas.plan_schema import AnalyzeRequest
from backend.schemas.risk_schema import HistoricalAssessment
from backend.services.unified_ai_engine import UnifiedAIEngine


router = APIRouter()
database = Database()
unified_engine = UnifiedAIEngine(database=database)


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "neuroguard-ai",
        "ai_mode": AI_MODE,
        "llm_policy": "max_one_call_per_request",
    }


@router.delete("/privacy/logs")
def delete_logs(x_admin_token: str | None = Header(default=None)) -> dict[str, int]:
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Privacy deletion endpoint is not configured.")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid privacy administration token.")
    return {"deleted": database.delete_all()}


@router.get("/usage")
def usage(x_admin_token: str | None = Header(default=None)) -> dict[str, int | str]:
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Usage endpoint is not configured.")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid privacy administration token.")
    snapshot = database.usage_snapshot(MAX_LLM_RPM, MAX_LLM_RPD)
    return {"ai_mode": AI_MODE, **snapshot}


@router.post("/analyze", response_model=UnifiedAIResponse)
def analyze(request: AnalyzeRequest, response: Response) -> UnifiedAIResponse:
    history = [HistoricalAssessment.model_validate(item) for item in request.history]
    result = unified_engine.analyze(request.input_text, history=history, day=request.day)
    response.headers["X-NeuroGuard-AI-Mode"] = unified_engine.last_mode
    response.headers["X-NeuroGuard-LLM-Calls"] = str(unified_engine.last_llm_calls)
    response.headers["X-NeuroGuard-Rate-Limit"] = "10-rpm;50-rpd"
    if unified_engine.last_llm_calls and unified_engine.last_mode == "local":
        response.headers["X-NeuroGuard-LLM-Status"] = "fallback"
    payload = result.model_dump()
    database.log_response(request.input_text, payload)
    return UnifiedAIResponse(**payload)
