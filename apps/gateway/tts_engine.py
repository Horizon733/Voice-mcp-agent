"""Workshop scaffold for TTS loading and synthesis.

This module keeps stable function signatures but replaces implementation with
small TODO checkpoints for attendees.
"""
from __future__ import annotations

from pathlib import Path


class VoiceError(RuntimeError):
    """User-facing voice/TTS configuration or runtime error."""


def _normalize_tts_text(text: str) -> str:
    """TODO: normalize text for stable TTS output."""
    # TODO(Workshop 5 min): strip whitespace and collapse repeated spaces.
    # TODO(Workshop 5 min): optionally remove URLs/symbols that hurt pronunciation.
    return (text or "").strip()


def _compact_for_speech(text: str, max_chars: int = 520, max_sentences: int = 5) -> str:
    """TODO: compact long replies for speech synthesis."""
    # TODO(Workshop 5 min): split into sentences and keep only first N.
    # TODO(Workshop 5 min): clip to max_chars while ending cleanly on punctuation.
    _ = max_chars
    _ = max_sentences
    return (text or "").strip()


def _import_tts(backend: str):
    # TODO(Workshop 10 min):
    # - backend='turbo' -> import Turbo class + Conditionals.
    # - backend='full'  -> import Full class + Conditionals.
    # - else raise VoiceError.
    _ = backend
    raise VoiceError("TODO: implement TTS backend import selection")


def load_tts(
    device: str = "auto",
    backend: str = "turbo",
    conds_path: Path | None = None,
):
    """TODO: load TTS model and optional conditionals."""
    _ = conds_path
    # TODO(Workshop 10 min): resolve runtime device from input (auto/cuda/mps/cpu).
    # TODO(Workshop 10 min): import selected backend and call from_pretrained().
    # TODO(Workshop 10 min): if conds_path exists, load saved voice conditionals.
    # TODO(Workshop 5 min): return (model, Conditionals, resolved_device, backend_name, conds_loaded).
    return None, None, device, backend, False


def build_and_save_conds(
    ref_wav: Path,
    out_path: Path,
    device: str = "auto",
    backend: str = "turbo",
    exaggeration: float = 0.5,
):
    """TODO: build/snapshot voice conditionals from a reference wav."""
    # TODO(Workshop 10 min): validate ref_wav exists; create parent output directory.
    # TODO(Workshop 10 min): load model then call prepare_conditionals(ref_wav, exaggeration).
    # TODO(Workshop 5 min): save conditionals to out_path and return path.
    _ = ref_wav
    _ = device
    _ = backend
    _ = exaggeration
    raise VoiceError(
        f"TODO: implement conditionals build then save to {out_path}"
    )


def synthesize_to_wav_bytes(model, text: str) -> bytes:
    """TODO: generate WAV bytes from text."""
    # TODO(Workshop 5 min): guard for missing model.conds and raise VoiceError.
    # TODO(Workshop 5 min): normalize + compact text before generation.
    # TODO(Workshop 10 min): call model.generate and serialize to WAV bytes.
    _ = model
    _ = _compact_for_speech(_normalize_tts_text(text))
    raise VoiceError("TODO: implement synthesize_to_wav_bytes")


def synthesize_to_file(model, text: str, out_path: Path) -> Path:
    raw = synthesize_to_wav_bytes(model, text)
    out_path.write_bytes(raw)
    return out_path
