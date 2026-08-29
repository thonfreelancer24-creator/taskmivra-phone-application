import math

from crystal_voice.audio import Audio, peak_dbfs
from crystal_voice.resample import resample


def tone(rate, frequency, seconds=0.12):
    return Audio(tuple(0.2 * math.sin(2 * math.pi * frequency * i / rate) for i in range(round(rate * seconds))), rate)


def rms(audio):
    return math.sqrt(sum(x*x for x in audio.samples) / len(audio.samples))


def test_explicit_48k_to_16k_round_trip_preserves_speech_detail_and_length():
    original = tone(48_000, 6_000)
    model_rate = resample(original, 16_000)
    restored = resample(model_rate, 48_000)
    assert model_rate.sample_rate == 16_000
    assert restored.sample_rate == 48_000
    assert abs(restored.duration - original.duration) < 1 / 16_000
    assert 0.75 <= rms(restored) / rms(original) <= 1.05
    assert peak_dbfs(restored) < -3


def test_resampler_does_not_boost_dc():
    converted = resample(Audio((0.1,) * 4800, 48_000), 16_000)
    assert max(abs(x) for x in converted.samples) <= 0.100001

