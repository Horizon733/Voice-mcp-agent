"""Entry point wiring Phases 1-3 (STT -> Gemini -> TTS) into a voice loop. No MCP yet."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .agent import VoiceAgent
from .config import GEMINI_API_KEY, WAKE_WORD
from .stt import VoiceListener, select_microphone
from .tts import VoiceSpeaker


console = Console()


async def _tee_print(text_stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """Print each chunk to the console as it passes through to the speaker."""
    async for chunk in text_stream:
        console.print(chunk, end="", style="bold magenta")
        yield chunk


def _load_components() -> tuple[VoiceListener, VoiceAgent, VoiceSpeaker]:
    """Load STT, agent, and TTS with a spinner (model loads can take 10-30s)."""
    if not GEMINI_API_KEY:
        console.print(
            "[bold red]Missing GEMINI_API_KEY.[/bold red] Set it in .env before running."
        )
        sys.exit(1)

    device_index = select_microphone()

    listener: VoiceListener | None = None
    agent: VoiceAgent | None = None
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Loading speech-to-text (Whisper)...", total=None)
        try:
            listener = VoiceListener(input_device_index=device_index)
        except OSError as exc:
            console.print(f"[bold red]Microphone initialization failed:[/bold red] {exc}")
            sys.exit(1)

        progress.update(task, description="Connecting to Gemini...")
        try:
            agent = VoiceAgent()
        except Exception as exc:
            console.print(f"[bold red]Failed to initialize Gemini agent:[/bold red] {exc}")
            listener.shutdown()
            sys.exit(1)

        progress.update(task, description="Loading text-to-speech (Qwen3-TTS)...")
        try:
            speaker = VoiceSpeaker(voice_preset="jarvis")
        except Exception as exc:
            console.print(f"[bold red]Failed to load TTS model:[/bold red] {exc}")
            listener.shutdown()
            sys.exit(1)

        progress.update(task, description="Ready!")

    return listener, agent, speaker


async def main() -> None:
    console.print(Panel.fit("[bold green]Talk to Your Tools — Voice Agent Ready[/bold green]"))
    console.print(f"Say '[bold]{WAKE_WORD}[/bold]' to activate, then ask anything.")

    listener, agent, speaker = _load_components()

    try:
        while True:
            user_text = await listener.listen_once()
            if not user_text:
                continue

            console.print(f"[bold cyan]🧑 You:[/bold cyan] {user_text}")
            console.print("[bold magenta]🤖 Agent:[/bold magenta] ", end="")
            await speaker.speak_streaming(_tee_print(agent.respond(user_text)))
            console.print()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    finally:
        listener.shutdown()
        speaker.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
