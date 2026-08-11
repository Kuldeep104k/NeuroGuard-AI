from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.schemas.symptom_schema import StructuredCheckIn


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
    normal_plan_suppressed: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    escalation_message: str | None = None
    disclaimer: str


class AnalyzeRequest(BaseModel):
    input_text: str = Field(default="", max_length=5000)
    history: list[dict] = Field(default_factory=list)
    day: int | None = Field(default=None, ge=0, le=3650)
    structured_answers: StructuredCheckIn | None = None

    @model_validator(mode="after")
    def require_input(self):
        answer_values = self.structured_answers.model_dump(exclude_none=True) if self.structured_answers else {}
        has_answers = any(value not in (None, "", []) for value in answer_values.values())
        if not self.input_text.strip() and not has_answers:
            raise ValueError("Provide free-text symptoms or structured check-in answers.")
        return self


class AnalyzeResponse(BaseModel):
    symptoms: dict
    risk: dict
    plan: dict
    explanation: str
    safety: dict
