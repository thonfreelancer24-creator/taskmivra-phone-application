"""Optional Apache-2.0 MossFormer2_SE_48K enhancement adapter.

This module is intentionally isolated from the protected TaskMivra Phone call path.
It may be used for offline/benchmarked enhancement and future live streaming only
after the latency and quality gate in LICENSE-INVENTORY.md passes.

The ClearerVoice-Studio runtime and MossFormer2_SE_48K weights are third-party
Apache-2.0 components and must ship with their required notices. They are not
TaskMivra-owned technology.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

SAMPLE_RATE = 48_000
MODEL_NAME = "MossFormer2_SE_48K"


class MossFormer2Unavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class EnhancementResult:
    audio: np.ndarray
    bypassed: bool
    reason: str


class MossFormer2Enhancer:
    """Fail-safe 48 kHz speech-enhancement wrapper.

    On any initialization or inference failure, callers can choose a physical
    microphone bypass instead of losing call audio.
    """

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._load_error: Exception | None = None

    def load(self) -> None:
        if self._engine is not None:
            return
        if self._load_error is not None:
            raise MossFormer2Unavailable(str(self._load_error))
        try:
            from clearvoice import ClearVoice

            self._engine = ClearVoice(
                task="speech_enhancement",
                model_names=[MODEL_NAME],
            )
        except Exception as exc:  # fail closed; caller may bypass
            self._load_error = exc
            raise MossFormer2Unavailable(
                f"Unable to load {MODEL_NAME}: {exc}"
            ) from exc

    def process(self, wave_48k: np.ndarray, *, bypass_on_error: bool = True) -> EnhancementResult:
        wave = np.asarray(wave_48k, dtype=np.float32).reshape(-1)
        if wave.size == 0:
            return EnhancementResult(wave.copy(), True, "empty-input")

        try:
            self.load()
            source = wave[None, :]
            enhanced = self._engine(source)
            if enhanced is None:
                raise RuntimeError(f"{MODEL_NAME} returned no audio")
            if hasattr(enhanced, "detach"):
                enhanced = enhanced.detach().cpu().numpy()
            out = np.asarray(enhanced, dtype=np.float32).reshape(-1)
            if out.size < wave.size:
                out = np.pad(out, (0, wave.size - out.size))
            out = out[: wave.size]
            if not np.all(np.isfinite(out)):
                raise RuntimeError(f"{MODEL_NAME} returned non-finite samples")

            # No normalization or auto-level. Only hard safety clipping.
            peak = float(np.max(np.abs(out))) if out.size else 0.0
            if peak > 1.0:
                out = np.clip(out, -1.0, 1.0)
            return EnhancementResult(out.astype(np.float32), False, "enhanced")
        except Exception as exc:
            if not bypass_on_error:
                raise
            return EnhancementResult(wave.copy(), True, f"bypass:{type(exc).__name__}")
