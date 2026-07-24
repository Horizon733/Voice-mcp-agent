"""Workshop scaffold for startup/model wiring and turn pipeline."""
from __future__ import annotations

from typing import Any, Callable

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
        self.whisper = None
        self.tts = None
        self.gemini: genai.Client | None = None
        self.groq_enabled = False
        self.conds_loaded = False
        self.tts_device = "cpu"
        self.tts_backend = config.TTS_BACKEND
        self.wake_word = WakeWordDetector()
        self.mcp_tools = [
            "web_search",
            "notes",
        ]

    def load(self):
        # TODO(Workshop step 1): Load STT model and assign self.whisper.
        #   1a) compute_type = _stt_compute_type(...)
        #   1b) self.whisper = WhisperModel(...)
        # TODO(Workshop step 2): Load TTS model + conditionals via load_tts().
        # TODO(Workshop step 3): Initialize Gemini client when API key is set.
        # TODO(Workshop step 4): Enable optional Groq fallback.
        # TODO(Workshop step 5): Load wake-word detector.
        self.whisper = None
        self.tts, _Conditionals, self.tts_device, self.tts_backend, self.conds_loaded = load_tts(
            device=config.TTS_DEVICE,
            backend=config.TTS_BACKEND,
            conds_path=config.JARVIS_CONDS,
        )
        self.gemini = genai.Client(api_key=config.GEMINI_API_KEY) if config.GEMINI_API_KEY else None
        self.groq_enabled = bool(config.GROQ_API_KEY)
        self.wake_word.load()


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
    _ = audio_bytes
    if on_event:
        on_event({"type": "status", "status": "todo_transcribe"})
    # TODO(Workshop 10 min): persist incoming audio bytes to temporary wav/webm file.
    # TODO(Workshop 10 min): call models.whisper.transcribe(temp_path, **_stt_decode_options()).
    # TODO(Workshop 5 min): join segment text into one transcript string.
    # TODO(Workshop 5 min): emit transcript event and clean up temp file.
    return "TODO: implement transcription in apps/gateway/pipeline.py"


def ask_gemini(
    transcript: str,
    on_event: EventCallback | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    if on_event:
        on_event({"type": "status", "status": "todo_llm"})

    # TODO: primary path - call Gemini via run_agent.
    if models.gemini is not None:
        return run_agent(models.gemini, transcript, on_event=on_event)

    # TODO: fallback path - call Groq when enabled.
    if models.groq_enabled:
        return ask_groq(transcript, on_event=on_event)

    raise ConfigError("TODO: configure GEMINI_API_KEY or GROQ_API_KEY for LLM step")


def synthesize(text: str, on_event: EventCallback | None = None) -> bytes:
    if not models.conds_loaded:
        raise ConfigError("TODO: load/build voice conditionals before TTS synthesis")
    if on_event:
        on_event({"type": "status", "status": "todo_tts"})
    try:
        return synthesize_to_wav_bytes(models.tts, text)
    except VoiceError as exc:
        raise ConfigError(str(exc)) from exc


def run_turn(
    audio_bytes: bytes,
    on_event: EventCallback | None = None,
) -> dict:
    # TODO(Workshop): keep this orchestrator but implement each stage incrementally.
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
