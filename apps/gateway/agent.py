"""Gemini + MCP tool-calling agent loop."""
from __future__ import annotations

import json
from typing import Any, Callable

from google.genai import types

from apps.gateway import config
from apps.gateway.tools import TOOL_HANDLERS, call_tool

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
        name="get_weather",
        description="Get current weather for a city or place name.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"location": types.Schema(type=types.Type.STRING)},
            required=["location"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_news",
        description="Get recent news headlines about a topic.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "topic": types.Schema(type=types.Type.STRING),
                "max_results": types.Schema(type=types.Type.INTEGER),
            },
            required=["topic"],
        ),
    ),
    types.FunctionDeclaration(
        name="notes_add",
        description=(
            "Store a lasting memory. REQUIRED when the user states their name "
            "(use tags='identity') or asks you to remember a fact."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "content": types.Schema(type=types.Type.STRING),
                "tags": types.Schema(type=types.Type.STRING),
            },
            required=["content"],
        ),
    ),
    types.FunctionDeclaration(
        name="notes_list",
        description="List recently saved notes and memories about the user.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"limit": types.Schema(type=types.Type.INTEGER)},
        ),
    ),
    types.FunctionDeclaration(
        name="notes_search",
        description=(
            "Search stored memories (names, preferences, facts). "
            "Use before answering personal questions."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(type=types.Type.STRING),
                "limit": types.Schema(type=types.Type.INTEGER),
            },
            required=["query"],
        ),
    ),
]


SYSTEM_PROMPT_WITH_TOOLS = (
    config.SYSTEM_PROMPT
    + f" Language policy: respond in {config.ASSISTANT_LANGUAGE} unless the user explicitly asks for another language. "
    + " Tools available: web_search, get_weather, get_news, notes_add, notes_list, notes_search. "
    "Use notes_add whenever the user shares their name or asks you to remember a fact. "
    "Use notes_search when addressing them or recalling prior details. "
    "Use weather/news/search when up-to-date info is needed. "
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
    """Run Gemini with MCP-backed tools. Returns (final_text, tool_trace)."""
    tools = [types.Tool(function_declarations=FUNCTION_DECLARATIONS)]
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=user_text)])
    ]
    tool_trace: list[dict[str, Any]] = []

    for _round in range(max_tool_rounds + 1):
        _emit(on_event, {"type": "status", "status": "thinking"})
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_WITH_TOOLS,
                tools=tools,
            ),
        )

        fn_calls = _extract_function_calls(response)
        if not fn_calls:
            text = (getattr(response, "text", None) or "").strip()
            return text, tool_trace

        model_parts = [_function_call_part(name, args) for name, args in fn_calls]
        contents.append(types.Content(role="model", parts=model_parts))

        response_parts = []
        for name, args in fn_calls:
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
            response_parts.append(_function_response_part(name, result))

        contents.append(types.Content(role="user", parts=response_parts))

    return (
        "I ran into a loop using tools. Please try a simpler request.",
        tool_trace,
    )
