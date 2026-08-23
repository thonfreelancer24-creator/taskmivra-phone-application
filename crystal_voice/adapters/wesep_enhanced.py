"""Two-stage Crystal Voice recovery path: WeSep isolation + 48 kHz speech enhancement."""

from __future__ import annotations

import math

from crystal_voice.adapters.base import Extraction, TargetSpeakerExtractor
from crystal_voice.adapters.wesep_native import NativeWeSepAdapter
from crystal_voice.audio import Audio


def _bounded_loudness_recovery(audio: Audio, target_rms_dbfs: float = -24.0, max_gain_db: float = 18.0, ceiling_dbfs: float = -3.0) -> tuple[Audio, float]:
    if not audio.samples:
        return audio, 0.0
    rms = math.sqrt(sum(x * x for x in audio.samples) / len(audio.samples))
    peak = max(abs(x) for x in audio.samples)
    if rms <= 1e-8 or peak <= 1e-8:
        return audio, 0.0
    target_rms = 10 ** (target_rms_dbfs / 20.0)
    requested = max(1.0, target_rms / rms)
    requested = min(requested, 10 ** (max_gain_db / 20.0))
    ceiling = 10 ** (ceiling_dbfs / 20.0)
    gain = min(requested, ceiling / peak)
    gain = max(0.0, gain)
    return Audio(tuple(float(x * gain) for x in audio.samples), audio.sample_rate), 20.0 * math.log10(gain) if gain > 0 else float("-inf")


class WeSepMossFormerSEAdapter(TargetSpeakerExtractor):
    name = "WeSep BSRNN-ECAPA + MossFormer2_SE_48K"
    version = "wesep-bsrnn_ecapa_vox1+mossformer2-se-48k"
    sample_rate = 48_000
    eligible_for_acceptance = False
    two_stage_pipeline = True

    def __init__(self) -> None:
        self.extractor = NativeWeSepAdapter()

    def load(self) -> None:
        self.extractor.load()
        import numpy as np
        from clearvoice import ClearVoice
        self._np = np
        self._enhancer = ClearVoice(task="speech_enhancement", model_names=["MossFormer2_SE_48K"])

    def enroll(self, reference: Audio) -> object:
        return self.extractor.enroll(reference)

    def extract(self, mixture: Audio, profile: object) -> Extraction:
        return self.extractor.extract(mixture, profile)

    def review_isolation(self, extraction: Extraction) -> Extraction:
        audible, gain_db = _bounded_loudness_recovery(extraction.audio)
        return Extraction(audible, {**extraction.metadata, "review_gain_db": gain_db, "review_target_rms_dbfs": -24.0})

    def restore(self, extraction: Extraction) -> Extraction:
        if extraction.audio.sample_rate != 48_000:
            raise RuntimeError("MossFormer2_SE_48K recovery stage requires 48 kHz isolation audio")
        source = self._np.asarray(extraction.audio.samples, dtype=self._np.float32)[None, :]
        enhanced = self._enhancer(source)
        if enhanced is None:
            raise RuntimeError("MossFormer2_SE_48K returned no enhanced audio")
        if hasattr(enhanced, "detach"):
            enhanced = enhanced.detach().cpu().numpy()
        enhanced = self._np.asarray(enhanced, dtype=self._np.float32)
        samples = enhanced.reshape(-1)
        length = len(extraction.audio.samples)
        if len(samples) < length:
            samples = self._np.pad(samples, (0, length - len(samples)))
        samples = samples[:length]
        cleaned = Audio(tuple(float(x) for x in samples.tolist()), 48_000)
        audible, gain_db = _bounded_loudness_recovery(cleaned)
        return Extraction(
            audible,
            {
                **extraction.metadata,
                "speech_enhancement": "MossFormer2_SE_48K",
                "enhancement_sample_rate": 48_000,
                "loudness_recovery_gain_db": gain_db,
                "loudness_target_rms_dbfs": -24.0,
                "loudness_max_gain_db": 18.0,
                "output_ceiling_dbfs": -3.0,
            },
        )
