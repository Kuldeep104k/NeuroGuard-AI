from __future__ import annotations

import re

from backend.schemas.symptom_schema import SymptomSignals
from backend.services.llm_client import LLMClient


SYSTEM_PROMPT = """You are a clinical safety assistant. Extract only symptoms explicitly supported by the text.
Return JSON matching the SymptomSignals schema. Never diagnose, minimize danger, or invent facts."""


class SymptomExtractor:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def extract(self, text: str) -> SymptomSignals:
        result = self.llm.complete_json(SYSTEM_PROMPT, f"Extract signals from this report:\n{text}")
        if result:
            try:
                return SymptomSignals.model_validate({**result, "raw_text": text})
            except Exception:
                pass
        return self._local_extract(text)

    def _local_extract(self, text: str) -> SymptomSignals:
        lower = text.lower()

        def has(*terms: str) -> bool:
            return any(term in lower for term in terms)

        signals = {
            "headache": has("headache", "head pain", "migraine"),
            "severe_headache": has("severe headache", "worst headache", "extreme headache"),
            "dizziness": has("dizz", "vertigo", "off balance"),
            "nausea": has("nausea", "queasy"),
            "vomiting": has("vomit", "throwing up"),
            "fatigue": has("tired", "fatigue", "exhausted", "low energy"),
            "sleep_problems": has("poor sleep", "insomnia", "sleep problem", "sleeping poorly"),
            "cognitive_difficulty": has("confus", "concentrat", "memory", "brain fog", "slow thinking"),
            "light_sensitivity": has("light sensitive", "sensitive to light", "photophobia"),
            "noise_sensitivity": has("noise sensitive", "sensitive to noise", "sound sensitive"),
            "balance_problems": has("balance", "unsteady", "stumbling"),
            "worsening": has("worsening", "getting worse", "worse", "deteriorat"),
        }
        explicit_no_symptoms = has("no symptoms", "symptom-free", "symptom free")
        count = sum(value for key, value in signals.items() if key != "worsening")
        if explicit_no_symptoms:
            count = 0
        severity = "severe" if signals["severe_headache"] or signals["vomiting"] else "moderate" if count >= 3 else "mild"
        day_match = re.search(r"\bday\s*(\d+)\b", lower)
        return SymptomSignals(
            **signals,
            symptom_count=count,
            severity=severity,
            onset_or_day=int(day_match.group(1)) if day_match else None,
            raw_text=text,
        )
