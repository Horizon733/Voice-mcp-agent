"""Workshop scaffold for Gemini + tool-calling agent loop.

This file intentionally keeps only the interface and a TODO-oriented control
flow so attendees can implement model/tool logic step by step.
"""
from __future__ import annotations

from typing import Any, Callable

from google.genai import types

from apps.gateway import config
from apps.gateway.tools import TOOL_HANDLERS

EventCallback = Callable[[dict[str, Any]], None]

FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="web_search",
        description="Search the public web for current information.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(type=types.Type.STRING),
                "max_results": types.Schema(type=types.Type.INTEGER),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="notes",
        description=(
            "Manage memory with action=add|list|search. "
            "Use add when user shares details to remember."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "action": types.Schema(type=types.Type.STRING),
                "content": types.Schema(type=types.Type.STRING),
                "tags": types.Schema(type=types.Type.STRING),
                "query": types.Schema(type=types.Type.STRING),
                "limit": types.Schema(type=types.Type.INTEGER),
            },
            required=["action"],
        ),
    ),
]


SYSTEM_PROMPT_WITH_TOOLS = (
    config.SYSTEM_PROMPT
    + f" Language policy: respond in {config.ASSISTANT_LANGUAGE} unless the user explicitly asks for another language. "
    + " Tools available: web_search and notes. "
    "Use notes action='add' whenever the user shares their name or asks you to remember a fact. "
    "Use notes action='search' when addressing them or recalling prior details. "
    "Use web_search when up-to-date info is needed. "
    "After tools, answer briefly in Jarvis's voice. Never narrate tool names unless asked."
)


def _emit(cb: EventCallback | None, event: dict[str, Any]) -> None:
    if cb:
        cb(event)


def _function_call_part(name: str, args: dict[str, Any]) -> types.Part:
    if hasattr(types.Part, "from_function_call"):
        return types.Part.from_function_call(name=name, args=args)
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


def _function_response_part(name: str, result: dict[str, Any]) -> types.Part:
    if hasattr(types.Part, "from_function_response"):
        return types.Part.from_function_response(name=name, response=result)
    return types.Part(
        function_response=types.FunctionResponse(name=name, response=result)
    )


def _extract_function_calls(response) -> list[tuple[str, dict]]:
    calls: list[tuple[str, dict]] = []
    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", None) or []:
            fc = getattr(part, "function_call", None)
            if not fc:
                continue
            name = getattr(fc, "name", "") or ""
            args = dict(getattr(fc, "args", None) or {})
            calls.append((name, args))
    return calls


def run_agent(
    client,
    user_text: str,
    *,
    on_event: EventCallback | None = None,
    max_tool_rounds: int = 4,
) -> tuple[str, list[dict[str, Any]]]:
    """TODO: run Gemini with tool-calling. Returns (final_text, tool_trace)."""
    _emit(on_event, {"type": "status", "status": "todo_agent"})

    tool_trace = [
        {
            "name": "run_agent",
            "args": {"max_tool_rounds": max_tool_rounds},
            "result_preview": (
                "TODO stages: setup prompt+contents -> call model -> parse tool calls "
                "-> execute tools -> feed responses -> repeat until final text. "
                f"Available handlers: {sorted(TOOL_HANDLERS.keys())}."
            ),
        }
    ]

    # TODO(Workshop 10 min)
    # 1) Create tools = [types.Tool(function_declarations=FUNCTION_DECLARATIONS)].
    # 2) Initialize contents with one user text message.
    # 3) Initialize empty tool_trace list for executed tools.
    #
    # TODO(Workshop 10 min)
    # 4) Add a for-loop for max_tool_rounds + 1 iterations.
    # 5) Emit status='thinking' before each model call.
    # 6) Call client.models.generate_content(...) with system prompt and tools.
    #
    # TODO(Workshop 10 min)
    # 7) Extract function calls from model response.
    # 8) If no function calls: return response.text + tool_trace.
    #
    # TODO(Workshop 10 min)
    # 9) For each function call: validate tool name in TOOL_HANDLERS.
    # 10) Execute handler via apps.gateway.tools.call_tool(name, args).
    # 11) Append compact preview entries to tool_trace.
    #
    # TODO(Workshop 10 min)
    # 12) Convert tool results into function_response parts.
    # 13) Append function_response parts back to contents as next user turn.
    # 14) Continue loop until final text or max rounds reached.
    #
    # TODO(Workshop 5 min)
    # 15) Add graceful fallback text if loop ends without final content.
    # Keep this placeholder reply so API and UI remain testable before implementation.
    return (
        "TODO: attendees should implement the Gemini agent loop in apps/gateway/agent.py.",
        tool_trace,
    )
