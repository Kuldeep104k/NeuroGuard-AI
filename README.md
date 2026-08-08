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

## Setup

Python 3.10+ is recommended. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

An `OPENAI_API_KEY` is optional. Without it, symptom extraction, planning, and retrieval use deterministic local fallbacks. With it, the OpenAI-compatible client can provide LLM-enhanced extraction and planning.

## Run the backend

```bash
uvicorn backend.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive API documentation is available at `/docs`.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/analyze \\
  -H 'Content-Type: application/json' \\
  -d '{"input_text":"Mild headache and fatigue after injury"}'
```

## Run the frontend

With the backend running in another terminal:

```bash
streamlit run frontend/streamlit_app.py
```

## Run the benchmark

```bash
python evaluation/benchmark.py
```

The benchmark prints each expected/predicted risk and the overall accuracy. Assessments are logged to `backend/data/neuroguard.db` by default; set `NEUROGUARD_DB_PATH` to use another SQLite path.

## Current development branch

Implementation work is currently on `dev`. Keep API keys and other secrets in environment variables; do not commit them to the repository.
