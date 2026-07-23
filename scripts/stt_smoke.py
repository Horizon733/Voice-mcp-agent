"""Transcribe a WAV/audio file with faster-whisper.

Usage (from repo root):
    python scripts/stt_smoke.py path/to/recording.wav --device cpu
"""
from __future__ import annotations

import argparse
from pathlib import Path

from faster_whisper import WhisperModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="Path to a wav/mp3/etc. recording")
    parser.add_argument(
        "--model",
        default="small.en",
        help="faster-whisper model size/name, e.g. tiny.en, small.en, medium.en",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cuda", "cpu"],
        help="Prefer cpu so TTS can keep the accelerator",
    )
    parser.add_argument(
        "--compute-type",
        default=None,
        help="e.g. float16 (cuda), int8 (cpu). Defaults picked per device if unset.",
    )
    args = parser.parse_args()

    if not args.audio.exists():
        raise SystemExit(f"Audio file not found: {args.audio}")

    compute_type = args.compute_type or ("float16" if args.device == "cuda" else "int8")

    print(f"Loading faster-whisper model '{args.model}' on {args.device} ({compute_type})...")
    model = WhisperModel(args.model, device=args.device, compute_type=compute_type)

    segments, info = model.transcribe(str(args.audio))
    print(f"Detected language: {info.language} (p={info.language_probability:.2f})\n")

    transcript = []
    for segment in segments:
        print(f"[{segment.start:6.2f}s -> {segment.end:6.2f}s] {segment.text}")
        transcript.append(segment.text.strip())

    print("\n--- Full transcript ---")
    print(" ".join(transcript))


if __name__ == "__main__":
    main()
