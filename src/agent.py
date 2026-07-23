"""Gemini orchestration via google-genai (Phase 3 — no MCP tool use yet)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from .config import GEMINI_API_KEY, GEMINI_MODEL


SYSTEM_INSTRUCTION = (
    "You are a helpful voice assistant. Respond conversationally in clear, "
    "natural English. Keep responses under 3 sentences unless the user asks "
    "for detail. Avoid emojis, markdown, or special characters — your output "
    "will be spoken aloud."
)


class VoiceAgent:
    """Streams Gemini responses while keeping a running conversation history."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._config = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        self._history: list[types.Content] = []

    async def respond(self, user_text: str) -> AsyncIterator[str]:
        """Send user_text to Gemini and yield the streamed reply chunk by chunk."""
        self._history.append(types.UserContent(parts=[types.Part(text=user_text)]))

        chunks: list[str] = []
        stream = await self._client.aio.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=self._history,
            config=self._config,
        )
        async for response in stream:
            if response.text:
                chunks.append(response.text)
                yield response.text

        self._history.append(types.ModelContent(parts=[types.Part(text="".join(chunks))]))

    def reset_conversation(self) -> None:
        """Clear conversation history, starting a fresh session."""
        self._history = []


async def _repl() -> None:
    agent = VoiceAgent()
    print("Chat with Gemini (type 'quit' to exit):")
    loop = asyncio.get_event_loop()
    while True:
        user_text = await loop.run_in_executor(None, input, "> ")
        if user_text.strip().lower() == "quit":
            break
        async for chunk in agent.respond(user_text):
            print(chunk, end="", flush=True)
        print()


def main() -> None:
    try:
        asyncio.run(_repl())
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")


if __name__ == "__main__":
    main()
