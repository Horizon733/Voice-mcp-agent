"""Generate speech using saved Jarvis conditionals (no re-cloning).

Usage (from repo root):
    python scripts/tts_smoke.py "Good evening, sir."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.gateway.tts_engine import (  # noqa: E402
    VoiceError,
    load_tts,
    synthesize_to_file,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "text",
        nargs="?",
        default="Good evening, sir. All systems are online.",
    )
    parser.add_argument("--conds", type=Path, default=ROOT / "voices" / "jarvis_conds.pt")
    parser.add_argument("--ref", type=Path, default=ROOT / "voices" / "jarvis-5s.wav")
    parser.add_argument("--out", type=Path, default=ROOT / "out.wav")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--backend", default="turbo", choices=["turbo", "full"])
    args = parser.parse_args()

    try:
        if args.conds.exists():
            model, _C, _dev, _backend, loaded = load_tts(
                device=args.device, backend=args.backend, conds_path=args.conds
            )
            if not loaded:
                raise VoiceError(f"Failed to load conditionals from {args.conds}")
            synthesize_to_file(model, args.text, args.out)
        else:
            if not args.ref.exists():
                raise VoiceError(
                    f"Neither {args.conds} nor {args.ref} exist. "
                    "Run build_jarvis_conds.py first."
                )
            model, _C, _dev, _backend, _ = load_tts(
                device=args.device, backend=args.backend, conds_path=None
            )
            print(f"No saved conditionals; cloning live from {args.ref}...")
            wav = model.generate(args.text, audio_prompt_path=str(args.ref))
            import torchaudio as ta

            ta.save(str(args.out), wav, model.sr)
        print(f"Wrote {args.out}")
    except VoiceError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
