"""MCP stdio server exposing search, weather, news, and notes tools.

Run standalone:
    python -m mcp_servers.assistant.server

The gateway also imports the same tool implementations in-process for low latency,
and can optionally talk to this server over MCP stdio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as `python -m mcp_servers.assistant.server` from repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP

from apps.gateway import tools as tool_impl

mcp = FastMCP("mcp-voice-assistant-tools")


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """Search the public web for up-to-date information."""
    return json.dumps(tool_impl.web_search(query=query, max_results=max_results), ensure_ascii=False)


@mcp.tool()
def get_weather(location: str) -> str:
    """Get current weather for a city or place name."""
    return json.dumps(tool_impl.get_weather(location=location), ensure_ascii=False)


@mcp.tool()
def get_news(topic: str = "top technology", max_results: int = 5) -> str:
    """Get recent news headlines for a topic."""
    return json.dumps(
        tool_impl.get_news(topic=topic, max_results=max_results), ensure_ascii=False
    )


@mcp.tool()
def notes_add(content: str, tags: str = "") -> str:
    """Store a note or something the user asked you to remember."""
    return json.dumps(tool_impl.notes_add(content=content, tags=tags), ensure_ascii=False)


@mcp.tool()
def notes_list(limit: int = 10) -> str:
    """List recently saved notes."""
    return json.dumps(tool_impl.notes_list(limit=limit), ensure_ascii=False)


@mcp.tool()
def notes_search(query: str, limit: int = 10) -> str:
    """Search saved notes by keyword."""
    return json.dumps(
        tool_impl.notes_search(query=query, limit=limit), ensure_ascii=False
    )


@mcp.tool()
def notes(
    action: str,
    content: str = "",
    tags: str = "",
    query: str = "",
    limit: int = 10,
) -> str:
    """Compatibility wrapper for unified notes action=add|list|search."""
    return json.dumps(
        tool_impl.notes(
            action=action,
            content=content,
            tags=tags,
            query=query,
            limit=limit,
        ),
        ensure_ascii=False,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
