import pytest

from crystal_voice.adapters.diagnostic import SameTakeDiagnosticAdapter
from crystal_voice.adapters.external import ClearerVoiceSpExPlusAdapter
from crystal_voice.audio import Audio


def audio(seconds):
    return Audio((0.01,) * int(seconds * 16_000), 16_000)


def test_profile_duration_is_enforced():
    adapter = SameTakeDiagnosticAdapter()
    with pytest.raises(ValueError, match="3–5"):
        adapter.enroll(audio(2))
    assert adapter.enroll(audio(4))


def test_external_command_requires_all_conditioning_paths(monkeypatch):
    monkeypatch.setenv("CRYSTAL_VOICE_SPEX_COMMAND", "infer {mixture} {output}")
    with pytest.raises(RuntimeError, match="reference"):
        ClearerVoiceSpExPlusAdapter().load()

