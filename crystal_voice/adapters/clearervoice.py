"""Persistent in-process ClearerVoice-Studio SpEx+ integration."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

from crystal_voice.adapters.base import Extraction, TargetSpeakerExtractor
from crystal_voice.audio import Audio, encode_wav
from crystal_voice.resample import resample
from crystal_voice.provenance import write_clearervoice_report


@dataclass(frozen=True)
class SpExProfile:
    samples_16k: tuple[float, ...]


def _samples(value: Any) -> tuple[float, ...]:
    """Convert common ClearVoice numpy/torch/list return shapes to mono."""
    if isinstance(value, dict):
        for key in ("SpEx_plus_TSE_16K", "output", "audio", "wav"):
            if key in value:
                return _samples(value[key])
        if len(value) == 1:
            return _samples(next(iter(value.values())))
    if isinstance(value, (list, tuple)) and len(value) == 1 and not isinstance(value[0], (float, int)):
        return _samples(value[0])
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    if hasattr(value, "squeeze"):
        value = value.squeeze()
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list) and value and isinstance(value[0], list):
        value = value[0]
    try:
        return tuple(float(sample) for sample in value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Unsupported ClearVoice output type: {type(value).__name__}") from exc


class ClearerVoiceSpExPlusAdapter(TargetSpeakerExtractor):
    name = "ClearerVoice-Studio SpEx+"
    version = "SpEx_plus_TSE_16K"
    sample_rate = 16_000

    def load(self) -> None:
        checkout = Path(os.environ.get("CRYSTAL_VOICE_CLEARERVOICE_HOME", "runtime/ClearerVoice-Studio")).resolve()
        if not checkout.is_dir():
            raise RuntimeError(f"ClearerVoice checkout is missing at {checkout}; run scripts/install_macos.sh")
        for candidate in (checkout, checkout / "clearvoice"):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
        module = importlib.import_module("clearvoice")
        clear_voice = getattr(module, "ClearVoice", None)
        if clear_voice is None:
            raise RuntimeError("Reviewed checkout does not expose clearvoice.ClearVoice")
        # Construction downloads/loads the checkpoint. Readiness is not announced
        # until this returns, so the first microphone recording cannot race loading.
        self._engine = clear_voice(task="target_speaker_extraction", model_names=[self.version])
        self.provenance_path = write_clearervoice_report(checkout)

    def enroll(self, reference: Audio) -> SpExProfile:
        if not 3.0 <= reference.duration <= 5.0:
            raise ValueError("Target Voice Profile must be 3–5 seconds")
        converted = resample(reference, self.sample_rate)
        return SpExProfile(converted.samples)

    def extract(self, mixture: Audio, profile: object) -> Extraction:
        if not isinstance(profile, SpExProfile):
            raise TypeError("SpEx+ requires an enrolled reference profile")
        converted = resample(mixture, self.sample_rate)
        # Use explicit 16 kHz files so neither upstream decoding nor inference can
        # guess the microphone rate. Both files enter the extractor itself.
        with tempfile.TemporaryDirectory(prefix="crystal-spex-") as directory:
            mixture_path = Path(directory) / "mixture-16k.wav"
            reference_path = Path(directory) / "reference-16k.wav"
            mixture_path.write_bytes(encode_wav(converted))
            reference_path.write_bytes(encode_wav(Audio(profile.samples_16k, self.sample_rate)))
            result = self._engine(
                input_path=str(mixture_path),
                reference_path=str(reference_path),
                online_write=False,
            )
        extracted = Audio(_samples(result), self.sample_rate)
        restored = resample(extracted, mixture.sample_rate)
        return Extraction(restored, {
            "conditioned_by_reference": True,
            "model_sample_rate": self.sample_rate,
            "input_sample_rate": mixture.sample_rate,
            "resampler": "48-tap Hann-windowed sinc, 94% Nyquist cutoff",
            "post_processing": "none",
        })
