"""Tool implementations used by the MCP server and the in-process agent host."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from apps.gateway import config


def _http_json(url: str, timeout: float = 15.0) -> Any:
    req = Request(url, headers={"User-Agent": "mcp-voice/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web (DuckDuckGo). No API key required."""
    query = (query or "").strip()
    max_results = max(1, min(int(max_results or 5), 10))
    if not query:
        return {"error": "Empty query", "query": query, "results": []}

    def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in items:
            url = str(item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            out.append(item)
            if len(out) >= max_results:
                break
        return out

    def _ddgs_text_search() -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        ddgs = DDGS()
        for item in ddgs.text(
            query,
            max_results=max_results,
            safesearch="off",
            backend="auto",
        ):
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("href"),
                    "snippet": item.get("body"),
                    "source": "ddgs:text",
                }
            )
        return results

    def _ddgs_news_search() -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        ddgs = DDGS()
        for item in ddgs.news(query, max_results=max_results):
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url") or item.get("href"),
                    "snippet": item.get("body") or item.get("excerpt"),
                    "source": "ddgs:news",
                }
            )
        return results

    def _google_news_rss() -> list[dict[str, Any]]:
        url = (
            "https://news.google.com/rss/search?q="
            f"{quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        )
        req = Request(url, headers={"User-Agent": "mcp-voice/1.0"})
        with urlopen(req, timeout=15.0) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        channel = root.find("channel")
        if channel is None:
            return []

        results: list[dict[str, Any]] = []
        for item in channel.findall("item"):
            title = item.findtext("title")
            link = item.findtext("link")
            desc = item.findtext("description")
            results.append(
                {
                    "title": title,
                    "url": link,
                    "snippet": desc,
                    "source": "google-news:rss",
                }
            )
            if len(results) >= max_results:
                break
        return results

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install duckduckgo-search (or ddgs)") from exc

    errors: list[str] = []
    candidates: list[dict[str, Any]] = []

    for provider in (_ddgs_text_search, _ddgs_news_search, _google_news_rss):
        if len(candidates) >= max_results:
            break
        try:
            candidates.extend(provider())
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{provider.__name__}: {exc}")

    results = _dedupe(candidates)
    payload: dict[str, Any] = {"query": query, "results": results}
    if errors:
        payload["provider_errors"] = errors
    if not results:
        payload["hint"] = "No search hits found. Try a more specific query."
    return payload


def _notes_db() -> Path:
    path = Path(config.NOTES_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    return path


def notes_add(content: str, tags: str = "") -> dict[str, Any]:
    """Store something the user said (or asked to remember)."""
    content = (content or "").strip()
    if not content:
        return {"error": "Empty note content"}
    db = _notes_db()
    created = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db) as conn:
        cur = conn.execute(
            "INSERT INTO notes (content, tags, created_at) VALUES (?, ?, ?)",
            (content, tags.strip(), created),
        )
        conn.commit()
        note_id = cur.lastrowid
    return {"id": note_id, "content": content, "tags": tags, "created_at": created}


def notes_list(limit: int = 10) -> dict[str, Any]:
    db = _notes_db()
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT id, content, tags, created_at FROM notes ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 50)),),
        ).fetchall()
    notes = [
        {"id": r[0], "content": r[1], "tags": r[2], "created_at": r[3]} for r in rows
    ]
    return {"count": len(notes), "notes": notes}


def notes_search(query: str, limit: int = 10) -> dict[str, Any]:
    db = _notes_db()
    q = f"%{(query or '').strip()}%"
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            """
            SELECT id, content, tags, created_at FROM notes
            WHERE content LIKE ? OR tags LIKE ?
            ORDER BY id DESC LIMIT ?
            """,
            (q, q, max(1, min(limit, 50))),
        ).fetchall()
    notes = [
        {"id": r[0], "content": r[1], "tags": r[2], "created_at": r[3]} for r in rows
    ]
    return {"query": query, "count": len(notes), "notes": notes}


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
        return notes_add(
            content=str(kwargs.get("content", "")),
            tags=str(kwargs.get("tags", "")),
        )
    if normalized == "list":
        return notes_list(limit=int(kwargs.get("limit", 10)))
    if normalized == "search":
        return notes_search(
            query=str(kwargs.get("query", "")),
            limit=int(kwargs.get("limit", 10)),
        )
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
