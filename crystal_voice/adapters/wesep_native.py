"""Native WeSep English target-speaker extraction quality-gate adapter.

This recovery adapter intentionally bypasses the rejected 8 kHz SpEx+ path.
WeSep performs its own torchaudio resampling to the model rate, and we disable
WeSep's peak normalization so TaskMivra can judge the real extracted waveform
before any restoration or loudness processing is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib

from crystal_voice.adapters.base import Extraction, TargetSpeakerExtractor
from crystal_voice.audio import Audio


@dataclass(frozen=True)
class WeSepProfile:
    audio: Audio


class NativeWeSepAdapter(TargetSpeakerExtractor):
    name = "WeSep English BSRNN-ECAPA target-speaker extraction"
    version = "bsrnn_ecapa_vox1"
    sample_rate = 16_000
    eligible_for_acceptance = False
    restoration_enabled = False

    def load(self) -> None:
        torch = importlib.import_module("torch")
        torchaudio = importlib.import_module("torchaudio")
        wesep = importlib.import_module("wesep")
        extractor = wesep.load_model("english")
        extractor.set_device("cpu")
        extractor.set_vad(False)
        # Do not let the upstream helper normalize every extraction to 0.9.
        # We want the actual model waveform and apply TaskMivra safety later.
        extractor.set_output_norm(False)
        self._torch = torch
        self._torchaudio = torchaudio
        self._extractor = extractor

    def enroll(self, reference: Audio) -> WeSepProfile:
        if not 3.0 <= reference.duration <= 5.0:
            raise ValueError("Target Voice Profile must be 3-5 seconds")
        return WeSepProfile(reference)

    def extract(self, mixture: Audio, profile: object) -> Extraction:
        if not isinstance(profile, WeSepProfile):
            raise TypeError("WeSep requires an enrolled reference profile")

        mix = self._torch.tensor(mixture.samples, dtype=self._torch.float32).unsqueeze(0)
        enroll = self._torch.tensor(profile.audio.samples, dtype=self._torch.float32).unsqueeze(0)
        with self._torch.inference_mode():
            target = self._extractor.extract_speech_from_pcm(
                mix,
                mixture.sample_rate,
                enroll,
                profile.audio.sample_rate,
            )
        if target is None:
            raise RuntimeError("WeSep did not return target speech")
        if isinstance(target, (tuple, list)):
            target = target[0]
        target = target.detach().cpu()
        if target.ndim == 1:
            target = target.unsqueeze(0)

        model_rate = int(self._extractor.resample_rate)
        if model_rate != mixture.sample_rate:
            target = self._torchaudio.transforms.Resample(
                orig_freq=model_rate,
                new_freq=mixture.sample_rate,
            )(target)

        samples = target.squeeze().tolist()
        if not isinstance(samples, list) or not samples:
            raise RuntimeError("WeSep returned an empty waveform")
        return Extraction(
            Audio(tuple(float(sample) for sample in samples), mixture.sample_rate),
            {
                "conditioned_by_reference": True,
                "model_sample_rate": model_rate,
                "input_sample_rate": mixture.sample_rate,
                "resampler": "torchaudio.transforms.Resample",
                "post_processing": "none",
                "quality_role": "isolation-only recovery gate; restoration disabled",
                "restoration_enabled": False,
            },
        )
