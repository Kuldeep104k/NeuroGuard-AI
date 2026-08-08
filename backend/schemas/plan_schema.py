from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RecoveryPlan(BaseModel):
    stage: int = Field(ge=1, le=5)
    stage_name: str
    recommendations: list[str] = Field(min_length=1)
    restrictions: list[str] = Field(default_factory=list)
    monitoring: list[str] = Field(default_factory=list)
    escalation: str
    disclaimer: str
    source_guidelines: list[str] = Field(default_factory=list)


class SafetyStatus(BaseModel):
    safe: bool
    emergency: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    escalation_message: str | None = None
    disclaimer: str


class AnalyzeRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=5000)
    history: list[dict] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    symptoms: dict
    risk: dict
    plan: dict
    safe: dict
    explanation: str
