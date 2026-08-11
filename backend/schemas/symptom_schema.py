from __future__ import annotations

from typing import Literal, Optional

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
    seizure: bool = False
    loss_of_consciousness: bool = False
    confusion: bool = False
    weakness_or_numbness: bool = False
    slurred_speech: bool = False
    unequal_pupils: bool = False
    unable_to_wake: bool = False
    unusual_behavior: bool = False
    repeated_vomiting: bool = False
    symptom_count: int = Field(default=0, ge=0)
    severity: str = Field(default="mild", pattern="^(mild|moderate|severe|unknown)$")
    onset_or_day: Optional[int] = Field(default=None, ge=0)
    raw_text: str = ""
    headache_level: int | None = Field(default=None, ge=0, le=10)
    fatigue_level: Literal["low", "medium", "high"] | None = None
    sleep_quality: Literal["good", "poor"] | None = None
    mood: Literal["calm", "anxious", "depressed"] | None = None
    symptom_change: Literal["improving", "stable", "worsening"] | None = None
    activity_response: Literal["tolerated", "worsened", "not_tried"] | None = None


class StructuredCheckIn(BaseModel):
    """Optional direct observations that disambiguate free-text language."""

    headache_level: int | None = Field(default=None, ge=0, le=10)
    dizziness: bool | None = None
    fatigue: Literal["low", "medium", "high"] | None = None
    sleep_quality: Literal["good", "poor"] | None = None
    mood: Literal["calm", "anxious", "depressed"] | None = None
    symptom_change: Literal["improving", "stable", "worsening"] | None = None
    activity_response: Literal["tolerated", "worsened", "not_tried"] | None = None
    vomiting: Literal["none", "once", "repeated"] | None = None
    emergency_signs: list[
        Literal[
            "seizure",
            "loss_of_consciousness",
            "confusion",
            "slurred_speech",
            "weakness_or_numbness",
            "unequal_pupils",
            "unable_to_wake",
            "repeated_vomiting",
        ]
    ] = Field(default_factory=list, max_length=8)


class SymptomExtractionRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=5000)
