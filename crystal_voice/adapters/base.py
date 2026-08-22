"""Common contract for reference-conditioned target-speaker extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from crystal_voice.audio import Audio


@dataclass(frozen=True)
class Extraction:
    audio: Audio
    metadata: dict[str, Any]


class TargetSpeakerExtractor(ABC):
    name: str
    version: str
    sample_rate: int
    eligible_for_acceptance: bool = True

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def enroll(self, reference: Audio) -> object: ...

    @abstractmethod
    def extract(self, mixture: Audio, profile: object) -> Extraction: ...

