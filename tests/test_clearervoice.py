import json
import subprocess
import sys
from types import ModuleType

from crystal_voice.adapters.clearervoice import ClearerVoiceSpExPlusAdapter
from crystal_voice.audio import Audio, decode_wav


class FakeClearVoice:
    def __init__(self, task, model_names):
        assert task == "target_speaker_extraction"
        assert model_names == ["SpEx_plus_TSE_16K"]

    def __call__(self, *, input_path, reference_path, online_write):
        assert online_write is False
        assert 3 <= decode_wav(open(reference_path, "rb").read()).duration <= 5
        return decode_wav(open(input_path, "rb").read()).samples


def test_real_adapter_conditions_engine_and_explicitly_resamples(monkeypatch, tmp_path):
    checkout = tmp_path / "upstream"; checkout.mkdir()
    (checkout / "LICENSE").write_text("test license")
    (checkout / "spex-test.pth").write_bytes(b"fake checkpoint")
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(checkout), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(checkout), "add", "LICENSE", "spex-test.pth"], check=True)
    subprocess.run(["git", "-C", str(checkout), "commit", "-qm", "fixture"], check=True)
    fake = ModuleType("clearvoice"); fake.ClearVoice = FakeClearVoice
    monkeypatch.setitem(sys.modules, "clearvoice", fake)
    monkeypatch.setenv("CRYSTAL_VOICE_CLEARERVOICE_HOME", str(checkout))
    monkeypatch.setenv("CRYSTAL_VOICE_PROVENANCE", str(tmp_path / "provenance.json"))
    monkeypatch.setenv("CRYSTAL_VOICE_CHECKPOINT_LOCK", str(tmp_path / "checkpoint.lock.json"))
    adapter = ClearerVoiceSpExPlusAdapter(); adapter.load()
    reference = Audio((0.02,) * (4 * 48_000), 48_000)
    mixture = Audio((0.03,) * 48_000, 48_000)
    result = adapter.extract(mixture, adapter.enroll(reference))
    assert result.audio.sample_rate == 48_000
    assert abs(result.audio.duration - 1) < 1 / 16_000
    assert result.metadata["conditioned_by_reference"] is True
    assert result.metadata["model_sample_rate"] == 16_000
    report = json.loads((tmp_path / "provenance.json").read_text())
    assert len(report["source_commit"]) == 40
    assert report["checkpoint_review_required"] is True
    second = ClearerVoiceSpExPlusAdapter(); second.load()
    verified = json.loads((tmp_path / "provenance.json").read_text())
    assert verified["checkpoint_verified_against_existing_lock"] is True
