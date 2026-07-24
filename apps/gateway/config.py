"""Env-driven configuration for the gateway. Loads .env if present."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# TODO(Workshop): pick your Gemini model name.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "TODO_GEMINI_MODEL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
# TODO(Workshop): pick your Groq fallback model name.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "TODO_GROQ_MODEL")
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
ASSISTANT_LANGUAGE = os.environ.get("ASSISTANT_LANGUAGE", "English").strip() or "English"

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small.en")
# Phase 2+: STT stays on CPU by default to leave GPU/MPS for TTS.
STT_DEVICE = os.environ.get("STT_DEVICE", "cpu")
STT_PROFILE = os.environ.get("STT_PROFILE", "balanced").strip().lower()
STT_LANGUAGE = os.environ.get("STT_LANGUAGE", "en").strip().lower()
STT_COMPUTE_TYPE = os.environ.get("STT_COMPUTE_TYPE", "auto").strip().lower()


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


STT_VAD_FILTER = _env_bool("STT_VAD_FILTER", True)
STT_BEAM_SIZE = _env_int("STT_BEAM_SIZE", 2)
GROQ_TIMEOUT_SEC = _env_float("GROQ_TIMEOUT_SEC", 25.0)
TTS_NORMALIZE_ENGLISH = _env_bool("TTS_NORMALIZE_ENGLISH", True)

# auto | cuda | mps | cpu  (auto = CUDA -> MPS -> CPU)
TTS_DEVICE = os.environ.get("TTS_DEVICE", "auto")
# turbo (lighter) | full
TTS_BACKEND = os.environ.get("TTS_BACKEND", "turbo")

JARVIS_CONDS = Path(os.environ.get("JARVIS_CONDS", ROOT / "voices" / "jarvis_conds.pt"))
JARVIS_REF_WAV = Path(os.environ.get("JARVIS_REF_WAV", ROOT / "voices" / "jarvis-5s.wav"))

NOTES_DB_PATH = Path(os.environ.get("NOTES_DB_PATH", ROOT / "data" / "notes.db"))

# Comma-separated origins for the React dev server / production UI
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
    ).split(",")
    if o.strip()
]

SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "TODO: write your assistant system prompt for workshop exercises.",
)
