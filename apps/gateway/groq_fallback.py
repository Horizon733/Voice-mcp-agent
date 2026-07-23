"""Groq fallback with tool-calling parity for web_search and notes."""
from __future__ import annotations

import json
from typing import Any, Callable

import requests

from apps.gateway import config
from apps.gateway.tools import TOOL_HANDLERS, call_tool

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
    url = f"{config.GROQ_BASE_URL}/chat/completions"
    payload: dict[str, Any] = {
        "model": config.GROQ_MODEL,
        "messages": messages,
        "tools": GROQ_TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens": 320,
    }
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=config.GROQ_TIMEOUT_SEC,
    )
    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"Groq API error ({response.status_code}): {detail}")
    return response.json()


def _parse_args(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def ask_groq(
    user_text: str,
    *,
    on_event: EventCallback | None = None,
    max_tool_rounds: int = 4,
) -> tuple[str, list[dict[str, Any]]]:
    """Run Groq with tool-calling loop. Returns (final_text, tool_trace)."""
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": GROQ_SYSTEM_PROMPT_WITH_TOOLS},
        {"role": "user", "content": user_text},
    ]
    tool_trace: list[dict[str, Any]] = []

    for _round in range(max_tool_rounds + 1):
        _emit(on_event, {"type": "status", "status": "thinking"})
        data = _post_chat(messages)
        message = (data.get("choices", [{}])[0] or {}).get("message", {}) or {}

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            text = str(message.get("content") or "").strip()
            if text:
                return text, tool_trace
            raise RuntimeError("Groq returned an empty response")

        assistant_message = {
            "role": "assistant",
            "content": message.get("content") or "",
            "tool_calls": tool_calls,
        }
        messages.append(assistant_message)

        for tool_call in tool_calls:
            fn = (tool_call or {}).get("function", {}) or {}
            call_id = str((tool_call or {}).get("id") or "")
            name = str(fn.get("name") or "")
            args = _parse_args(str(fn.get("arguments") or ""))

            _emit(
                on_event,
                {"type": "status", "status": "tool", "tool": name, "args": args},
            )

            if name not in TOOL_HANDLERS:
                result: dict[str, Any] = {"error": f"Unknown tool '{name}'"}
            else:
                result = call_tool(name, args)

            preview = json.dumps(result, ensure_ascii=False)
            if len(preview) > 500:
                preview = preview[:500] + "…"

            entry = {"name": name, "args": args, "result_preview": preview}
            tool_trace.append(entry)
            _emit(on_event, {"type": "tool", **entry})

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return (
        "I ran into a loop using tools. Please try a simpler request.",
        tool_trace,
    )
