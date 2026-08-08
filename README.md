# NeuroGuard AI – Adaptive Concussion Recovery Assistant

NeuroGuard AI is a safety-first, explainable clinical decision-support prototype for concussion recovery. It accepts free-text symptom descriptions, extracts structured signals, estimates recovery risk, generates conservative staged guidance, and records results for evaluation.

> **Important:** NeuroGuard AI is not a doctor and does not replace professional medical care. It must not be used for diagnosis or emergency treatment. Worsening symptoms or emergency symptoms require immediate medical attention.

## Project status

The repository is being built incrementally. The `main` branch contains the initial project documentation baseline. Ongoing implementation work belongs on `dev`.

## Planned stack

- FastAPI backend
- Streamlit frontend
- Pydantic schemas
- SQLite persistence
- OpenAI-compatible language-model interface
- FAISS-based guideline retrieval
- Python evaluation benchmark

## Planned capabilities

- Structured symptom extraction from free text
- Hybrid rule-based and history-aware risk scoring
- Conservative staged recovery planning
- Safety guardrails and emergency escalation
- Guideline-grounded retrieval and explanations
- Evaluation logs and benchmark accuracy reporting

## Repository layout

```text
backend/       FastAPI application, services, schemas, database, and guideline data
evaluation/    Benchmark scripts and evaluation utilities
frontend/      Streamlit user interface
requirements.txt
README.md
```

## Development workflow

Use `main` for stable baselines and `dev` for active implementation. Changes should be developed and verified on `dev`, then merged into `main` when ready.

Setup and run instructions will be added as the application components are implemented.
