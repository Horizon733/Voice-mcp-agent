"""Send a wav through the full gateway pipeline (STT -> Gemini -> Jarvis TTS).

Usage:
    python scripts/turn_smoke.py path/to/recording.wav --out reply.wav

Requires the gateway:
    uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000
  or:
    docker compose up --build
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="Wav file to send as input speech")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--out", type=Path, default=Path("reply.wav"))
    args = parser.parse_args()

    if not args.audio.exists():
        raise SystemExit(f"Audio file not found: {args.audio}")

    health = requests.get(f"{args.url}/health", timeout=30)
    health.raise_for_status()
    print("Gateway health:", health.json())

    with open(args.audio, "rb") as f:
        resp = requests.post(
            f"{args.url}/v1/turn",
            files={"file": (args.audio.name, f, "audio/wav")},
            timeout=300,
        )

    if not resp.ok:
        print(f"Error {resp.status_code}: {resp.text}")
        raise SystemExit(1)

    data = resp.json()
    print(f"Transcript: {data['transcript']}")
    print(f"Reply text: {data['reply_text']}")

    args.out.write_bytes(base64.b64decode(data["audio_base64"]))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
