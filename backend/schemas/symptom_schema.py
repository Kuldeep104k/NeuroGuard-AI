from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SymptomSignals(BaseModel):
    headache: bool = False
    severe_headache: bool = False
    dizziness: bool = False
    nausea: bool = False
    vomiting: bool = False
    fatigue: bool = False
    sleep_problems: bool = False
    cognitive_difficulty: bool = False
    light_sensitivity: bool = False
    noise_sensitivity: bool = False
    balance_problems: bool = False
    worsening: bool = False
    symptom_count: int = Field(default=0, ge=0)
    severity: str = Field(default="mild", pattern="^(mild|moderate|severe|unknown)$")
    onset_or_day: Optional[int] = Field(default=None, ge=0)
    raw_text: str = ""


class SymptomExtractionRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=5000)
