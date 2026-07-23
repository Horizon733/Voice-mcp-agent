"""Build and save Chatterbox voice-clone conditionals from a reference WAV.

Usage (from repo root):
    python scripts/build_jarvis_conds.py
    python scripts/build_jarvis_conds.py --backend turbo --device auto
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.gateway.tts_engine import VoiceError, build_and_save_conds  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", type=Path, default=ROOT / "voices" / "jarvis-5s.wav")
    parser.add_argument("--out", type=Path, default=ROOT / "voices" / "jarvis_conds.pt")
    parser.add_argument(
        "--device",
        default="auto",
        help="auto | cuda | mps | cpu (auto picks CUDA, then Mac MPS, then CPU)",
    )
    parser.add_argument("--backend", default="turbo", choices=["turbo", "full"])
    parser.add_argument("--exaggeration", type=float, default=0.5)
    args = parser.parse_args()

    try:
        build_and_save_conds(
            ref_wav=args.ref,
            out_path=args.out,
            device=args.device,
            backend=args.backend,
            exaggeration=args.exaggeration,
        )
    except VoiceError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
