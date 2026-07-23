"""Cross-platform device selection: CUDA -> MPS (Mac) -> CPU."""
from __future__ import annotations

import torch


def pick_device(preferred: str | None = "auto") -> str:
    """Resolve a torch device string.

    preferred:
      - "auto" / None / "": pick best available
      - "cuda" | "mps" | "cpu": honor if available, else fall back with a warning print
    """
    pref = (preferred or "auto").strip().lower()
    if pref in ("", "auto"):
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    if pref == "cuda":
        if torch.cuda.is_available():
            return "cuda"
        print("[device] CUDA requested but unavailable; falling back.")
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    if pref == "mps":
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        print("[device] MPS requested but unavailable; falling back.")
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    if pref == "cpu":
        return "cpu"

    print(f"[device] Unknown device '{pref}', using auto.")
    return pick_device("auto")
