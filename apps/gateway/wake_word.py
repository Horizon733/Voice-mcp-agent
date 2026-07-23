"""'Hey Jarvis' wake-word detection via openWakeWord — fully local, no account/key.

Runs on CPU via ONNX Runtime (the only backend openWakeWord ships on Windows;
the model is tiny enough that CPU is plenty fast on any platform, so this
never needs CUDA/MPS).
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
        try:
            import openwakeword
            from openwakeword.model import Model

            openwakeword.utils.download_models([WAKE_MODEL_NAME])
            self._model = Model(
                wakeword_models=[WAKE_MODEL_NAME],
                inference_framework="onnx",
            )
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[gateway] WARNING: wake-word model failed to load: {exc}")
            self._model = None
            return False

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def score(self, frame: np.ndarray) -> float:
        if self._model is None:
            return 0.0
        predictions = self._model.predict(frame)
        return float(predictions.get(WAKE_MODEL_NAME, 0.0))
