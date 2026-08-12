"""Offline regression tests for quota, schema, safety, and privacy invariants."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.routes import unified_engine
from backend.db.database import Database
from backend.main import app
from backend.schemas.ai_schema import UnifiedAIResponse
from backend.schemas.symptom_schema import StructuredCheckIn
from backend.services import unified_ai_engine as engine_module
from backend.services.unified_ai_engine import UnifiedAIEngine


class FakeLLM:
    available = True

    def __init__(self, result=None):
        self.calls = 0
        self.result = result

    def complete_structured(self, system_prompt, user_prompt, json_schema):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def valid_model_result() -> dict:
    return {
        "symptoms": {
            "headache": 3,
            "dizziness": False,
            "fatigue": "medium",
            "sleep_quality": "good",
            "mood": "calm",
        },
        "risk": {"risk_level": "low", "score": 10},
        "plan": {
            "stage": 1,
            "recommendations": ["Rest", "Monitor symptoms", "Seek professional guidance"],
        },
        "explanation": "Conservative guidance based on the reported symptoms.",
        "safety": {"safe": True, "alert": None},
    }


class OfflineRegressionTests(unittest.TestCase):
    def setUp(self):
        self.original_mode = engine_module.AI_MODE
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        engine_module.AI_MODE = self.original_mode
        self.temp_dir.cleanup()

    def test_local_mode_never_calls_provider(self):
        fake = FakeLLM(valid_model_result())
        engine_module.AI_MODE = "local"
        result = UnifiedAIEngine(llm=fake, database=self.database).analyze("Mild headache")
        self.assertEqual(fake.calls, 0)
        self.assertEqual(result.safety.safe, True)

    def test_openai_mode_makes_exactly_one_call(self):
        fake = FakeLLM(valid_model_result())
        engine_module.AI_MODE = "openai"
        result = UnifiedAIEngine(llm=fake, database=self.database).analyze("Mild headache")
        self.assertEqual(fake.calls, 1)
        self.assertIsInstance(result, UnifiedAIResponse)

    def test_provider_failure_falls_back_without_retry(self):
        fake = FakeLLM(RuntimeError("secret request details must not leak"))
        engine_module.AI_MODE = "openai"
        result = UnifiedAIEngine(llm=fake, database=self.database).analyze("Mild headache")
        self.assertEqual(fake.calls, 1)
        self.assertIsInstance(result, UnifiedAIResponse)

    def test_emergency_override_is_deterministic(self):
        fake = FakeLLM(valid_model_result())
        engine_module.AI_MODE = "local"
        result = UnifiedAIEngine(llm=fake, database=self.database).analyze(
            "Severe worsening headache with repeated vomiting and confusion"
        )
        self.assertFalse(result.safety.safe)
        self.assertEqual(result.risk.risk_level, "high")
        self.assertIn("score of 100/100", result.explanation)
        self.assertEqual(result.plan.stage, 1)

    def test_structured_answers_override_ambiguous_free_text(self):
        engine_module.AI_MODE = "local"
        result = UnifiedAIEngine(database=self.database).analyze(
            "I am unsure how bad it is",
            structured_answers=StructuredCheckIn(
                headache_level=7,
                dizziness=True,
                fatigue="high",
                sleep_quality="poor",
                symptom_change="worsening",
            ),
        )
        self.assertEqual(result.symptoms.headache, 7)
        self.assertTrue(result.symptoms.dizziness)
        self.assertEqual(result.symptoms.fatigue, "high")
        self.assertEqual(result.symptoms.sleep_quality, "poor")
        self.assertEqual(result.risk.risk_level, "high")

    def test_structured_emergency_sign_is_prioritized(self):
        engine_module.AI_MODE = "local"
        result = UnifiedAIEngine(database=self.database).analyze(
            "I feel okay",
            structured_answers=StructuredCheckIn(emergency_signs=["confusion"]),
        )
        self.assertFalse(result.safety.safe)
        self.assertEqual(result.plan.stage, 1)

    def test_rate_gate_allows_ten_and_blocks_eleven(self):
        for _ in range(10):
            self.assertTrue(self.database.reserve_llm_call(10, 50))
        self.assertFalse(self.database.reserve_llm_call(10, 50))

    def test_usage_snapshot_and_privacy_deletion(self):
        self.database.reserve_llm_call(10, 50)
        self.assertEqual(self.database.usage_snapshot(10, 50)["minute_used"], 1)
        self.database.delete_all()
        self.assertEqual(self.database.usage_snapshot(10, 50)["minute_used"], 0)

    def test_api_contract_is_strict(self):
        client = TestClient(app)
        response = client.post("/analyze", json={"day": 1, "input_text": "Mild headache and fatigue"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            sorted(response.json()),
            ["explanation", "plan", "risk", "safety", "symptoms"],
        )
        self.assertEqual(response.headers["x-neuroguard-llm-calls"], "0")

    def test_api_rejects_empty_check_in(self):
        client = TestClient(app)
        response = client.post("/analyze", json={"input_text": "", "structured_answers": {}})
        self.assertEqual(response.status_code, 422)

    def test_api_accepts_structured_only_check_in(self):
        client = TestClient(app)
        response = client.post(
            "/analyze",
            json={"structured_answers": {"headache_level": 4, "fatigue": "medium"}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["symptoms"]["headache"], 4)
        self.assertEqual(response.json()["symptoms"]["fatigue"], "medium")


if __name__ == "__main__":
    unittest.main(verbosity=2)
