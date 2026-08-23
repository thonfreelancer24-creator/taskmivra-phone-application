"""Auditable adapters for locally installed upstream TSE implementations."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

from crystal_voice.adapters.base import Extraction, TargetSpeakerExtractor
from crystal_voice.audio import Audio, decode_wav, encode_wav


@dataclass(frozen=True)
class ReferenceProfile:
    audio: Audio


class ExternalReferenceAdapter(TargetSpeakerExtractor):
    command_environment: str

    def load(self) -> None:
        template = os.environ.get(self.command_environment, "")
        required = ("{mixture}", "{reference}", "{output}")
        if not template:
            raise RuntimeError(f"{self.command_environment} is not configured; see docs/MODELS.md")
        if any(field not in template for field in required):
            raise RuntimeError(f"{self.command_environment} must contain {', '.join(required)}")
        self._template = template

    def enroll(self, reference: Audio) -> ReferenceProfile:
        if not 3.0 <= reference.duration <= 5.0:
            raise ValueError("Target Voice Profile must be 3–5 seconds")
        return ReferenceProfile(reference)

    def extract(self, mixture: Audio, profile: object) -> Extraction:
        if not isinstance(profile, ReferenceProfile):
            raise TypeError("This extractor requires its enrolled reference profile")
        with tempfile.TemporaryDirectory(prefix="crystal-voice-") as directory:
            root = Path(directory)
            mixture_path, reference_path, output_path = root / "mixture.wav", root / "reference.wav", root / "output.wav"
            mixture_path.write_bytes(encode_wav(mixture))
            reference_path.write_bytes(encode_wav(profile.audio))
            command = self._template.format(
                mixture=shlex.quote(str(mixture_path)),
                reference=shlex.quote(str(reference_path)),
                output=shlex.quote(str(output_path)),
            )
            result = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=600)
            if result.returncode or not output_path.exists():
                detail = (result.stderr or result.stdout or "output WAV was not created").strip()
                raise RuntimeError(f"{self.name} inference failed: {detail}")
            output = decode_wav(output_path.read_bytes())
        if output.sample_rate != mixture.sample_rate:
            raise RuntimeError("Adapter output rate differs from input; configure upstream high-quality resampling explicitly")
        return Extraction(output, {"conditioned_by_reference": True, "command_env": self.command_environment})


class WeSepAdapter(ExternalReferenceAdapter):
    name = "WeSep reference-conditioned TSE"
    version = "upstream-checkout-required"
    sample_rate = 16_000
    command_environment = "CRYSTAL_VOICE_WESEP_COMMAND"
