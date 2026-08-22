import math

from crystal_voice.audio import Audio, apply_headroom, decode_wav, encode_wav, fingerprint, peak_dbfs


def test_wav_round_trip_and_fingerprint():
    source = Audio(tuple(0.2 * math.sin(i / 8) for i in range(800)), 16_000)
    encoded = encode_wav(source)
    decoded = decode_wav(encoded)
    assert decoded.sample_rate == 16_000
    assert len(decoded.samples) == len(source.samples)
    assert fingerprint(encoded) == fingerprint(encoded)


def test_headroom_attenuates_but_never_boosts():
    quiet, gain = apply_headroom(Audio((0.01, -0.01), 16_000))
    assert quiet.samples == (0.01, -0.01)
    assert gain == 0
    loud, gain = apply_headroom(Audio((0.99, -0.99), 16_000))
    assert gain < 0
    assert peak_dbfs(loud) <= -3

