from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.risk_engine import RiskEngine
from backend.services.symptom_extractor import SymptomExtractor


def run() -> float:
    root = ROOT_DIR
    dataset = json.loads((root / "backend" / "data" / "simulated_dataset.json").read_text(encoding="utf-8"))
    extractor = SymptomExtractor()
    engine = RiskEngine()
    correct = 0
    for item in dataset:
        prediction = engine.assess(extractor.extract(item["input"])).risk_level
        correct += prediction == item["expected_risk"]
        print(f"day={item['day']} expected={item['expected_risk']} predicted={prediction}")
    accuracy = correct / len(dataset) if dataset else 0.0
    print(f"Accuracy: {accuracy:.2%} ({correct}/{len(dataset)})")
    return accuracy


if __name__ == "__main__":
    run()
