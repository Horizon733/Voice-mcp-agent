"""Workshop scaffold for Groq fallback with tool-calling.

Implementation details are intentionally left as TODO items for attendees.
"""
from __future__ import annotations

from typing import Any, Callable

from apps.gateway import config
from apps.gateway.tools import TOOL_HANDLERS

EventCallback = Callable[[dict[str, Any]], None]

GROQ_SYSTEM_PROMPT_WITH_TOOLS = (
    config.SYSTEM_PROMPT
    + f" Language policy: respond in {config.ASSISTANT_LANGUAGE} unless the user explicitly asks for another language. "
    + " Tools available: web_search and notes. "
    "Use notes action='add' whenever the user shares their name or asks you to remember a fact. "
    "Use notes action='search' when addressing them or recalling prior details. "
    "Use web_search when up-to-date info is needed. "
    "After tools, answer briefly in Jarvis's voice. Never narrate tool names unless asked."
)

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public web for current information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notes",
            "description": (
                "Manage long-term memory with action=add|list|search. "
                "Use add when the user shares their name or asks you to remember a fact. "
                "Use search/list before answering personal questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["action"],
            },
        },
    },
]


def _emit(cb: EventCallback | None, event: dict[str, Any]) -> None:
    if cb:
        cb(event)


def _post_chat(messages: list[dict[str, Any]]) -> dict[str, Any]:
    # TODO: implement Groq HTTP call. Keep this helper for attendee implementation.
    raise RuntimeError(
        "TODO: implement _post_chat in apps/gateway/groq_fallback.py"
    )


def _parse_args(raw: str) -> dict[str, Any]:
    # TODO: parse JSON tool arguments from Groq tool call payload.
    _ = raw
    return {}


def ask_groq(
    user_text: str,
    *,
    on_event: EventCallback | None = None,
    max_tool_rounds: int = 4,
) -> tuple[str, list[dict[str, Any]]]:
    """TODO: run Groq with a tool-calling loop. Returns (final_text, tool_trace)."""
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    _emit(on_event, {"type": "status", "status": "todo_groq"})
    tool_trace = [
        {
            "name": "ask_groq",
            "args": {"max_tool_rounds": max_tool_rounds},
            "result_preview": (
                "TODO: implement Groq chat call, parse tool_calls, dispatch tools "
                f"from {sorted(TOOL_HANDLERS.keys())}, and return final text."
            ),
        }
    ]
    _ = user_text
    return (
        "TODO: attendees should implement Groq fallback in apps/gateway/groq_fallback.py.",
        tool_trace,
    )
