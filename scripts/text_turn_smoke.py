"""Text-only turn against a running gateway (good for testing MCP tools).

Usage:
    python scripts/text_turn_smoke.py "What's the weather in Mumbai?"
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--out", type=Path, default=Path("reply.wav"))
    args = parser.parse_args()

    resp = requests.post(
        f"{args.url}/v1/turn/text",
        json={"text": args.text},
        timeout=180,
    )
    if not resp.ok:
        raise SystemExit(f"{resp.status_code}: {resp.text}")

    data = resp.json()
    print("Reply:", data.get("reply_text"))
    print("Tools:", data.get("tools"))
    args.out.write_bytes(base64.b64decode(data["audio_base64"]))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
