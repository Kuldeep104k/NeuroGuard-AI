from __future__ import annotations

import re

from backend.schemas.symptom_schema import SymptomSignals
from backend.schemas.symptom_schema import StructuredCheckIn
from backend.services.llm_client import LLMClient


SYSTEM_PROMPT = """You are a clinical safety assistant. Extract only symptoms explicitly supported by the text.
Return JSON matching the SymptomSignals schema. Never diagnose, minimize danger, or invent facts."""


class SymptomExtractor:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = None

    def extract(self, text: str, structured_answers: StructuredCheckIn | None = None) -> SymptomSignals:
        signals = self._local_extract(text)
        if structured_answers:
            signals = self._apply_structured_answers(signals, structured_answers)
        return signals

    @property
    def mode(self) -> str:
        return "local"

    def _local_extract(self, text: str) -> SymptomSignals:
        lower = text.lower()

        def has(*terms: str) -> bool:
            """Match explicit symptom language while respecting simple negation."""
            for term in terms:
                for match in re.finditer(re.escape(term), lower):
                    prefix = lower[max(0, match.start() - 32):match.start()]
                    # Do not let a negation from a previous clause (for
                    # example, "no vomiting; only mild fatigue") leak into
                    # the next symptom statement.
                    prefix = re.split(r"[,;:]", prefix)[-1]
                    if not re.search(r"\b(no|not|without|denies|denied|never)\b[^.!?]{0,24}$", prefix):
                        return True
            return False

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
            "seizure": has("seizure", "convulsion", "shaking or twitching"),
            "loss_of_consciousness": has("loss of consciousness", "passed out", "knocked out", "blackout"),
            "confusion": has("confus", "cannot recognize", "can't recognize", "disoriented"),
            "weakness_or_numbness": has("weakness", "numbness", "decreased coordination"),
            "slurred_speech": has("slurred speech", "slurring words"),
            "unequal_pupils": has("unequal pupils", "one pupil larger", "double vision"),
            "unable_to_wake": has("cannot wake", "can't wake", "unable to wake", "cannot stay awake"),
            "unusual_behavior": has("unusual behavior", "agitated", "restless", "personality change"),
            "repeated_vomiting": has("repeated vomiting", "vomiting repeatedly", "vomited multiple times"),
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

    @staticmethod
    def _apply_structured_answers(signals: SymptomSignals, answers: StructuredCheckIn) -> SymptomSignals:
        values = answers.model_dump(exclude_none=True)
        if "headache_level" in values:
            level = values["headache_level"]
            signals.headache_level = level
            # Never let a low questionnaire value erase a dangerous phrase
            # detected in free text; contradictions must resolve conservatively.
            signals.headache = signals.headache or level > 0
            signals.severe_headache = signals.severe_headache or level >= 8
        if "dizziness" in values:
            signals.dizziness = values["dizziness"]
        if "fatigue" in values:
            signals.fatigue_level = values["fatigue"]
            signals.fatigue = values["fatigue"] != "low"
        if "sleep_quality" in values:
            signals.sleep_quality = values["sleep_quality"]
            signals.sleep_problems = values["sleep_quality"] == "poor"
        if "mood" in values:
            signals.mood = values["mood"]
        if "symptom_change" in values:
            signals.symptom_change = values["symptom_change"]
            signals.worsening = signals.worsening or values["symptom_change"] == "worsening"
        if "activity_response" in values:
            signals.activity_response = values["activity_response"]
            if values["activity_response"] == "worsened":
                signals.worsening = True
        if "vomiting" in values:
            vomiting = values["vomiting"]
            signals.vomiting = vomiting != "none"
            signals.repeated_vomiting = vomiting == "repeated"
        for name in values.get("emergency_signs", []):
            setattr(signals, name, True)
        signals.symptom_count = sum(
            value for key, value in signals.model_dump().items()
            if key not in {
                "worsening", "symptom_count", "severity", "onset_or_day", "raw_text",
                "headache_level", "fatigue_level", "sleep_quality", "mood",
                "symptom_change", "activity_response",
            } and isinstance(value, bool)
        )
        signals.severity = "severe" if signals.severe_headache or signals.vomiting else "moderate" if signals.symptom_count >= 3 else "mild"
        return signals
