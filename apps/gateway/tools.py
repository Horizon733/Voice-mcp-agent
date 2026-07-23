"""Tool implementations used by the MCP server and the in-process agent host."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from apps.gateway import config


def _http_json(url: str, timeout: float = 15.0) -> Any:
    req = Request(url, headers={"User-Agent": "mcp-voice/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web (DuckDuckGo). No API key required."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install duckduckgo-search (or ddgs)") from exc

    results = []
    ddgs = DDGS()
    for item in ddgs.text(query, max_results=max_results):
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("href"),
                "snippet": item.get("body"),
            }
        )
    return {"query": query, "results": results}


def get_weather(location: str) -> dict[str, Any]:
    """Current weather via Open-Meteo (geocode + forecast). No API key."""
    geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode(
        {"name": location, "count": 1, "language": "en", "format": "json"}
    )
    geo = _http_json(geo_url)
    results = geo.get("results") or []
    if not results:
        return {"error": f"Could not find location '{location}'"}

    place = results[0]
    lat, lon = place["latitude"], place["longitude"]
    label = ", ".join(
        p for p in [place.get("name"), place.get("admin1"), place.get("country")] if p
    )

    weather_url = "https://api.open-meteo.com/v1/forecast?" + urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
    )
    weather = _http_json(weather_url)
    current = weather.get("current") or {}
    return {
        "location": label,
        "latitude": lat,
        "longitude": lon,
        "temperature_c": current.get("temperature_2m"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "observed_at": current.get("time"),
    }


def get_news(topic: str = "top technology", max_results: int = 5) -> dict[str, Any]:
    """News headlines via DuckDuckGo news. No API key required."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install duckduckgo-search (or ddgs)") from exc

    articles = []
    ddgs = DDGS()
    for item in ddgs.news(topic, max_results=max_results):
        articles.append(
            {
                "title": item.get("title"),
                "url": item.get("url") or item.get("href"),
                "source": item.get("source"),
                "date": item.get("date"),
                "snippet": item.get("body"),
            }
        )
    return {"topic": topic, "articles": articles}


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


TOOL_HANDLERS = {
    "web_search": lambda **kw: web_search(
        query=kw.get("query", ""), max_results=int(kw.get("max_results", 5))
    ),
    "get_weather": lambda **kw: get_weather(location=kw.get("location", "")),
    "get_news": lambda **kw: get_news(
        topic=kw.get("topic", "top technology"),
        max_results=int(kw.get("max_results", 5)),
    ),
    "notes_add": lambda **kw: notes_add(
        content=kw.get("content", ""), tags=kw.get("tags", "")
    ),
    "notes_list": lambda **kw: notes_list(limit=int(kw.get("limit", 10))),
    "notes_search": lambda **kw: notes_search(
        query=kw.get("query", ""), limit=int(kw.get("limit", 10))
    ),
}


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return handler(**(arguments or {}))
    except Exception as exc:  # noqa: BLE001 — surface to the LLM
        return {"error": str(exc)}
