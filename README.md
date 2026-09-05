# NeuroGuard AI

NeuroGuard AI is a safety-first concussion recovery companion that helps people record daily symptoms, understand a conservative next step, and prepare a clear summary for a caregiver or healthcare professional.

> **Important:** NeuroGuard AI is educational decision support. It does not diagnose, treat, or replace professional medical care. Severe, rapidly worsening, or emergency symptoms require immediate local medical help.

## Try NeuroGuard AI

- [Open the live NeuroGuard application](https://neuroguard-frontend.onrender.com)
- [Check the live recovery service](https://neuroguard-backend-3su2.onrender.com/health)

The application is deployed on Render with a Streamlit interface connected to a FastAPI recovery service. It runs in local deterministic mode and does not require user credentials or external model access.

## What it does

- Converts a written check-in and optional guided answers into a structured symptom summary.
- Identifies concerning patterns with deterministic safety rules.
- Produces a conservative five-stage recovery plan.
- Tracks check-ins in a simple day-by-day recovery timeline.
- Shows the evidence supporting the guidance.
- Provides a downloadable caregiver or clinician handoff summary.
- Keeps raw symptom text out of stored logs by default.

## Recovery experience

Each check-in asks only for information the person knows:

1. Describe what changed.
2. Clarify severity, activity response, sleep, mood, and warning signs.
3. Review the current risk, recovery stage, next steps, and escalation guidance.

The timeline preserves previous check-ins and advances only after a successful assessment. Starting a new recovery timeline clears the local session and begins again at Day 1.

## Safety principles

The application is deliberately conservative. It prioritizes urgent escalation when warning signs appear, discourages contact or fall-risk activity while symptoms are concerning, and recommends professional reassessment when symptoms worsen or persist. It supports relative rest and gradual, symptom-limited return to daily activity rather than strict isolation.

## Project structure

```text
backend/       Recovery service, safety rules, schemas, storage, and guideline data
frontend/      Streamlit user interface
evaluation/    Offline benchmark and regression suites
requirements.txt
README.md
```

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

Start the recovery service:

```bash
uvicorn backend.main:app --reload
```

In a second terminal, start the interface:

```bash
streamlit run frontend/streamlit_app.py
```

Open the local Streamlit address shown in the terminal and complete a check-in. The interface uses `http://127.0.0.1:8000` for the local recovery service. For a separate deployment, set `NEUROGUARD_BACKEND_URL` in the interface service environment.

## Verification

Run the offline checks from the repository root:

```bash
python evaluation/regression_tests.py
python evaluation/benchmark.py
python evaluation/safety_benchmark.py
python evaluation/quality_benchmark.py
```

The checks cover response validation, structured check-ins, safety escalation, prompt-injection resistance, fallback behavior, usage protection, privacy deletion, risk accuracy, stage accuracy, symptom signal quality, and evidence coverage. They do not require external credentials.

## Privacy defaults

Raw symptom text is not stored by default. Optional local settings can be copied from `.env.example`. Keep any private deployment configuration outside version control.

## Deployment

The project is deployed as two Render web services:

- Frontend: `streamlit run frontend/streamlit_app.py --server.address 0.0.0.0 --server.port $PORT`
- Recovery service: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

The frontend service uses `NEUROGUARD_BACKEND_URL` to locate the deployed recovery service. Keep that value in the deployment environment rather than hard-coding a private service address in source code.

## Responsible use

Recovery timelines and recommendations must be interpreted in context. Return to learning, work, exercise, and sport should be individualized and guided by symptoms, activity tolerance, and qualified professional advice. The application is not a substitute for an examination or emergency care.
