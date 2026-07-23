"""Work around Windows/librosa float64 vs Chatterbox float32 weight mismatches."""
from __future__ import annotations

import numpy as np
import torch


_PATCHED = False


def apply_float32_patches() -> None:
    """Idempotent monkeypatches for Chatterbox tokenizer + voice encoder."""
    global _PATCHED
    if _PATCHED:
        return

    from chatterbox.models.s3tokenizer.s3tokenizer import S3Tokenizer
    from chatterbox.models.voice_encoder.voice_encoder import VoiceEncoder

    _orig_mel = S3Tokenizer.log_mel_spectrogram

    def _log_mel_spectrogram(self, audio, padding: int = 0):
        if not torch.is_tensor(audio):
            audio = torch.as_tensor(audio, dtype=torch.float32)
        else:
            audio = audio.float()
        out = _orig_mel(self, audio, padding=padding)
        return out.float() if torch.is_tensor(out) else out

    S3Tokenizer.log_mel_spectrogram = _log_mel_spectrogram

    _orig_embeds = VoiceEncoder.embeds_from_mels

    def _embeds_from_mels(self, mels, mel_lens=None, as_spk=False, batch_size=32, **kwargs):
        if isinstance(mels, list):
            mels = [np.asarray(mel, dtype=np.float32) for mel in mels]
        elif isinstance(mels, np.ndarray):
            mels = np.asarray(mels, dtype=np.float32)
        return _orig_embeds(
            self, mels, mel_lens=mel_lens, as_spk=as_spk, batch_size=batch_size, **kwargs
        )

    _orig_inference = VoiceEncoder.inference

    def _inference(self, mels, mel_lens, batch_size=32, **kwargs):
        if torch.is_tensor(mels):
            mels = mels.float()
        return _orig_inference(self, mels, mel_lens, batch_size=batch_size, **kwargs)

    VoiceEncoder.embeds_from_mels = _embeds_from_mels
    VoiceEncoder.inference = _inference
    _PATCHED = True


def force_tokenizer_float32(model) -> None:
    """Ensure mel filter / window buffers are float32 after model load."""
    tok = getattr(getattr(model, "s3gen", None), "tokenizer", None)
    if tok is None:
        return
    if hasattr(tok, "_mel_filters"):
        tok._mel_filters = tok._mel_filters.float()
    if hasattr(tok, "window"):
        tok.window = tok.window.float()
