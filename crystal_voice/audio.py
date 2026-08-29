"""Small, dependency-free PCM WAV utilities and conservative output safety."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
import hashlib
import io
import math
import wave


@dataclass(frozen=True)
class Audio:
    samples: tuple[float, ...]
    sample_rate: int

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sample_rate


def decode_wav(data: bytes) -> Audio:
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            if wav.getcomptype() != "NONE" or wav.getsampwidth() != 2:
                raise ValueError("Only uncompressed 16-bit PCM WAV is supported")
            channels, rate, count = wav.getnchannels(), wav.getframerate(), wav.getnframes()
            pcm = array("h")
            pcm.frombytes(wav.readframes(count))
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"Invalid WAV: {exc}") from exc
    if channels < 1 or rate < 8_000 or rate > 192_000:
        raise ValueError("WAV has unsupported channel count or sample rate")
    mono = []
    for offset in range(0, len(pcm), channels):
        mono.append(sum(pcm[offset : offset + channels]) / (32768.0 * channels))
    return Audio(tuple(mono), rate)


def encode_wav(audio: Audio) -> bytes:
    pcm = array("h", (max(-32768, min(32767, round(x * 32767))) for x in audio.samples))
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setparams((1, 2, audio.sample_rate, 0, "NONE", "not compressed"))
        wav.writeframes(pcm.tobytes())
    return out.getvalue()


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def peak_dbfs(audio: Audio) -> float:
    peak = max((abs(x) for x in audio.samples), default=0.0)
    return 20 * math.log10(peak) if peak else float("-inf")


def rms_dbfs(audio: Audio) -> float:
    if not audio.samples:
        return float("-inf")
    rms = math.sqrt(sum(x * x for x in audio.samples) / len(audio.samples))
    return 20 * math.log10(rms) if rms else float("-inf")


def clipped_samples(audio: Audio) -> int:
    return sum(abs(x) >= 1.0 for x in audio.samples)


def apply_headroom(audio: Audio, ceiling_dbfs: float = -3.0) -> tuple[Audio, float]:
    """Attenuate only when necessary; never normalize or boost."""
    if not audio.samples:
        return audio, 0.0
    ceiling = 10 ** (ceiling_dbfs / 20)
    peak = max(abs(x) for x in audio.samples)
    gain = min(1.0, ceiling / peak) if peak else 1.0
    return Audio(tuple(x * gain for x in audio.samples), audio.sample_rate), 20 * math.log10(gain)


def align_length(audio: Audio, length: int) -> Audio:
    samples = audio.samples[:length]
    if len(samples) < length:
        samples += (0.0,) * (length - len(samples))
    return Audio(samples, audio.sample_rate)

