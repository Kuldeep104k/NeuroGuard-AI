"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "backend" / "data"
GUIDELINES_PATH = DATA_DIR / "guidelines" / "guidelines.txt"
DATABASE_PATH = Path(os.getenv("NEUROGUARD_DB_PATH", str(DATA_DIR / "neuroguard.db")))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
RAG_TOP_K = int(os.getenv("NEUROGUARD_RAG_TOP_K", "3"))

DISCLAIMER = (
    "NeuroGuard AI is an educational clinical decision-support tool, not a doctor, "
    "diagnosis, or replacement for professional medical care."
)
