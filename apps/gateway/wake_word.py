"""Workshop scaffold for wake-word detection.

Attendees can implement loading and scoring in small TODO steps.
"""
from __future__ import annotations

import numpy as np

WAKE_MODEL_NAME = "hey_jarvis"
WAKE_THRESHOLD = 0.5
# openWakeWord's native streaming chunk size: 80ms @ 16kHz.
FRAME_SAMPLES = 1280


class WakeWordDetector:
    def __init__(self) -> None:
        self._model = None

    def load(self) -> bool:
        # TODO(Workshop):
        # 1) Import openwakeword
        # 2) Download/load WAKE_MODEL_NAME
        # 3) Store model in self._model
        self._model = None
        return False

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def score(self, frame: np.ndarray) -> float:
        # TODO(Workshop): return wake score from loaded model prediction.
        _ = frame
        return 0.0
