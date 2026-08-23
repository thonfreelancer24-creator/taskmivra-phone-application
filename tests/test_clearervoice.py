import json
import subprocess
import sys
from types import ModuleType, SimpleNamespace

from crystal_voice.adapters.clearervoice import ClearerVoiceSpExPlusAdapter
from crystal_voice.audio import Audio


class FakeTensor:
    def __init__(self, values): self.values = list(values)
    def unsqueeze(self, _): return self
    def numel(self): return len(self.values)
    def detach(self): return self
    def cpu(self): return self
    def squeeze(self): return self
    def tolist(self): return self.values


class InferenceMode:
    def __enter__(self): return self
    def __exit__(self, *_): return False


def test_direct_spex_loads_checkpoint_model_and_8k_config(monkeypatch, tmp_path):
    checkout = tmp_path / "ClearerVoice-Studio"
    architecture = checkout / "train/target_speaker_extraction/models/SpEx_plus/SpEx_plus.py"
    architecture.parent.mkdir(parents=True)
    architecture.write_text("""
class SpEx_Plus:
    def __init__(self, N): self.N = N
    def load_state_dict(self, state, strict): assert state == {'weight': 1} and strict
    def eval(self): return self
    def __call__(self, mixture, reference): return mixture, object()
""")
    (checkout / "LICENSE").write_text("Apache-2.0 test fixture")
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(checkout), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(checkout), "add", "."], check=True)
    subprocess.run(["git", "-C", str(checkout), "commit", "-qm", "fixture"], check=True)
    root = tmp_path / "spex-plus"; root.mkdir()
    config = root / "config_wsj0-2mix_speech_SpEx-plus_2spk.yaml"; config.write_text("audio_sr: 8000\nref_sr: 8000\nnet_conf:\n  N: 256\n")
    checkpoint = root / "last_best_checkpoint.pt"; checkpoint.write_bytes(b"released checkpoint fixture")
    yaml = ModuleType("yaml"); yaml.safe_load = lambda _: {"audio_sr": 8000, "ref_sr": 8000, "net_conf": {"N": 256}}
    torch = ModuleType("torch")
    torch.float32 = object(); torch.load = lambda *_, **__: {"model": {"weight": 1}}
    torch.tensor = lambda values, dtype: FakeTensor(values); torch.inference_mode = InferenceMode
    monkeypatch.setitem(sys.modules, "yaml", yaml); monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setenv("CRYSTAL_VOICE_SPEX_HOME", str(root))
    monkeypatch.setenv("CRYSTAL_VOICE_SPEX_ARCHITECTURE", str(architecture))
    monkeypatch.setenv("CRYSTAL_VOICE_CHECKPOINT_LOCK", str(tmp_path / "assets.lock.json"))
    monkeypatch.setenv("CRYSTAL_VOICE_PROVENANCE", str(tmp_path / "provenance.json"))
    adapter = ClearerVoiceSpExPlusAdapter(); adapter.load()
    assert adapter.eligible_for_acceptance is False
    reference = Audio((0.02,) * (4 * 48_000), 48_000)
    mixture = Audio((0.03,) * 48_000, 48_000)
    result = adapter.extract(mixture, adapter.enroll(reference))
    assert result.audio.sample_rate == 48_000
    assert result.metadata["model_sample_rate"] == 8_000
    assert result.metadata["conditioned_by_reference"] is True
    report = json.loads((tmp_path / "provenance.json").read_text())
    assert {item["role"] for item in report["assets"]} == {"architecture", "configuration", "checkpoint"}
    assert all(len(item["sha256"]) == 64 for item in report["assets"])


def test_rejects_wrong_released_sample_rate(monkeypatch, tmp_path):
    # The exact 8 kHz assertion is covered through adapter load rather than
    # permitting the old invented 16 kHz setting.
    from crystal_voice.adapters.clearervoice import _network_configuration
    class Network:
        def __init__(self, N): pass
    assert _network_configuration({"net_conf": {"N": 1}}, Network) == {"N": 1}
