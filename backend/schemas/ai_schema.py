from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class UnifiedSymptoms(BaseModel):
    headache: int = Field(ge=0, le=10)
    dizziness: bool
    fatigue: Literal["low", "medium", "high"]
    sleep_quality: Literal["good", "poor"]
    mood: Literal["calm", "anxious", "depressed"]


class UnifiedRisk(BaseModel):
    risk_level: Literal["low", "moderate", "high"]
    score: float = Field(ge=0, le=100)


class UnifiedPlan(BaseModel):
    stage: int = Field(ge=1, le=5)
    recommendations: list[str] = Field(min_length=3, max_length=3)


class UnifiedSafety(BaseModel):
    safe: bool
    alert: str | None = None


class UnifiedAIResponse(BaseModel):
    symptoms: UnifiedSymptoms
    risk: UnifiedRisk
    plan: UnifiedPlan
    explanation: str = Field(min_length=1, max_length=4000)
    safety: UnifiedSafety
