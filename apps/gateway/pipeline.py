"""Model loading (once at startup) and audio-in -> audio-out turn pipeline."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable

from faster_whisper import WhisperModel
from google import genai

from apps.gateway import config
from apps.gateway.agent import run_agent
from apps.gateway.tts_engine import VoiceError, load_tts, synthesize_to_wav_bytes
from apps.gateway.wake_word import WakeWordDetector

EventCallback = Callable[[dict[str, Any]], None]


class ConfigError(RuntimeError):
    """Raised for missing/invalid setup (API key, conds file, etc.)."""


class GatewayModels:
    """Singleton STT / TTS / Gemini clients, loaded once at startup."""

    def __init__(self):
        self.whisper: WhisperModel | None = None
        self.tts = None
        self.gemini: genai.Client | None = None
        self.conds_loaded = False
        self.tts_device = "cpu"
        self.tts_backend = config.TTS_BACKEND
        self.wake_word = WakeWordDetector()
        self.mcp_tools = [
            "web_search",
            "get_weather",
            "get_news",
            "notes_add",
            "notes_list",
            "notes_search",
        ]

    def load(self):
        print(
            f"[gateway] Loading faster-whisper '{config.WHISPER_MODEL}' "
            f"on {config.STT_DEVICE}..."
        )
        self.whisper = WhisperModel(
            config.WHISPER_MODEL,
            device=config.STT_DEVICE,
            compute_type="int8",
        )

        self.tts, _Conditionals, self.tts_device, self.tts_backend, self.conds_loaded = load_tts(
            device=config.TTS_DEVICE,
            backend=config.TTS_BACKEND,
            conds_path=config.JARVIS_CONDS,
        )
        if not self.conds_loaded:
            print(
                f"[gateway] WARNING: {config.JARVIS_CONDS} not found. "
                "Run scripts/build_jarvis_conds.py before calling /v1/turn or /tts."
            )

        if config.GEMINI_API_KEY:
            self.gemini = genai.Client(api_key=config.GEMINI_API_KEY)
        else:
            print("[gateway] WARNING: GEMINI_API_KEY not set. /v1/turn will fail until it is.")
            self.gemini = None

        print(f"[gateway] MCP tools ready: {', '.join(self.mcp_tools)}")

        if self.wake_word.load():
            print("[gateway] Wake-word ('hey jarvis') model ready.")


models = GatewayModels()


def transcribe(audio_bytes: bytes, on_event: EventCallback | None = None) -> str:
    if on_event:
        on_event({"type": "status", "status": "transcribing"})
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        segments, _info = models.whisper.transcribe(tmp_path)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if on_event:
            on_event({"type": "transcript", "text": text})
        return text
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def ask_gemini(
    transcript: str,
    on_event: EventCallback | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    if models.gemini is None:
        raise ConfigError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key, "
            "then restart the gateway."
        )
    return run_agent(models.gemini, transcript, on_event=on_event)


def synthesize(text: str, on_event: EventCallback | None = None) -> bytes:
    if not models.conds_loaded:
        raise ConfigError(
            f"No Jarvis conditionals loaded ({config.JARVIS_CONDS} missing). "
            "Run: python scripts/build_jarvis_conds.py"
        )
    if on_event:
        on_event({"type": "status", "status": "speaking"})
    try:
        return synthesize_to_wav_bytes(models.tts, text)
    except VoiceError as exc:
        raise ConfigError(str(exc)) from exc


def run_turn(
    audio_bytes: bytes,
    on_event: EventCallback | None = None,
) -> dict:
    transcript = transcribe(audio_bytes, on_event=on_event)
    if not transcript:
        raise ConfigError("I couldn't hear anything clearly. Please try again.")

    reply_text, tool_trace = ask_gemini(transcript, on_event=on_event)
    if not reply_text:
        reply_text = "I'm afraid I have nothing useful to say to that, sir."

    if on_event:
        on_event({"type": "reply_text", "text": reply_text})

    audio_out = synthesize(reply_text, on_event=on_event)
    result = {
        "transcript": transcript,
        "reply_text": reply_text,
        "audio_out": audio_out,
        "tools": tool_trace,
    }
    if on_event:
        on_event({"type": "done"})
    return result
