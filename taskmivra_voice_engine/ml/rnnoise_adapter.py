"""Commercial-safe optional RNNoise backend for TaskMivra Voice.

RNNoise is not a TaskMivra-owned component. It is used only under its
BSD-style license and must ship with the upstream copyright/license notice.
The TaskMivra proprietary value remains in routing, target-speaker logic,
TaskMivra checkpoints, safety behavior, and product integration.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

import numpy as np

SAMPLE_RATE = 48_000
FRAME_SAMPLES = 480


class RNNoiseUnavailable(RuntimeError):
    pass


class RNNoiseProcessor:
    """Small ctypes wrapper around a locally bundled librnnoise."""

    def __init__(self, library_path: str | os.PathLike[str] | None = None) -> None:
        path = self._resolve_library(library_path)
        try:
            lib = ctypes.CDLL(str(path))
        except OSError as exc:
            raise RNNoiseUnavailable(f"Unable to load RNNoise library: {path}") from exc
        lib.rnnoise_create.argtypes = [ctypes.c_void_p]
        lib.rnnoise_create.restype = ctypes.c_void_p
        lib.rnnoise_destroy.argtypes = [ctypes.c_void_p]
        lib.rnnoise_destroy.restype = None
        lib.rnnoise_process_frame.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        ]
        lib.rnnoise_process_frame.restype = ctypes.c_float
        state = lib.rnnoise_create(None)
        if not state:
            raise RNNoiseUnavailable("rnnoise_create returned a null state")
        self._lib = lib
        self._state = state

    @staticmethod
    def _resolve_library(explicit: str | os.PathLike[str] | None) -> Path:
        candidates: list[Path] = []
        if explicit:
            candidates.append(Path(explicit))
        if os.environ.get("TASKMIVRA_RNNOISE_LIB"):
            candidates.append(Path(os.environ["TASKMIVRA_RNNOISE_LIB"]))
        here = Path(__file__).resolve().parent
        candidates.extend(
            [
                here / ".." / "third_party" / "rnnoise" / "lib" / "librnnoise.dylib",
                here / ".." / "third_party" / "rnnoise" / "lib" / "librnnoise.so",
                here / ".." / "third_party" / "rnnoise" / "bin" / "rnnoise.dll",
            ]
        )
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate.is_file():
                return candidate
        raise RNNoiseUnavailable(
            "RNNoise library not found. Set TASKMIVRA_RNNOISE_LIB or run tools/build_rnnoise.sh."
        )

    def close(self) -> None:
        if getattr(self, "_state", None):
            self._lib.rnnoise_destroy(self._state)
            self._state = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def process_frame(self, frame_48k: np.ndarray) -> tuple[np.ndarray, float]:
        frame = np.asarray(frame_48k, dtype=np.float32).reshape(-1)
        if frame.size != FRAME_SAMPLES:
            raise ValueError(f"RNNoise requires exactly {FRAME_SAMPLES} samples per frame")
        pcm = np.ascontiguousarray(frame * 32768.0, dtype=np.float32)
        out = np.empty(FRAME_SAMPLES, dtype=np.float32)
        vad = float(
            self._lib.rnnoise_process_frame(
                self._state,
                out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                pcm.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            )
        )
        return np.clip(out / 32768.0, -1.0, 1.0).astype(np.float32), vad

    def process(self, wave_48k: np.ndarray) -> tuple[np.ndarray, float]:
        wave = np.asarray(wave_48k, dtype=np.float32).reshape(-1)
        result = np.empty_like(wave)
        vad_values: list[float] = []
        full = (wave.size // FRAME_SAMPLES) * FRAME_SAMPLES
        for start in range(0, full, FRAME_SAMPLES):
            result[start : start + FRAME_SAMPLES], vad = self.process_frame(
                wave[start : start + FRAME_SAMPLES]
            )
            vad_values.append(vad)
        if full < wave.size:
            result[full:] = wave[full:]
        return result, float(np.mean(vad_values)) if vad_values else 0.0
