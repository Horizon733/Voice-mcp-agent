"""Env-driven configuration for the gateway. Loads .env if present."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small.en")
# Phase 2+: STT stays on CPU by default to leave GPU/MPS for TTS.
STT_DEVICE = os.environ.get("STT_DEVICE", "cpu")

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
    "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's "
    "trusted AI companion. Persona: calm, precise, dryly witty British butler-engineer; "
    "unflappable, never gushing, never robotic. Address the user with quiet respect "
    "(use their name once known; otherwise 'sir' or 'madam' sparingly). "
    "Do not say you are an AI language model. No markdown, lists, or emoji — speak "
    "in 1-3 short sentences meant to be heard aloud. "
    "MEMORY: If the user states their name or asks you to remember something, "
    "immediately store it with notes action='add' (tag names with tags='identity' or 'name'). "
    "Before answering personal questions, check notes action='search' or action='list' so you "
    "recall prior facts. Prefer remembering over asking again.",
)
