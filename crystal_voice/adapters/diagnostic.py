"""Non-model adapter used only to validate laboratory plumbing."""

from crystal_voice.adapters.base import Extraction, TargetSpeakerExtractor
from crystal_voice.audio import Audio


class SameTakeDiagnosticAdapter(TargetSpeakerExtractor):
    name = "Same-take diagnostic (no extraction)"
    version = "1"
    sample_rate = 48_000
    eligible_for_acceptance = False

    def load(self) -> None:
        pass

    def enroll(self, reference: Audio) -> object:
        if not 3 <= reference.duration <= 5:
            raise ValueError("Target Voice Profile must be 3–5 seconds")
        return {"reference_duration": reference.duration}

    def extract(self, mixture: Audio, profile: object) -> Extraction:
        if not profile:
            raise ValueError("An enrolled profile is required")
        return Extraction(mixture, {"conditioned_by_reference": False, "diagnostic_only": True})

