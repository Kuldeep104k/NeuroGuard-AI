from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.guardrails import Guardrails
from backend.services.planner import Planner
from backend.services.rag_engine import RAGEngine
from backend.services.risk_engine import RiskEngine
from backend.services.symptom_extractor import SymptomExtractor


def binary_metrics(expected: list[bool], actual: list[bool]) -> dict[str, float]:
    tp = sum(want and got for want, got in zip(expected, actual))
    fp = sum(not want and got for want, got in zip(expected, actual))
    fn = sum(want and not got for want, got in zip(expected, actual))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {"precision": precision, "recall": recall}


def run() -> dict[str, float]:
    cases = json.loads((Path(__file__).parent / "quality_cases.json").read_text(encoding="utf-8"))
    extractor = SymptomExtractor()
    risk_engine = RiskEngine()
    guardrails = Guardrails()
    rag = RAGEngine()
    planner = Planner(rag=rag)

    risk_correct = 0
    stage_correct = 0
    citation_covered = 0
    expected_emergency: list[bool] = []
    actual_emergency: list[bool] = []
    expected_blocked: list[bool] = []
    actual_blocked: list[bool] = []
    signal_expected: list[bool] = []
    signal_actual: list[bool] = []
    signal_names = sorted({signal for case in cases for signal in case["expected_signals"]})

    for case in cases:
        symptoms = extractor.extract(case["input"])
        risk = risk_engine.assess(symptoms)
        safe = guardrails.assess(symptoms, input_text=case["input"])
        stage = planner._select_stage(symptoms, risk, case["day"])
        retrieved = rag.retrieve_documents(case["input"])

        risk_correct += risk.risk_level == case["expected_risk"]
        stage_correct += stage == case["expected_stage"]
        citation_covered += bool(retrieved)
        expected_emergency.append(case["expected_emergency"])
        actual_emergency.append(safe.emergency)
        expected_blocked.append(case["expected_blocked"])
        actual_blocked.append(not safe.safe)
        for signal in signal_names:
            signal_expected.append(signal in case["expected_signals"])
            signal_actual.append(bool(getattr(symptoms, signal)))

        print(
            f"{case['id']}: risk={risk.risk_level}/{case['expected_risk']} "
            f"stage={stage}/{case['expected_stage']} emergency={safe.emergency}/{case['expected_emergency']}"
        )

    emergency_metrics = binary_metrics(expected_emergency, actual_emergency)
    blocked_metrics = binary_metrics(expected_blocked, actual_blocked)
    signal_metrics = binary_metrics(signal_expected, signal_actual)
    metrics = {
        "risk_accuracy": risk_correct / len(cases),
        "stage_accuracy": stage_correct / len(cases),
        "citation_coverage": citation_covered / len(cases),
        "signal_precision": signal_metrics["precision"],
        "signal_recall": signal_metrics["recall"],
        "emergency_precision": emergency_metrics["precision"],
        "emergency_recall": emergency_metrics["recall"],
        "unsafe_block_precision": blocked_metrics["precision"],
        "unsafe_block_recall": blocked_metrics["recall"],
    }
    print("\nQuality metrics:")
    for name, value in metrics.items():
        print(f"{name}: {value:.2%}")
    return metrics


if __name__ == "__main__":
    run()
