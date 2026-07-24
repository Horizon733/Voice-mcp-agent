"""Workshop tool stubs used by MCP server and in-process agent host.

Each function intentionally returns a small TODO payload so attendees can
implement one tool at a time.
"""
from __future__ import annotations

from typing import Any


def _todo_payload(tool_name: str, steps: list[str], **context: Any) -> dict[str, Any]:
    return {
        "status": "todo",
        "tool": tool_name,
        "message": f"TODO: implement '{tool_name}' with attendees.",
        "steps": steps,
        "context": context,
    }


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """TODO: implement web search provider integration."""
    return _todo_payload(
        "web_search",
        steps=[
            "Validate query and max_results.",
            "Call a search provider.",
            "Return normalized results: title, url, snippet.",
        ],
        query=(query or "").strip(),
        max_results=max_results,
    )


def notes_add(content: str, tags: str = "") -> dict[str, Any]:
    """TODO: implement persistent note storage."""
    return _todo_payload(
        "notes_add",
        steps=[
            "Validate content is non-empty.",
            "Insert note into a local store (SQLite/file).",
            "Return saved id and timestamp.",
        ],
        content=(content or "").strip(),
        tags=(tags or "").strip(),
    )


def notes_list(limit: int = 10) -> dict[str, Any]:
    """TODO: implement recent notes listing."""
    return _todo_payload(
        "notes_list",
        steps=[
            "Read notes from storage.",
            "Sort by latest first.",
            "Limit number of returned rows.",
        ],
        limit=limit,
    )


def notes_search(query: str, limit: int = 10) -> dict[str, Any]:
    """TODO: implement notes keyword search."""
    return _todo_payload(
        "notes_search",
        steps=[
            "Normalize query string.",
            "Run LIKE/FTS lookup over notes storage.",
            "Return matching notes with count.",
        ],
        query=(query or "").strip(),
        limit=limit,
    )


def notes(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Unified notes tool with add/list/search actions.

    Accepts action either positionally or as a keyword so mixed call paths
    do not fail with duplicate keyword errors.
    """
    action = kwargs.pop("action", "")
    if args and not action:
        action = args[0]

    normalized = str(action or "").strip().lower()
    if normalized == "add":
        return notes_add(content=str(kwargs.get("content", "")), tags=str(kwargs.get("tags", "")))
    if normalized == "list":
        return notes_list(limit=int(kwargs.get("limit", 10)))
    if normalized == "search":
        return notes_search(query=str(kwargs.get("query", "")), limit=int(kwargs.get("limit", 10)))
    return {
        "error": "Invalid notes action",
        "allowed_actions": ["add", "list", "search"],
    }


TOOL_HANDLERS = {
    "web_search": lambda **kw: web_search(
        query=kw.get("query", ""), max_results=int(kw.get("max_results", 5))
    ),
    "notes": lambda **kw: notes(**kw),
}


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return handler(**(arguments or {}))
    except Exception as exc:  # noqa: BLE001 — surface to the LLM
        return {"error": str(exc)}
