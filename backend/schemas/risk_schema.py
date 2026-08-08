from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "moderate", "high"]


class HistoricalAssessment(BaseModel):
    day: int = Field(ge=0)
    score: float = Field(ge=0)
    risk_level: RiskLevel


class RiskAssessment(BaseModel):
    risk_level: RiskLevel
    score: float = Field(ge=0, le=100)
    factors: list[str] = Field(default_factory=list)
    trend: str = "stable"
