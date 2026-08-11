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

The project defaults to `NEUROGUARD_AI_MODE=local`: symptom extraction, risk scoring, planning, retrieval, and safety checks run deterministically with **zero hosted-model calls**. This is the recommended mode for development, demos, benchmarking, and quota protection. Copy `.env.example` to `.env` if desired; never commit the real `.env`.

Hosted structured-output inference is opt-in only. Set `NEUROGUARD_AI_MODE=openai` together with `OPENAI_API_KEY` when quota is available. The provider remains limited to one call per request.

The recovery API also accepts an optional `day` field and prior `history` records so the recommended stage can evolve over a longitudinal recovery timeline. Retrieved evidence is included in the explanation.

The request may also include optional `structured_answers` for direct observations such as headache intensity, dizziness, fatigue, sleep, mood, symptom change, activity response, vomiting, and urgent warning signs. These selectable answers supplement free text and take precedence for ordinary fields while dangerous contradictions are resolved conservatively.

## API usage limits and unified AI call

Each `POST /analyze` request performs local symptom/risk preprocessing and makes **at most one** LLM call. The symptom extraction, risk result, recovery plan, explanation, and safety result are requested together as one strict JSON response. RAG retrieval and all evaluation scripts are local and do not consume LLM quota.

The hosted default model is `gpt-5.6-luna`; override it with `OPENAI_MODEL`. The default usage gate is 10 LLM calls per minute and 50 per UTC day. Configure limits with `NEUROGUARD_MAX_LLM_RPM` and `NEUROGUARD_MAX_LLM_RPD`. If hosted mode is disabled, the key is absent, a call is rate-limited, or the single call fails, NeuroGuard returns a deterministic safe fallback without retrying.

The response shape is:

```json
{
  "symptoms": {
    "headache": 0,
    "dizziness": false,
    "fatigue": "low",
    "sleep_quality": "good",
    "mood": "calm"
  },
  "risk": {"risk_level": "low", "score": 0},
  "plan": {"stage": 1, "recommendations": ["...", "...", "..."]},
  "explanation": "...",
  "safety": {"safe": true, "alert": null}
}
```

The response also includes headers `X-NeuroGuard-AI-Mode`, `X-NeuroGuard-LLM-Calls`, `X-NeuroGuard-LLM-Status`, and `X-NeuroGuard-Rate-Limit` for observability. If a live call fails, the server logs a sanitized provider error without logging the API key.

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

Example structured check-in:

```json
{
  "input_text": "I felt worse after schoolwork",
  "day": 3,
  "structured_answers": {
    "headache_level": 5,
    "dizziness": false,
    "fatigue": "medium",
    "sleep_quality": "poor",
    "symptom_change": "worsening",
    "activity_response": "worsened",
    "vomiting": "none",
    "emergency_signs": []
  }
}
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

Run the safety benchmark with:

```bash
python evaluation/safety_benchmark.py
```

Raw symptom text is not stored by default. Set `NEUROGUARD_STORE_RAW_INPUT=true` only for controlled evaluation. Logs are automatically retained for `NEUROGUARD_RETENTION_DAYS` days (30 by default). To enable authenticated deletion, set `NEUROGUARD_ADMIN_TOKEN` and call `DELETE /privacy/logs` with the `X-Admin-Token` header.

Run the broader quality benchmark with:

```bash
python evaluation/quality_benchmark.py
```

Run the offline regression suite before enabling any hosted provider:

```bash
python evaluation/regression_tests.py
```

The regression suite verifies strict response keys, local zero-call behavior, exactly one hosted call when explicitly enabled, no-retry fallback behavior, emergency overrides, RPM gating, and privacy deletion. It does not contact an external API.

If `NEUROGUARD_ADMIN_TOKEN` is configured, the protected `GET /usage` endpoint reports current-minute and current-day usage remaining. The protected `DELETE /privacy/logs` endpoint clears assessment logs and usage reservations.

It reports risk accuracy, recovery-stage accuracy, symptom precision/recall, emergency precision/recall, unsafe-content blocking, and evidence citation coverage.

## Current development branch

Implementation work is currently on `dev`. Keep API keys and other secrets in environment variables; do not commit them to the repository.
