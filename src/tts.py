"""Text-to-speech module using Qwen3-TTS (Base / voice-clone) via the qwen-tts package.

The Base model has no fixed speaker roster — it clones whatever voice you give it
from a short reference clip + transcript. Drop your own clip at
voices/<preset>.wav (+ voices/<preset>.txt with its exact transcript) to speak in
that voice; see config.VOICES_DIR. If no local preset is found, "default" falls
back to Qwen's public example clip so the module is runnable out of the box.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import numpy as np
import sounddevice as sd
import torch
from qwen_tts import Qwen3TTSModel
from rich.console import Console

from .config import QWEN_TTS_MODEL, VOICES_DIR


console = Console()

# Qwen's own example clip, used only when no local voices/<preset>.{wav,txt} exists.
_FALLBACK_REF_AUDIO = "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-TTS-Repo/clone.wav"
_FALLBACK_REF_TEXT = (
    "Okay. Yeah. I resent you. I love you. I respect you. "
    "But you know what? You blew it! And thanks to you."
)


def _resolve_device() -> tuple[str, torch.dtype, str | None]:
    if torch.cuda.is_available():
        try:
            import flash_attn  # noqa: F401

            attn_impl = "flash_attention_2"
        except ImportError:
            attn_impl = None
        return "cuda:0", torch.bfloat16, attn_impl
    if torch.backends.mps.is_available():
        return "mps", torch.float16, None
    return "cpu", torch.float32, None


def _resolve_voice_preset(name: str) -> tuple[str, str]:
    """Return (ref_audio, ref_text) for a voice preset name.

    Looks for voices/<name>.wav + voices/<name>.txt; falls back to Qwen's
    bundled example clip for the "default" preset if those files don't exist.
    """
    audio_path = VOICES_DIR / f"{name}.wav"
    text_path = VOICES_DIR / f"{name}.txt"
    if audio_path.exists() and text_path.exists():
        return str(audio_path), text_path.read_text(encoding="utf-8").strip()

    if name == "default":
        console.print(
            f"[yellow]No {audio_path} found — using Qwen's example clip as a "
            f"placeholder voice. Add {audio_path} and {text_path} to clone your own.[/yellow]"
        )
        return _FALLBACK_REF_AUDIO, _FALLBACK_REF_TEXT

    raise FileNotFoundError(
        f"Voice preset '{name}' not found. Add {audio_path} (3+ second reference "
        f"clip) and {text_path} (its exact transcript)."
    )


class VoiceSpeaker:
    """Loads Qwen3-TTS (Base) once and clones a reference voice to speak English text."""

    def __init__(self, voice_preset: str = "default") -> None:
        device, dtype, attn_impl = _resolve_device()
        console.print(f"[dim]Loading {QWEN_TTS_MODEL} on {device} ({dtype})...[/dim]")
        kwargs = {"device_map": device, "dtype": dtype}
        if attn_impl:
            kwargs["attn_implementation"] = attn_impl
        self._model = Qwen3TTSModel.from_pretrained(QWEN_TTS_MODEL, **kwargs)

        ref_audio, ref_text = _resolve_voice_preset(voice_preset)
        self._voice_clone_prompt = self._model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text,
        )
        self._stop_requested = False
        console.print("[dim]TTS ready.[/dim]")

    def _synthesize(self, text: str) -> tuple[np.ndarray, int]:
        wavs, sr = self._model.generate_voice_clone(
            text=text,
            language="English",
            voice_clone_prompt=self._voice_clone_prompt,
        )
        return wavs[0], sr

    def _play(self, wav: np.ndarray, sr: int) -> None:
        sd.play(wav, sr)
        sd.wait()

    async def _speak_sentence(self, sentence: str) -> None:
        wav, sr = await asyncio.to_thread(self._synthesize, sentence)
        if not self._stop_requested:
            await asyncio.to_thread(self._play, wav, sr)

    async def speak(self, text: str) -> None:
        """Synthesize text and block until playback finishes."""
        self._stop_requested = False
        console.print("🔊 Speaking...")
        await self._speak_sentence(text)
        console.print("✅ Done")

    async def speak_streaming(self, text_stream: AsyncIterator[str]) -> None:
        """Consume a streamed text generator, then synthesize and play it as one clip.

        Waiting for the full reply trades first-audio latency for a single
        continuous waveform — no gaps between sentences.
        """
        self._stop_requested = False
        full_text = "".join([chunk async for chunk in text_stream]).strip()
        if self._stop_requested or not full_text:
            return
        console.print("🔊 Speaking...")
        await self._speak_sentence(full_text)
        console.print("✅ Done")

    def stop(self) -> None:
        """Interrupt any in-progress or queued playback (barge-in)."""
        self._stop_requested = True
        sd.stop()

    def shutdown(self) -> None:
        """Release the model and any GPU memory it holds."""
        sd.stop()
        del self._model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


async def _demo() -> None:
    speaker = VoiceSpeaker(voice_preset="jarvis")
    try:
        await speaker.speak(
            "Hello, this is your voice agent. I can hear you, think with Gemini, and talk back."
        )
    finally:
        speaker.shutdown()


def main() -> None:
    asyncio.run(_demo())


if __name__ == "__main__":
    main()
