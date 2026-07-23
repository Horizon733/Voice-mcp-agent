"""Centralized application configuration for the workshop demo."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


# Core model/runtime constants requested for the workshop.
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
WAKE_WORD = os.getenv("WAKE_WORD", "hey_jarvis")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Base (voice-clone) model: synthesizes speech in a reference speaker's voice
# from a short (3s+) audio clip + its transcript, rather than a fixed preset roster.
QWEN_TTS_MODEL = os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AUDIO_CHUNK_MS = int(os.getenv("AUDIO_CHUNK_MS", "80"))
MODELS_DIR = Path(os.getenv("MODELS_DIR", "models"))
NOTES_DB_PATH = Path(os.getenv("NOTES_DB_PATH", "data/notes.db"))

# Directory holding voice-clone presets: for a preset named "<name>", drop a
# reference clip at voices/<name>.wav and its exact transcript at voices/<name>.txt.
VOICES_DIR = Path(os.getenv("VOICES_DIR", "voices"))
