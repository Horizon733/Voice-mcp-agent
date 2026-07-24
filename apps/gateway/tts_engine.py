"""Shared Chatterbox load / conds / synthesize helpers (Win / Mac / Docker)."""
from __future__ import annotations

import io
import re
import unicodedata
from pathlib import Path

import torch
import torchaudio as ta

from apps.gateway import config
from apps.gateway.device import pick_device
from apps.gateway.dtype_patches import apply_float32_patches, force_tokenizer_float32


class VoiceError(RuntimeError):
    """User-facing voice/TTS configuration or runtime error."""


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•]+|\d+[.)])\s+")


def _normalize_tts_text(text: str) -> str:
    """Convert text into stable spoken English tokens for multilingual TTS models."""
    raw = (text or "").strip()
    if not raw:
        return raw

    # URLs and handles often trigger unexpected phonemes; keep meaning concise.
    s = _URL_RE.sub(" link ", raw)
    s = s.replace("@", " at ").replace("#", " number ")

    # Strip accents and non-ASCII symbols that can push the model out of English mode.
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    # Remove noisy punctuation while preserving sentence rhythm.
    s = re.sub(r"[^A-Za-z0-9\s.,!?;:'\"()%-]", " ", s)
    s = _WS_RE.sub(" ", s).strip()

    # Never return empty after normalization; fallback to original raw text.
    return s or raw


def _compact_for_speech(text: str, max_chars: int = 520, max_sentences: int = 5) -> str:
    """Compress long list-heavy text into concise spoken form for stable TTS."""
    s = (text or "").strip()
    if not s:
        return s

    lines = [line.strip() for line in s.splitlines() if line.strip()]
    lines = [_BULLET_PREFIX_RE.sub("", line) for line in lines]
    s = " ".join(lines)
    s = _WS_RE.sub(" ", s).strip()

    # Keep only a few complete sentences for speech stability.
    sentence_parts = re.split(r"(?<=[.!?])\s+", s)
    if len(sentence_parts) > max_sentences:
        s = " ".join(sentence_parts[:max_sentences]).strip()

    if len(s) > max_chars:
        cut = s[:max_chars]
        # Prefer cutting at sentence boundary, then clause boundary, then hard cut.
        for marker in (". ", "! ", "? ", "; ", ", "):
            idx = cut.rfind(marker)
            if idx > int(max_chars * 0.6):
                cut = cut[: idx + 1]
                break
        s = cut.rstrip(" ,;:-") + "."

    return s


def _import_tts(backend: str):
    backend = (backend or "turbo").strip().lower()
    if backend == "turbo":
        from chatterbox.tts_turbo import ChatterboxTurboTTS as TTS
        from chatterbox.tts_turbo import Conditionals
        return TTS, Conditionals, "turbo"
    if backend == "full":
        from chatterbox.tts import ChatterboxTTS as TTS
        from chatterbox.tts import Conditionals
        return TTS, Conditionals, "full"
    raise VoiceError(f"Unknown TTS_BACKEND '{backend}'. Use 'turbo' or 'full'.")


def load_tts(
    device: str = "auto",
    backend: str = "turbo",
    conds_path: Path | None = None,
):
    """Load Chatterbox, apply dtype patches, optionally load saved Jarvis conds.

    Returns (model, Conditionals_cls, resolved_device, backend_name, conds_loaded).
    """
    apply_float32_patches()
    resolved = pick_device(device)
    TTS, Conditionals, backend_name = _import_tts(backend)

    print(f"[tts] Loading Chatterbox ({backend_name}) on {resolved}...")
    try:
        model = TTS.from_pretrained(device=resolved)
    except Exception as exc:
        if backend_name == "turbo":
            print(f"[tts] Turbo load failed ({exc}); falling back to full ChatterboxTTS...")
            TTS, Conditionals, backend_name = _import_tts("full")
            model = TTS.from_pretrained(device=resolved)
        else:
            raise

    force_tokenizer_float32(model)

    conds_loaded = False
    if conds_path and Path(conds_path).exists():
        print(f"[tts] Loading conditionals from {conds_path}...")
        model.conds = Conditionals.load(str(conds_path), map_location=resolved).to(resolved)
        conds_loaded = True
    elif conds_path:
        print(f"[tts] WARNING: conditionals not found at {conds_path}")

    return model, Conditionals, resolved, backend_name, conds_loaded


def build_and_save_conds(
    ref_wav: Path,
    out_path: Path,
    device: str = "auto",
    backend: str = "turbo",
    exaggeration: float = 0.5,
):
    """Clone from reference wav once and persist conditionals."""
    if not ref_wav.exists():
        raise VoiceError(f"Reference wav not found: {ref_wav}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    model, _Conditionals, resolved, backend_name, _ = load_tts(
        device=device, backend=backend, conds_path=None
    )
    print(f"[tts] Building conditionals from {ref_wav} ({backend_name})...")
    model.prepare_conditionals(str(ref_wav), exaggeration=exaggeration)
    model.conds.save(out_path)
    print(f"[tts] Saved conditionals to {out_path}")
    return out_path


def synthesize_to_wav_bytes(model, text: str) -> bytes:
    """Generate speech using model.conds (must already be loaded)."""
    if getattr(model, "conds", None) is None:
        raise VoiceError(
            "No voice conditionals loaded. Run scripts/build_jarvis_conds.py first."
        )
    spoken_text = _normalize_tts_text(text) if config.TTS_NORMALIZE_ENGLISH else text
    spoken_text = _compact_for_speech(spoken_text)
    try:
        wav = model.generate(spoken_text)
    except torch.cuda.OutOfMemoryError as exc:
        raise VoiceError(
            "GPU out of memory during TTS. Shorten the reply, free GPU memory, "
            "or set TTS_DEVICE=cpu and restart."
        ) from exc

    buf = io.BytesIO()
    ta.save(buf, wav, model.sr, format="wav")
    return buf.getvalue()


def synthesize_to_file(model, text: str, out_path: Path) -> Path:
    raw = synthesize_to_wav_bytes(model, text)
    out_path.write_bytes(raw)
    return out_path
