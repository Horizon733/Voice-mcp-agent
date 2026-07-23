"""Shared Chatterbox load / conds / synthesize helpers (Win / Mac / Docker)."""
from __future__ import annotations

import io
from pathlib import Path

import torch
import torchaudio as ta

from apps.gateway.device import pick_device
from apps.gateway.dtype_patches import apply_float32_patches, force_tokenizer_float32


class VoiceError(RuntimeError):
    """User-facing voice/TTS configuration or runtime error."""


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
    try:
        wav = model.generate(text)
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
