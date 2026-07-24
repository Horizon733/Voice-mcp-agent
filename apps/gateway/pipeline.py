"""Model loading (once at startup) and audio-in -> audio-out turn pipeline."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from faster_whisper import WhisperModel
from google import genai

from apps.gateway import config
from apps.gateway.agent import run_agent
from apps.gateway.groq_fallback import ask_groq
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
        self.groq_enabled = False
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
            "notes",
        ]

    def load(self):
        compute_type = _stt_compute_type(config.STT_DEVICE, config.STT_COMPUTE_TYPE)
        print(
            f"[gateway] Loading faster-whisper '{config.WHISPER_MODEL}' "
            f"on {config.STT_DEVICE} (compute={compute_type}, profile={config.STT_PROFILE})..."
        )
        self.whisper = WhisperModel(
            config.WHISPER_MODEL,
            device=config.STT_DEVICE,
            compute_type=compute_type,
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

        self.groq_enabled = bool(config.GROQ_API_KEY)
        if self.groq_enabled:
            print(f"[gateway] Groq fallback enabled with model '{config.GROQ_MODEL}'.")
        else:
            print("[gateway] Groq fallback disabled (GROQ_API_KEY not set).")

        print(f"[gateway] MCP tools ready: {', '.join(self.mcp_tools)}")

        if self.wake_word.load():
            print("[gateway] Wake-word ('hey jarvis') model ready.")

        if config.TTS_WARMUP_ENABLED and self.conds_loaded:
            warmup_start = time.perf_counter()
            try:
                synthesize_to_wav_bytes(self.tts, config.TTS_WARMUP_TEXT)
                elapsed = time.perf_counter() - warmup_start
                print(f"[gateway] TTS warmup complete in {elapsed:.2f}s")
            except Exception as exc:  # noqa: BLE001
                print(f"[gateway] WARNING: TTS warmup failed: {exc}")


models = GatewayModels()


def _stt_compute_type(device: str, configured: str) -> str:
    if configured and configured != "auto":
        return configured
    if device == "cuda":
        return "int8_float16"
    return "int8"


def _stt_decode_options() -> dict[str, Any]:
    profile = config.STT_PROFILE
    options: dict[str, Any]

    if profile == "fast":
        options = {
            "beam_size": 1,
            "best_of": 1,
            "condition_on_previous_text": False,
        }
    elif profile == "accurate":
        options = {
            "beam_size": max(3, config.STT_BEAM_SIZE),
            "best_of": max(3, config.STT_BEAM_SIZE),
            "condition_on_previous_text": True,
        }
    else:
        options = {
            "beam_size": max(1, config.STT_BEAM_SIZE),
            "best_of": max(1, config.STT_BEAM_SIZE),
            "condition_on_previous_text": False,
        }

    options["vad_filter"] = config.STT_VAD_FILTER
    options["temperature"] = 0.0
    options["word_timestamps"] = False
    if config.STT_LANGUAGE and config.STT_LANGUAGE != "auto":
        options["language"] = config.STT_LANGUAGE
    return options


def transcribe(audio_bytes: bytes, on_event: EventCallback | None = None) -> str:
    if on_event:
        on_event({"type": "status", "status": "transcribing"})
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        segments, _info = models.whisper.transcribe(tmp_path, **_stt_decode_options())
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
    gemini_error: Exception | None = None

    if models.gemini is not None:
        try:
            return run_agent(models.gemini, transcript, on_event=on_event)
        except Exception as exc:  # noqa: BLE001
            gemini_error = exc

    if models.groq_enabled:
        try:
            reply, groq_trace = ask_groq(transcript, on_event=on_event)
            fallback_entry = {
                "name": "llm_fallback",
                "args": {"provider": "groq", "model": config.GROQ_MODEL},
                "result_preview": "Gemini failed; continued with Groq fallback.",
            }
            if on_event:
                on_event({"type": "tool", **fallback_entry})
            return reply, [fallback_entry, *groq_trace]
        except Exception as groq_exc:  # noqa: BLE001
            if gemini_error is None:
                raise ConfigError(f"Groq fallback failed: {groq_exc}") from groq_exc
            raise ConfigError(
                f"Gemini failed: {gemini_error}. Groq fallback failed: {groq_exc}"
            ) from groq_exc

    if gemini_error is not None:
        raise ConfigError(
            f"Gemini failed and Groq fallback is not configured: {gemini_error}"
        ) from gemini_error

    raise ConfigError(
        "No LLM configured. Set GEMINI_API_KEY or GROQ_API_KEY in .env and restart the gateway."
    )


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
