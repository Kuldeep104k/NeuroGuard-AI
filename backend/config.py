"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "backend" / "data"
GUIDELINES_PATH = DATA_DIR / "guidelines" / "guidelines.txt"
GUIDELINE_SOURCES_PATH = DATA_DIR / "guidelines" / "guideline_sources.json"
DATABASE_PATH = Path(os.getenv("NEUROGUARD_DB_PATH", str(DATA_DIR / "neuroguard.db")))
STORE_RAW_INPUT = os.getenv("NEUROGUARD_STORE_RAW_INPUT", "false").lower() == "true"
RETENTION_DAYS = int(os.getenv("NEUROGUARD_RETENTION_DAYS", "30"))
ADMIN_TOKEN = os.getenv("NEUROGUARD_ADMIN_TOKEN")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
AI_MODE = os.getenv("NEUROGUARD_AI_MODE", "local").strip().lower()
if AI_MODE not in {"local", "openai"}:
    raise ValueError("NEUROGUARD_AI_MODE must be 'local' or 'openai'")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
RAG_TOP_K = int(os.getenv("NEUROGUARD_RAG_TOP_K", "3"))
MAX_LLM_RPM = int(os.getenv("NEUROGUARD_MAX_LLM_RPM", "10"))
MAX_LLM_RPD = int(os.getenv("NEUROGUARD_MAX_LLM_RPD", "50"))

DISCLAIMER = (
    "NeuroGuard AI is an educational clinical decision-support tool, not a doctor, "
    "diagnosis, or replacement for professional medical care."
)
