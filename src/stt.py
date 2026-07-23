"""Speech-to-text module using RealtimeSTT + openWakeWord."""

from __future__ import annotations

import asyncio

import pyaudio
import torch
from RealtimeSTT import AudioToTextRecorder
from rich.console import Console
from rich.prompt import IntPrompt
from rich.table import Table

from .config import SAMPLE_RATE, WAKE_WORD, WHISPER_MODEL


console = Console()


def list_input_devices() -> list[dict]:
    """Return metadata for every audio-input-capable device PyAudio can see."""
    pa = pyaudio.PyAudio()
    try:
        devices = [
            pa.get_device_info_by_index(i)
            for i in range(pa.get_device_count())
            if pa.get_device_info_by_index(i)["maxInputChannels"] > 0
        ]
        try:
            default_index = pa.get_default_input_device_info()["index"]
        except OSError:
            default_index = None
        for device in devices:
            device["is_default"] = device["index"] == default_index
        return devices
    finally:
        pa.terminate()


def select_microphone() -> int | None:
    """Print available input devices and prompt the user to pick one.

    Returns the chosen device index, or None to let RealtimeSTT fall back
    to whatever the OS reports as the default input device.
    """
    devices = list_input_devices()
    if not devices:
        console.print("[yellow]No input devices found; using system default.[/yellow]")
        return None

    table = Table(title="Available Microphones")
    table.add_column("Index", justify="right")
    table.add_column("Name")
    table.add_column("Default", justify="center")
    for device in devices:
        table.add_row(
            str(device["index"]),
            device["name"],
            "✓" if device["is_default"] else "",
        )
    console.print(table)

    default_index = next((d["index"] for d in devices if d["is_default"]), devices[0]["index"])
    valid_indices = {d["index"] for d in devices}
    choice = IntPrompt.ask(
        "Select a microphone by index",
        default=default_index,
        show_default=True,
    )
    if choice not in valid_indices:
        console.print(f"[yellow]Invalid index {choice}; using default instead.[/yellow]")
        return default_index
    return choice


class VoiceListener:
    """Wake-word gated listener that returns one transcribed utterance at a time."""

    def __init__(self, input_device_index: int | None = None) -> None:
        # faster-whisper/CTranslate2 (used internally by RealtimeSTT) only
        # supports "cuda" or "cpu" — there is no MPS backend, so Apple
        # Silicon always transcribes on CPU regardless of torch.backends.mps.
        device = "cuda" if torch.cuda.is_available() else "cpu"
        console.print(f"[dim]Initializing STT ({WHISPER_MODEL} on {device})...[/dim]")
        self._recorder = AudioToTextRecorder(
            model=WHISPER_MODEL,
            language=None,  # auto-detect (English / Hindi / Hinglish)
            wakeword_backend="oww",
            wake_words=WAKE_WORD,
            silero_deactivity_detection=True,
            post_speech_silence_duration=0.7,
            sample_rate=SAMPLE_RATE,
            device=device,
            input_device_index=input_device_index,
            spinner=False,
            on_wakeword_detected=self.on_wakeword_detected,
            on_recording_start=self.on_recording_start,
            on_recording_stop=self.on_recording_stop,
        )
        console.print("[dim]STT ready.[/dim]")

    def on_wakeword_detected(self) -> None:
        console.print("👂 Wake word heard!")

    def on_recording_start(self) -> None:
        console.print("🎤 Listening...")

    def on_recording_stop(self) -> None:
        console.print("⏳ Transcribing...")

    async def listen_once(self) -> str:
        """Block until wake word + speech + silence, then return the transcript."""
        text = await asyncio.to_thread(self._recorder.text)
        return (text or "").strip()

    def shutdown(self) -> None:
        """Release microphone and worker threads."""
        self._recorder.shutdown()


async def _run_loop() -> None:
    device_index = select_microphone()
    listener = VoiceListener(input_device_index=device_index)
    console.print("Say 'Hey Jarvis' followed by anything...")
    try:
        while True:
            text = await listener.listen_once()
            if text:
                console.print(f"[bold green]You said:[/bold green] {text}")
    finally:
        listener.shutdown()


def main() -> None:
    try:
        asyncio.run(_run_loop())
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/yellow]")


if __name__ == "__main__":
    main()
